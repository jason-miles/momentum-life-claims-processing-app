"""Query helpers for the API. Return plain lists/dicts (JSON-ready).

Every function swallows ConnectionUnavailable and returns empty results so the
API stays up and the UI can show a friendly "connect to Databricks" state.
"""
from __future__ import annotations

from server.config import g, s, RISK_THRESHOLD
from server.sql_client import run_query, ConnectionUnavailable


def _safe(sql: str) -> list[dict]:
    try:
        return run_query(sql)
    except ConnectionUnavailable:
        return []
    except Exception:
        return []


def claims_inbox() -> list[dict]:
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
    row = _safe(f"SELECT * FROM {g('claim_synopsis_view')} WHERE claim_no = '{safe_no}'")
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
    tps = _safe(
        f"""SELECT source, result_summary, checked_ts FROM {s('tp_verification')}
            WHERE claim_no = '{safe_no}' ORDER BY source"""
    )
    return {
        "row": (row[0] if row else None),
        "requirements": reqs,
        "documents": docs,
        "events": events,
        "third_party": tps,
    }


def ntu_funnel() -> list[dict]:
    return _safe(f"SELECT claim_type, state, n_claims, n_ntu FROM {g('ntu_funnel')}")


def ntu_at_risk() -> list[dict]:
    return _safe(
        f"""SELECT claim_no, policy_no, claim_type, event_date, days_outstanding,
                   n_outstanding_reqs, drop_off_propensity
            FROM {g('ntu_at_risk')} ORDER BY drop_off_propensity DESC"""
    )


def ops_metrics() -> list[dict]:
    return _safe(
        f"""SELECT claim_no, claim_type, assessor, lodge_ts, decided_ts,
                   days_lodge_to_decision, sla_days, sla_breach
            FROM {g('ops_metrics')}"""
    )


def decision_split() -> list[dict]:
    return _safe(f"SELECT claim_type, decision, n, pct FROM {g('decision_split')}")


def requirement_analytics() -> list[dict]:
    return _safe(
        f"""SELECT claim_type, code, description, n_total, n_received,
                   n_outstanding, pct_received, avg_days_to_receive
            FROM {g('requirement_analytics')} ORDER BY n_outstanding DESC"""
    )


def assessors() -> list[str]:
    rows = _safe(
        f"SELECT DISTINCT assessor FROM {g('claim_synopsis_view')} "
        "WHERE assessor IS NOT NULL ORDER BY assessor"
    )
    return [r["assessor"] for r in rows] if rows else ["assessor_03", "assessor_07", "assessor_11"]


def _measure(view: str, measure: str) -> float | None:
    rows = _safe(f"SELECT MEASURE({measure}) AS v FROM {g(view)}")
    if rows and rows[0].get("v") is not None:
        try:
            return float(rows[0]["v"])
        except (TypeError, ValueError):
            return None
    return None


def exec_kpis() -> dict:
    return {
        "cycle_time_days": _measure("claim_cycle_time", "avg_cycle_days"),
        "ntu_rate": _measure("ntu_rate", "ntu_rate"),
        "sla_attainment_pct": _measure("sla_attainment", "sla_attainment_pct"),
    }


def throughput_per_assessor() -> list[dict]:
    return _safe(
        f"""SELECT assessor, MEASURE(n_decided) AS n_decided
            FROM {g('throughput_per_assessor')} GROUP BY assessor
            ORDER BY n_decided DESC"""
    )


def claims_by_province() -> list[dict]:
    return _safe(
        f"""SELECT province, COUNT(*) AS n_claims
            FROM {g('claim_synopsis_view')} WHERE province IS NOT NULL
            GROUP BY province ORDER BY n_claims DESC"""
    )


def catalog_inventory() -> list[dict]:
    objs = [
        ("claim_synopsis_view", "Gold view — one wide row per claim"),
        ("ntu_funnel", "Gold view — drop-off funnel by type/state"),
        ("ntu_at_risk", "Gold view — at-risk pre-lodge claims"),
        ("ops_metrics", "Gold view — SLA / cycle time per claim"),
        ("decision_split", "Gold view — pay/decline/refer mix"),
        ("requirement_analytics", "Gold view — requirement bottlenecks"),
    ]
    out = []
    for name, desc in objs:
        cnt = _safe(f"SELECT COUNT(*) AS n FROM {g(name)}")
        out.append({"object": name, "description": desc,
                    "row_count": (int(cnt[0]["n"]) if cnt else None)})
    return out
