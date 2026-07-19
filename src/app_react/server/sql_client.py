"""SQL access for the Momentum Claims API (FastAPI, streamlit-free).

Runs queries against the demo's serverless SQL warehouse using
``databricks-sql-connector``. Auth follows the Databricks Apps pattern: in the
deployed app the injected OAuth service-principal credentials are used via the
SDK credential provider; locally it falls back to a personal token or the
default profile. Results are cached briefly in-process (TTL) so repeated page
loads don't re-hit the warehouse.
"""
from __future__ import annotations

import os
import threading
import time
from functools import lru_cache

from server.config import WAREHOUSE_ID


class ConnectionUnavailable(RuntimeError):
    """Raised when we cannot establish a warehouse connection."""


def _http_path() -> str:
    return f"/sql/1.0/warehouses/{WAREHOUSE_ID}"


@lru_cache(maxsize=1)
def _server_hostname() -> str:
    host = os.environ.get("DATABRICKS_HOST", "")
    if host:
        return host.replace("https://", "").replace("http://", "").rstrip("/")
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        return w.config.host.replace("https://", "").replace("http://", "").rstrip("/")
    except Exception as exc:  # pragma: no cover - env dependent
        raise ConnectionUnavailable(str(exc))


def _connect():
    try:
        from databricks import sql as dbsql
    except Exception as exc:  # pragma: no cover - import guard
        raise ConnectionUnavailable(f"databricks-sql-connector not installed: {exc}")

    hostname = _server_hostname()
    http_path = _http_path()

    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return dbsql.connect(server_hostname=hostname, http_path=http_path, access_token=token)

    if os.environ.get("DATABRICKS_CLIENT_ID") and os.environ.get("DATABRICKS_CLIENT_SECRET"):
        try:
            from databricks.sdk.core import Config, oauth_service_principal

            cfg = Config(host=f"https://{hostname}")

            def credential_provider():
                return oauth_service_principal(cfg)

            return dbsql.connect(
                server_hostname=hostname,
                http_path=http_path,
                credentials_provider=credential_provider,
            )
        except Exception:
            pass

    try:
        from databricks.sdk import WorkspaceClient

        profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
        w = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
        header_factory = w.config.authenticate

        def credential_provider():
            return header_factory

        return dbsql.connect(
            server_hostname=hostname,
            http_path=http_path,
            credentials_provider=credential_provider,
        )
    except Exception as exc:
        raise ConnectionUnavailable(
            f"No Databricks credentials available ({exc}). Set DATABRICKS_TOKEN + "
            "DATABRICKS_HOST locally, or run inside a Databricks App."
        )


# --- tiny in-process TTL cache ------------------------------------------------
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_LOCK = threading.Lock()
_TTL = 60.0


def run_query(sql: str, use_cache: bool = True) -> list[dict]:
    """Execute a read query and return a list of row dicts (cached ~60s).

    Raises ``ConnectionUnavailable`` if the warehouse cannot be reached.
    """
    if use_cache:
        with _CACHE_LOCK:
            hit = _CACHE.get(sql)
            if hit and (time.time() - hit[0]) < _TTL:
                return hit[1]

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
        out = [dict(zip(cols, [_json_safe(v) for v in r])) for r in rows]
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if use_cache:
        with _CACHE_LOCK:
            _CACHE[sql] = (time.time(), out)
    return out


def execute(sql: str) -> None:
    """Execute a write/DDL statement (not cached)."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _json_safe(v):
    """Coerce warehouse values to JSON-serialisable primitives."""
    import datetime as _dt
    import decimal as _dec

    if isinstance(v, (_dt.date, _dt.datetime)):
        return v.isoformat()
    if isinstance(v, _dec.Decimal):
        return float(v)
    return v


def connection_ok() -> tuple[bool, str]:
    try:
        rows = run_query("SELECT 1 AS ok", use_cache=False)
        return (len(rows) > 0), "connected"
    except ConnectionUnavailable as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
