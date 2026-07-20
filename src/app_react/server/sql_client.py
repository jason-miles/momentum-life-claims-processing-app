"""SQL access for the Momentum Claims API (FastAPI, streamlit-free).

Runs queries against the demo's serverless SQL warehouse using
``databricks-sql-connector``. Auth follows the Databricks Apps pattern: in the
deployed app the injected OAuth service-principal credentials are used via the
SDK credential provider; locally it falls back to a personal token or the
default profile. Results are cached briefly in-process (TTL) so repeated page
loads don't re-hit the warehouse.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache

from server.config import WAREHOUSE_ID

log = logging.getLogger("momentum.sql")


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
            # Log rather than swallow: in the deployed app the SP OAuth path is
            # the intended identity; a silent fall-through to a default profile
            # would mask a misconfiguration behind confusing downstream errors.
            log.warning("SP OAuth connect failed; falling back to SDK default", exc_info=True)

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


# --- tiny in-process TTL cache (bounded) --------------------------------------
_CACHE: "OrderedDict[str, tuple[float, list[dict]]]" = None  # type: ignore[assignment]
from collections import OrderedDict  # noqa: E402

_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()
_TTL = 60.0
_CACHE_MAX = 512  # cap entries so a long-lived process can't grow unbounded


def _cache_key(sql: str, params: dict | None) -> str:
    return sql if not params else sql + "\x00" + repr(sorted(params.items()))


# --- pooled connection --------------------------------------------------------
# Opening a warehouse connection costs ~3.5s, and multi-query pages (exec KPIs,
# claim detail) fire several queries — so a fresh connection per query was the
# dominant page-load latency (5 queries ≈ 20s). Reuse one shared connection,
# serialized by a lock and transparently re-opened if it goes stale/broken.
_CONN = None
_CONN_LOCK = threading.RLock()


def _get_conn():
    global _CONN
    if _CONN is None:
        _CONN = _connect()
    return _CONN


def _reset_conn():
    global _CONN
    try:
        if _CONN is not None:
            _CONN.close()
    except Exception:
        pass
    _CONN = None


def run_query(
    sql: str, params: dict | None = None, use_cache: bool = True
) -> list[dict]:
    """Execute a read query and return a list of row dicts (cached ~60s).

    Reuses a shared pooled connection (see _get_conn) so multi-query pages don't
    pay the per-query connect cost. ``params`` are bound via the connector's
    native ``:name`` markers — NEVER interpolate untrusted values into ``sql``.
    Raises ``ConnectionUnavailable`` if the warehouse cannot be reached.
    """
    key = _cache_key(sql, params)
    if use_cache:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
            if hit and (time.time() - hit[0]) < _TTL:
                _CACHE.move_to_end(key)
                return hit[1]

    with _CONN_LOCK:
        try:
            out = _exec_on_shared(sql, params)
        except Exception:
            # Connection may be stale/closed — reset once and retry.
            _reset_conn()
            out = _exec_on_shared(sql, params)

    if use_cache:
        with _CACHE_LOCK:
            _CACHE[key] = (time.time(), out)
            _CACHE.move_to_end(key)
            while len(_CACHE) > _CACHE_MAX:
                _CACHE.popitem(last=False)  # evict oldest (LRU)
    return out


def _exec_on_shared(sql: str, params: dict | None) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or None)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, [_json_safe(v) for v in r])) for r in rows]


def execute(sql: str, params: dict | None = None) -> None:
    """Execute a write/DDL statement (not cached).

    ``params`` are bound via the connector (``:name`` markers). Do not
    interpolate untrusted values into ``sql``.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or None)
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
