"""Central config + environment resolution for the Momentum Claims app.

All identifiers (catalog / schemas / warehouse / endpoints) are read from the
environment injected by app.yaml, with sensible defaults so a bare
``streamlit run app.py`` works locally for a smoke test.
"""
from __future__ import annotations

import os

# --- Physical layout ---------------------------------------------------------
CATALOG = os.environ.get("MOMENTUM_CATALOG", "elexon_app_for_settlement_acc_catalog")
GOLD = os.environ.get("MOMENTUM_GOLD_SCHEMA", "momentum_claims_gold")
SILVER = os.environ.get("MOMENTUM_SILVER_SCHEMA", "momentum_claims_silver")
OPS = os.environ.get("MOMENTUM_OPS_SCHEMA", "momentum_claims_ops")
AI = os.environ.get("MOMENTUM_AI_SCHEMA", "momentum_claims_ai")

# --- Compute / serving -------------------------------------------------------
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "dcb1c3dd8d1570d6")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "01f18397532a1ba0b35d2e530bd1691a")
UW_GENIE_SPACE_ID = os.environ.get("UW_GENIE_SPACE_ID", "01f184232e3012439e84ae6cab552b1e")
LLM_ENDPOINT = os.environ.get("MOMENTUM_LLM_ENDPOINT", "databricks-claude-sonnet-4-6")

# --- Fully-qualified object names --------------------------------------------
def g(obj: str) -> str:
    """Fully-qualify a gold object name."""
    return f"{CATALOG}.{GOLD}.{obj}"


def s(obj: str) -> str:
    """Fully-qualify a silver object name."""
    return f"{CATALOG}.{SILVER}.{obj}"


def o(obj: str) -> str:
    """Fully-qualify an ops object name."""
    return f"{CATALOG}.{OPS}.{obj}"


# --- Brand -------------------------------------------------------------------
BRAND = {
    "primary": "#003366",      # Momentum deep navy
    "primary_light": "#0B4F8A",
    "accent": "#00A9E0",       # cyan accent
    "good": "#1E874B",
    "warn": "#C77700",
    "bad": "#C0392B",
    "bg_soft": "#F3F6FA",
}

ROLES = ["Assessor", "Manager", "Exec", "Investigator", "Admin"]

SLA_DAYS = 20
RISK_THRESHOLD = 0.6
