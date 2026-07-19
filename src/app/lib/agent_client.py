"""Claim-synopsis drafting for the Claim Detail page.

Resolution order (never hard-crashes the app):

1. Try the real agent: ``from ai.agents.synopsis_agent import draft_synopsis``.
2. Fall back to building claim context from SQL (optionally the UC function
   ``momentum_claims_ai.get_claim_context``) and calling the Foundation Model
   endpoint via a direct ``ai_query`` to ``databricks-claude-sonnet-4-6``.
3. If even that is unavailable (no DB creds locally), return a deterministic
   heuristic synopsis so the UI always renders.

``draft_synopsis(claim_no) -> dict`` returns::

    {
      "claim_no": str,
      "markdown": str,          # synopsis body (markdown)
      "discrepancies": [str],   # discrepancy badge labels
      "citations": [str],       # e.g. ["POL", "DOC-91", "REQ-5"]
      "recommendation": str,    # e.g. "REFER" / "PAY" / "DECLINE"
      "source": str,            # "agent" | "ai_query" | "heuristic"
    }
"""
from __future__ import annotations

import json

from lib.config import LLM_ENDPOINT, g


# --------------------------------------------------------------------------- #
# Context gathering
# --------------------------------------------------------------------------- #
def _fetch_claim_row(claim_no: str) -> dict | None:
    from lib.sql_client import run_query

    df = run_query(
        f"SELECT * FROM {g('claim_synopsis_view')} WHERE claim_no = '{claim_no}'"
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def _fmt_zar(val) -> str:
    try:
        return f"R{float(val):,.0f}"
    except (TypeError, ValueError):
        return str(val)


def _heuristic_synopsis(row: dict) -> dict:
    """Deterministic synopsis derived purely from the claim row."""
    claim_no = row.get("claim_no", "?")
    ctype = row.get("claim_type", "?")
    mismatch = bool(row.get("occupation_mismatch"))
    early = bool(row.get("early_claim_flag"))
    risk = float(row.get("risk_score") or 0)
    benefit_status = row.get("benefit_status", "?")
    policy_status = row.get("policy_status", "?")
    reqs_recv = row.get("reqs_received")
    reqs_total = row.get("reqs_total")
    outstanding = row.get("outstanding_codes") or ""
    sum_assured = _fmt_zar(row.get("sum_assured"))

    discrepancies: list[str] = []
    citations = ["POL"]
    if row.get("document_ids"):
        first_doc = str(row["document_ids"]).split(",")[0].strip()
        if first_doc:
            citations.append(first_doc)
    if reqs_total:
        citations.append(f"REQ-{reqs_recv}/{reqs_total}")

    if mismatch:
        discrepancies.append(
            f"Occupation mismatch: inception '{row.get('occupation_at_inception')}' "
            f"vs claim '{row.get('occupation_at_claim')}'"
        )
    if policy_status and policy_status != "in_force":
        discrepancies.append(f"Policy status is '{policy_status}' (not in force)")
    if benefit_status and benefit_status not in ("in_force", "active"):
        discrepancies.append(f"Benefit status is '{benefit_status}'")
    if early:
        discrepancies.append("Early claim relative to inception (anti-selection risk)")
    if outstanding:
        discrepancies.append(f"Outstanding requirements: {outstanding}")

    # Recommendation logic.
    if risk >= 0.6 or (policy_status and policy_status != "in_force"):
        rec = "REFER"
    elif outstanding:
        rec = "PEND (await requirements)"
    elif mismatch:
        rec = "REFER"
    else:
        rec = "PAY"

    body = f"""**{claim_no} — {ctype.title()} claim synopsis**

Benefit: **{row.get('benefit_type', '?')}** with sum assured **{sum_assured}** (status: {benefit_status}). Policy is **{policy_status}**.

Requirements received: **{reqs_recv}/{reqs_total}**. """
    if outstanding:
        body += f"Still outstanding: `{outstanding}`. "
    else:
        body += "All requirements are in. "

    if mismatch:
        body += (
            f"\n\n⚠ The occupation on record at inception "
            f"(*{row.get('occupation_at_inception')}*) differs from the occupation "
            f"stated at claim (*{row.get('occupation_at_claim')}*), which materially "
            f"affects the disability definition and must be verified before payment."
        )
    if early:
        body += (
            "\n\n⚠ The event occurred early in the policy life, raising an "
            "anti-selection / non-disclosure concern."
        )
    body += f"\n\nThird-party checks: {row.get('tp_summary') or 'none recorded'}."
    body += f"\n\nComputed risk score: **{risk:.2f}**."

    return {
        "claim_no": claim_no,
        "markdown": body,
        "discrepancies": discrepancies,
        "citations": citations,
        "recommendation": rec,
        "source": "heuristic",
    }


def _ai_query_synopsis(row: dict) -> dict | None:
    """Ask the Foundation Model to draft a synopsis, grounded in the claim row."""
    from lib.sql_client import run_query

    context = {k: (str(v) if v is not None else None) for k, v in row.items()}
    prompt = (
        "You are a life-insurance claims assessment assistant for Momentum Life "
        "(South Africa). Draft a concise, factual claim synopsis for an assessor "
        "to REVIEW (never auto-decide). Use only the JSON facts provided. "
        "Flag any discrepancies (occupation mismatch, lapsed/lapsing policy or "
        "benefit, early claim, outstanding requirements). Amounts are in ZAR (R). "
        "End with a single line 'Recommendation: <PAY|REFER|DECLINE|PEND>'.\n\n"
        f"CLAIM FACTS (JSON):\n{json.dumps(context, default=str)}"
    )
    safe = prompt.replace("'", "''")
    try:
        df = run_query(
            f"SELECT ai_query('{LLM_ENDPOINT}', '{safe}') AS synopsis"
        )
        if df.empty:
            return None
        text = str(df.iloc[0]["synopsis"])
    except Exception:
        return None

    # Reuse the heuristic to derive structured badges/citations, but swap in
    # the model narrative.
    base = _heuristic_synopsis(row)
    rec = base["recommendation"]
    low = text.lower()
    if "recommendation:" in low:
        tail = text[low.rindex("recommendation:") + len("recommendation:"):]
        rec = tail.strip().splitlines()[0].strip(" .*") or rec
    base.update({"markdown": text, "recommendation": rec, "source": "ai_query"})
    return base


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def draft_synopsis(claim_no: str) -> dict:
    """Draft a synopsis for a claim, degrading gracefully."""
    # 1) Real agent, if it happens to be importable in this runtime.
    try:  # pragma: no cover - only when agent is on path
        from ai.agents.synopsis_agent import draft_synopsis as _agent_draft

        result = _agent_draft(claim_no)
        if isinstance(result, dict) and result.get("markdown"):
            result.setdefault("source", "agent")
            return result
    except Exception:
        pass

    # 2) SQL context + ai_query fallback.
    try:
        row = _fetch_claim_row(claim_no)
    except Exception:
        row = None

    if row is None:
        return {
            "claim_no": claim_no,
            "markdown": (
                "_Could not load claim context — not connected to Databricks. "
                "Connect the app to a workspace to draft a live synopsis._"
            ),
            "discrepancies": [],
            "citations": [],
            "recommendation": "N/A",
            "source": "unavailable",
        }

    ai = _ai_query_synopsis(row)
    if ai is not None:
        return ai

    # 3) Deterministic heuristic (always renders).
    return _heuristic_synopsis(row)


def ask_claim_copilot(claim_no: str, question: str) -> str:
    """Answer a free-text question about a single claim via ai_query."""
    from lib.sql_client import run_query

    try:
        row = _fetch_claim_row(claim_no)
    except Exception:
        row = None
    if row is None:
        return (
            "I can't reach the claim data right now. Connect the app to "
            "Databricks to ask questions about this claim."
        )
    context = json.dumps(
        {k: (str(v) if v is not None else None) for k, v in row.items()},
        default=str,
    )
    prompt = (
        "You are a claims copilot. Answer the assessor's question using ONLY the "
        "claim facts below. Be concise and cite fields you rely on. "
        "Amounts are ZAR (R).\n\n"
        f"CLAIM FACTS: {context}\n\nQUESTION: {question}"
    )
    safe = prompt.replace("'", "''")
    try:
        df = run_query(f"SELECT ai_query('{LLM_ENDPOINT}', '{safe}') AS a")
        return str(df.iloc[0]["a"]) if not df.empty else "No answer returned."
    except Exception as exc:
        return f"Copilot unavailable: {exc}"
