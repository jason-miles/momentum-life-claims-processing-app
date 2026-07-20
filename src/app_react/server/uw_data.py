"""Underwriting query helpers for the API. Return JSON-ready lists/dicts.

Reads the momentum_uw_gold / _silver layer. Mirrors data.py (claims) but for
the new-business underwriting domain. Degrades gracefully (returns [] and logs).
"""
from __future__ import annotations

import logging

from server.sql_client import run_query, ConnectionUnavailable

log = logging.getLogger("momentum.uw")

import os

# Env-driven for portability (prod re-point). Defaults = demo co-located layout.
CAT = os.environ.get("MOMENTUM_CATALOG", "elexon_app_for_settlement_acc_catalog")
G = f"{CAT}." + os.environ.get("MOMENTUM_UW_GOLD_SCHEMA", "momentum_uw_gold")
S = f"{CAT}." + os.environ.get("MOMENTUM_UW_SILVER_SCHEMA", "momentum_uw_silver")
AI = f"{CAT}." + os.environ.get("MOMENTUM_UW_AI_SCHEMA", "momentum_uw_ai")
LLM = os.environ.get("MOMENTUM_LLM_ENDPOINT", "databricks-claude-sonnet-4-6")


def _vs_safe(text: str) -> str:
    """Allowlist a Vector Search query string to letters/digits/space (max 200
    chars). A VS table-valued function argument can't be bound as a query param,
    so strip quotes/backslashes/punctuation to make interpolation injection-safe."""
    import re
    return re.sub(r"[^A-Za-z0-9 ]", " ", str(text or ""))[:200].strip()


def _safe(sql: str, params: dict | None = None) -> list[dict]:
    try:
        return run_query(sql, params)
    except ConnectionUnavailable as exc:
        log.warning("warehouse unavailable: %s", exc)
        return []
    except Exception:
        log.exception("uw query failed: %s", sql.strip().split("\n")[0][:120])
        return []


def uw_inbox() -> list[dict]:
    return _safe(
        f"""SELECT policy_no, benefit_type, journey_type, sar_band, sum_at_risk,
                   province, underwriter, age, smoker_flag, occupation_class, risk_score,
                   reqs_total, reqs_returned, reqs_outstanding, decision_outcome,
                   task_status, sla_breach, is_ntu, ntu_propensity, days_req_outstanding
            FROM {G}.uw_case_view
            ORDER BY ntu_propensity DESC, sum_at_risk DESC"""
    )


def uw_case(policy_no: str) -> dict:
    p = {"p": policy_no}
    row = _safe(f"SELECT * FROM {G}.uw_case_view WHERE policy_no = :p", p)
    reqs = _safe(
        f"""SELECT code, description, status, requested_ts, returned_ts
            FROM {S}.uw_requirement WHERE policy_no = :p ORDER BY status DESC, code""", p)
    notes = _safe(
        f"""SELECT author, note_ts, note_text FROM {S}.uw_case_note
            WHERE policy_no = :p ORDER BY note_ts""", p)
    return {"row": (row[0] if row else None), "requirements": reqs, "notes": notes}


def uw_exec() -> dict:
    def m(view, measure):
        r = _safe(f"SELECT MEASURE({measure}) v FROM {G}.{view}")
        try:
            return float(r[0]["v"]) if r and r[0].get("v") is not None else None
        except (TypeError, ValueError):
            return None
    return {
        "stp_rate": m("uw_stp_rate", "stp_rate"),
        "ntu_rate": m("uw_ntu_rate", "ntu_rate"),
        "avg_cycle_days": m("uw_turnaround", "avg_cycle_days"),
        "journey_split": _safe(f"SELECT journey_type, n, pct FROM {G}.uw_journey_split ORDER BY n DESC"),
        "decision_split": _safe(f"SELECT outcome, n, pct, n_loadings, n_exclusions FROM {G}.uw_decision_split ORDER BY n DESC"),
    }


def uw_ntu() -> dict:
    return {
        "funnel": _safe(f"SELECT ntu_bucket, n, pct, total_sar FROM {G}.uw_ntu_funnel ORDER BY n DESC"),
        "at_risk": _safe(
            f"""SELECT policy_no, benefit_type, sar_band, sum_at_risk, journey_type,
                       underwriter, reqs_outstanding, days_req_outstanding, ntu_propensity
                FROM {G}.uw_ntu_at_risk LIMIT 100"""),
    }


def uw_requirements() -> list[dict]:
    return _safe(
        f"""SELECT code, description, n_requested, n_returned, n_outstanding,
                   pct_returned, avg_days_to_return
            FROM {G}.uw_requirement_analytics ORDER BY n_requested DESC""")


def uw_ops() -> list[dict]:
    return _safe(
        f"""SELECT underwriter, n_cases, n_breach, avg_cycle_days, n_closed
            FROM {G}.uw_ops_metrics ORDER BY n_cases DESC""")


