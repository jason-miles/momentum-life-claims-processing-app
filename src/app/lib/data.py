"""Query helpers returning DataFrames for the app pages.

All functions swallow ConnectionUnavailable and return empty DataFrames so
pages can render a friendly "connect to Databricks" state instead of crashing.
"""
from __future__ import annotations

import pandas as pd

from lib.config import g, s, RISK_THRESHOLD, SLA_DAYS
from lib.sql_client import run_query, ConnectionUnavailable


def _safe(sql: str) -> pd.DataFrame:
    try:
        return run_query(sql)
    except ConnectionUnavailable:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def claims_inbox() -> pd.DataFrame:
    return _safe(
        f"""
        SELECT claim_no, claim_type, state, province, assessor, decision,
               risk_score, occupation_mismatch, early_claim_flag,
               reqs_received, reqs_total, sum_assured, benefit_status,
               event_date, lodge_date,
               DATEDIFF(current_date(), event_date) AS days_in_stage,
               (risk_score >= {RISK_THRESHOLD}) AS high_risk
        FROM {g('claim_synopsis_view')}
        ORDER BY risk_score DESC, event_date
        """
    )


def claim_detail(claim_no: str) -> dict:
    safe_no = claim_no.replace("'", "''")
    row_df = _safe(
        f"SELECT * FROM {g('claim_synopsis_view')} WHERE claim_no = '{safe_no}'"
    )
    reqs = _safe(
        f"""SELECT code, description, status, requested_ts, received_ts
            FROM {s('requirement')} WHERE claim_no = '{safe_no}' ORDER BY status DESC, code"""
    )
    docs = _safe(
        f"""SELECT doc_id, doc_type, filenet_ref, parsed_text
            FROM {s('document')} WHERE claim_no = '{safe_no}' ORDER BY doc_id"""
    )
    events = _safe(
        f"""SELECT event, event_ts FROM {s('claim_event')}
            WHERE claim_no = '{safe_no}' ORDER BY event_ts"""
    )
    return {
        "row": (row_df.iloc[0].to_dict() if not row_df.empty else None),
        "requirements": reqs,
        "documents": docs,
        "events": events,
    }


def ntu_funnel() -> pd.DataFrame:
    return _safe(f"SELECT claim_type, state, n_claims, n_ntu FROM {g('ntu_funnel')}")


def ntu_at_risk() -> pd.DataFrame:
    return _safe(
        f"""SELECT claim_no, policy_no, claim_type, event_date, days_outstanding,
                   n_outstanding_reqs, drop_off_propensity
            FROM {g('ntu_at_risk')} ORDER BY drop_off_propensity DESC"""
    )


def ops_metrics() -> pd.DataFrame:
    return _safe(
        f"""SELECT claim_no, claim_type, assessor, lodge_ts, decided_ts,
                   days_lodge_to_decision, sla_days, sla_breach
            FROM {g('ops_metrics')}"""
    )


def decision_split() -> pd.DataFrame:
    return _safe(f"SELECT claim_type, decision, n, pct FROM {g('decision_split')}")


def requirement_analytics() -> pd.DataFrame:
    return _safe(
        f"""SELECT claim_type, code, description, n_total, n_received,
                   n_outstanding, pct_received, avg_days_to_receive
            FROM {g('requirement_analytics')} ORDER BY n_outstanding DESC"""
    )


def assessors() -> list[str]:
    df = _safe(
        f"SELECT DISTINCT assessor FROM {g('claim_synopsis_view')} "
        "WHERE assessor IS NOT NULL ORDER BY assessor"
    )
    return df["assessor"].tolist() if not df.empty else [
        "assessor_03", "assessor_07", "assessor_11"
    ]


# --- Metric-view KPIs --------------------------------------------------------
def kpi_cycle_time() -> float | None:
    df = _safe(f"SELECT MEASURE(avg_cycle_days) AS v FROM {g('claim_cycle_time')}")
    return float(df.iloc[0]["v"]) if not df.empty and df.iloc[0]["v"] is not None else None


def kpi_ntu_rate() -> float | None:
    df = _safe(f"SELECT MEASURE(ntu_rate) AS v FROM {g('ntu_rate')}")
    return float(df.iloc[0]["v"]) if not df.empty and df.iloc[0]["v"] is not None else None


def kpi_sla_attainment() -> float | None:
    df = _safe(f"SELECT MEASURE(sla_attainment_pct) AS v FROM {g('sla_attainment')}")
    return float(df.iloc[0]["v"]) if not df.empty and df.iloc[0]["v"] is not None else None


def throughput_per_assessor() -> pd.DataFrame:
    return _safe(
        f"""SELECT assessor, MEASURE(n_decided) AS n_decided
            FROM {g('throughput_per_assessor')} GROUP BY assessor
            ORDER BY n_decided DESC"""
    )


def claims_by_province() -> pd.DataFrame:
    return _safe(
        f"""SELECT province, COUNT(*) AS n_claims
            FROM {g('claim_synopsis_view')} WHERE province IS NOT NULL
            GROUP BY province ORDER BY n_claims DESC"""
    )


def catalog_inventory() -> pd.DataFrame:
    objs = [
        ("claim_synopsis_view", "Gold view — one wide row per claim"),
        ("ntu_funnel", "Gold view — drop-off funnel by type/state"),
        ("ntu_at_risk", "Gold view — at-risk pre-lodge claims"),
        ("ops_metrics", "Gold view — SLA / cycle time per claim"),
        ("decision_split", "Gold view — pay/decline/refer mix"),
        ("requirement_analytics", "Gold view — requirement bottlenecks"),
    ]
    rows = []
    for name, desc in objs:
        cnt = _safe(f"SELECT COUNT(*) AS n FROM {g(name)}")
        n = int(cnt.iloc[0]["n"]) if not cnt.empty else None
        rows.append({"object": name, "description": desc, "row_count": n})
    return pd.DataFrame(rows)
