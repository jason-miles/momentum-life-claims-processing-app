"""SQL access for the Momentum Claims app.

Runs queries against the demo's serverless SQL warehouse using
``databricks-sql-connector``. Authentication follows the Databricks Apps
pattern: in the deployed app the injected OAuth service-principal credentials
(DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET / DATABRICKS_HOST) are used via
the SDK's credential provider; locally it falls back to a personal token or the
default profile.

The module NEVER hard-crashes: if credentials or the connector are unavailable
it raises a friendly ``ConnectionUnavailable`` that the UI turns into a
"connect to Databricks" message instead of a stack trace.
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
import streamlit as st

from lib.config import WAREHOUSE_ID


class ConnectionUnavailable(RuntimeError):
    """Raised when we cannot establish a warehouse connection."""


def _http_path() -> str:
    return f"/sql/1.0/warehouses/{WAREHOUSE_ID}"


@lru_cache(maxsize=1)
def _server_hostname() -> str:
    host = os.environ.get("DATABRICKS_HOST", "")
    if host:
        return host.replace("https://", "").replace("http://", "").rstrip("/")
    # Fall back to the SDK config (local profile).
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        return w.config.host.replace("https://", "").replace("http://", "").rstrip("/")
    except Exception as exc:  # pragma: no cover - env dependent
        raise ConnectionUnavailable(str(exc))


def _connect():
    """Open a databricks-sql-connector connection using Apps/SDK auth."""
    try:
        from databricks import sql as dbsql
    except Exception as exc:  # pragma: no cover - import guard
        raise ConnectionUnavailable(
            f"databricks-sql-connector not installed: {exc}"
        )

    hostname = _server_hostname()
    http_path = _http_path()

    # 1) Explicit token (local dev or DATABRICKS_TOKEN injected).
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return dbsql.connect(
            server_hostname=hostname, http_path=http_path, access_token=token
        )

    # 2) Databricks Apps service-principal OAuth (injected client id/secret).
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

    # 3) Generic SDK credential provider (local profile: PAT, U2M/OAuth, etc.).
    try:
        from databricks.sdk import WorkspaceClient

        profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
        w = WorkspaceClient(profile=profile) if profile else WorkspaceClient()
        header_factory = w.config.authenticate  # callable -> {"Authorization": ...}

        def credential_provider():
            return header_factory

        return dbsql.connect(
            server_hostname=hostname,
            http_path=http_path,
            credentials_provider=credential_provider,
        )
    except Exception as exc:
        raise ConnectionUnavailable(
            f"No Databricks credentials available ({exc}). "
            "Set DATABRICKS_TOKEN + DATABRICKS_HOST locally, or run inside a "
            "Databricks App."
        )


@st.cache_data(ttl=60, show_spinner=False)
def run_query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute a read query and return a DataFrame (cached 60s).

    Raises ``ConnectionUnavailable`` if the warehouse cannot be reached; callers
    should catch and show a friendly message.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or None)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame([list(r) for r in rows], columns=cols)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute(sql: str, params: tuple | None = None) -> None:
    """Execute a write/DDL statement (not cached)."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or None)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def connection_ok() -> tuple[bool, str]:
    """Lightweight health probe used by the UI to decide demo vs live mode."""
    try:
        df = run_query("SELECT 1 AS ok")
        return (not df.empty), "connected"
    except ConnectionUnavailable as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