# --- Underwriting AI synopsis (agentic risk assessment over governed data) ----
def uw_synopsis(policy_no: str) -> dict:
    """Draft a source-cited underwriting risk synopsis. Advisory only — never a
    bind/decline decision. Uses the UC tools as context, then ai_query(Claude)."""
    from server import synopsis_cache
    cache_key = f"uw:{policy_no}"
    cached = synopsis_cache.get(cache_key)
    if cached is not None:
        return cached

    detail = uw_case(policy_no)
    row = detail["row"]
    if not row:
        # Don't cache the unavailable state.
        return {"policy_no": policy_no, "markdown": "_Case not found or not connected._",
                "flags": [], "citations": [], "recommendation": "N/A", "source": "unavailable",
                "similar_cases": []}

    # Coerce the numeric fields used in comparisons/formatting to float up front,
    # so a string-typed warehouse value can't raise a TypeError mid-synopsis
    # (the flag block below is not otherwise guarded — see Isaac review #3).
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    row["risk_score"] = _num(row.get("risk_score"))
    row["ntu_propensity"] = _num(row.get("ntu_propensity"))

    # RAG: semantically-similar prior notepad cases via Vector Search (idx_uw_notes),
    # retrieved through the governed search_uw_notes UC function. Native re-build of
    # the pgvector POC (spec R2.2). Best-effort — never blocks the synopsis.
    similar = []
    note_txt = " ".join(n.get("note_text", "") for n in detail["notes"])
    # A VS table-valued function arg can't be bound and quote-doubling is beaten
    # by Spark backslash-escaping, so allowlist the query text to letters/digits/
    # space (this is stored notepad free text — a second-order injection source).
    q = _vs_safe(note_txt)
    if q:
        try:
            rows = run_query(
                f"SELECT policy_no, chunk_text, score FROM {AI}.search_uw_notes('{q}') "
                f"WHERE policy_no <> :p ORDER BY score DESC LIMIT 3", {"p": policy_no})
            similar = rows
        except Exception:
            similar = []

    flags, citations = [], ["APP", "LIFE"]
    if row.get("smoker_flag"):
        flags.append("Smoker — cotinine / loading consideration")
    if (row.get("risk_score") or 0) >= 0.55:
        flags.append("Impaired risk profile (elevated risk score)")
    if str(row.get("occupation_class", "")).startswith(("C", "D")):
        flags.append(f"Occupation class {row.get('occupation_class')} — manual/hazardous loading")
    if (row.get("reqs_outstanding") or 0) > 0:
        flags.append(f"{row['reqs_outstanding']} requirement(s) outstanding "
                     f"({row.get('days_req_outstanding')} days) — NTU risk")
        citations.append("REQ")
    if (row.get("ntu_propensity") or 0) >= 0.6:
        flags.append(f"High NTU propensity {row['ntu_propensity']:.2f} — intervene now")
    if row.get("decision_outcome") == "counteroffer":
        det = (f"+{row['loading_pct']}% loading" if row.get("loading_pct")
               else f"{row.get('exclusion')} exclusion")
        flags.append(f"Counteroffer on file ({det})")

    # recommendation (advisory)
    if (row.get("ntu_propensity") or 0) >= 0.6:
        rec = "INTERVENE (NTU risk)"
    elif (row.get("risk_score") or 0) >= 0.55 or str(row.get("occupation_class","")).startswith("D"):
        rec = "REFER TO UNDERWRITER"
    elif (row.get("reqs_outstanding") or 0) > 0:
        rec = "AWAIT REQUIREMENTS"
    else:
        rec = "STANDARD ACCEPT (indicative)"

    # try Claude via ai_query for a richer narrative, grounded in the case JSON
    import json
    ctx = {k: (str(v) if v is not None else None) for k, v in row.items()}
    notes_txt = " ".join(n.get("note_text", "") for n in detail["notes"])[:1500]
    prompt = (
        "You are an underwriting assistant for Momentum Life (South Africa). Draft a "
        "concise, factual NEW-BUSINESS risk synopsis for an underwriter to REVIEW. "
        "Never issue a bind/decline decision — advisory only. Use ONLY the JSON facts + "
        "notepad text. Flag risk drivers (smoker, occupation class, impaired risk, "
        "outstanding requirements, NTU risk, counteroffers). Amounts are ZAR (R). End with "
        "a single line 'Recommendation: <STANDARD ACCEPT|REFER|AWAIT REQUIREMENTS|INTERVENE>'.\n\n"
        f"CASE FACTS: {json.dumps(ctx, default=str)}\n\nNOTEPAD: {notes_txt}")
    try:
        r = run_query("SELECT ai_query(:e, :p) AS a", {"e": LLM, "p": prompt}, use_cache=False)
        text = str(r[0]["a"]) if r else None
    except Exception:
        text = None

    if not text:
        # deterministic fallback narrative
        text = (f"**{policy_no} — {str(row.get('benefit_type','')).title()} new business**\n\n"
                f"Life age {row.get('age')}, {row.get('occupation_class')}, "
                f"{'smoker' if row.get('smoker_flag') else 'non-smoker'}. "
                f"Sum at risk R{float(row.get('sum_at_risk') or 0):,.0f} on a "
                f"{str(row.get('journey_type','')).replace('_',' ')} journey. "
                f"Requirements {row.get('reqs_returned')}/{row.get('reqs_total')} returned. "
                f"NTU propensity {row.get('ntu_propensity')}.")
        source = "heuristic"
    else:
        source = "ai_query"

    if similar:
        citations.append("VS:notes")
    result = {"policy_no": policy_no, "markdown": text, "flags": flags,
              "citations": citations, "recommendation": rec, "source": source,
              "similar_cases": similar}
    synopsis_cache.put(cache_key, result)
    return result
