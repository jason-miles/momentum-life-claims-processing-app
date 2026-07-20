"""Claim-synopsis drafting + per-claim copilot (streamlit-free, for the API).

Resolution order (never hard-crashes):
1. Real agent ``ai.agents.synopsis_agent.draft_synopsis`` if importable.
2. SQL context + ``ai_query`` to the Claude Sonnet FM endpoint.
3. Deterministic heuristic synopsis so the UI always renders.

``draft_synopsis(claim_no) -> dict`` and ``ask_claim_copilot(claim_no, q) -> str``.
"""
from __future__ import annotations

import json

from server.config import LLM_ENDPOINT, g


def _fetch_claim_row(claim_no: str) -> dict | None:
    from server.sql_client import run_query

    rows = run_query(
        f"SELECT * FROM {g('claim_synopsis_view')} WHERE claim_no = :claim_no",
        {"claim_no": claim_no},
    )
    return rows[0] if rows else None


def _fmt_zar(val) -> str:
    try:
        return f"R{float(val):,.0f}"
    except (TypeError, ValueError):
        return str(val)


def _heuristic_synopsis(row: dict) -> dict:
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

    if risk >= 0.6 or (policy_status and policy_status != "in_force"):
        rec = "REFER"
    elif outstanding:
        rec = "PEND (await requirements)"
    elif mismatch:
        rec = "REFER"
    else:
        rec = "PAY"

    body = f"""**{claim_no} — {str(ctype).title()} claim synopsis**

Benefit: **{row.get('benefit_type', '?')}** with sum assured **{sum_assured}** (status: {benefit_status}). Policy is **{policy_status}**.

Requirements received: **{reqs_recv}/{reqs_total}**. """
    body += f"Still outstanding: `{outstanding}`. " if outstanding else "All requirements are in. "
    if mismatch:
        body += (
            f"\n\n⚠ The occupation at inception (*{row.get('occupation_at_inception')}*) "
            f"differs from the occupation stated at claim (*{row.get('occupation_at_claim')}*), "
            f"which materially affects the disability definition and must be verified before payment."
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
    from server.sql_client import run_query

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
    try:
        # Bind BOTH the endpoint name and the prompt as parameters so no
        # user/claim-derived text is ever interpolated into SQL syntax.
        rows = run_query(
            "SELECT ai_query(:endpoint, :prompt) AS synopsis",
            {"endpoint": LLM_ENDPOINT, "prompt": prompt},
            use_cache=False,
        )
        if not rows:
            return None
        text = str(rows[0]["synopsis"])
    except Exception:
        return None

    base = _heuristic_synopsis(row)
    rec = base["recommendation"]
    low = text.lower()
    if "recommendation:" in low:
        tail = text[low.rindex("recommendation:") + len("recommendation:"):]
        rec = tail.strip().splitlines()[0].strip(" .*") or rec
    base.update({"markdown": text, "recommendation": rec, "source": "ai_query"})
    return base


def draft_synopsis(claim_no: str) -> dict:
    # Serve a cached result if we have a recent successful one (Claude calls are
    # slow; re-opening the same claim during a demo should be instant).
    from server import synopsis_cache
    cache_key = f"claim:{claim_no}"
    cached = synopsis_cache.get(cache_key)
    if cached is not None:
        return cached

    try:  # pragma: no cover - only when agent is on path
        from ai.agents.synopsis_agent import draft_synopsis as _agent_draft

        result = _agent_draft(claim_no)
        if isinstance(result, dict) and result.get("markdown"):
            result.setdefault("source", "agent")
            synopsis_cache.put(cache_key, result)
            return result
    except Exception:
        pass

    try:
        row = _fetch_claim_row(claim_no)
    except Exception:
        row = None

    if row is None:
        # Do NOT cache the unavailable state — a transient blip shouldn't stick.
        return {
            "claim_no": claim_no,
            "markdown": ("_Could not load claim context — not connected to Databricks._"),
            "discrepancies": [],
            "citations": [],
            "recommendation": "N/A",
            "source": "unavailable",
        }

    ai = _ai_query_synopsis(row)
    result = ai if ai is not None else _heuristic_synopsis(row)

    # RAG: semantically-similar prior claim documents via Vector Search
    # (idx_documents), through the governed search_similar_documents UC function.
    # Best-effort — never blocks the synopsis.
    result["similar_cases"] = _similar_claims(row, exclude=claim_no)
    if result["similar_cases"]:
        result.setdefault("citations", []).append("VS:docs")

    synopsis_cache.put(cache_key, result)
    return result


def _similar_claims(row: dict, exclude: str) -> list[dict]:
    from server.sql_client import run_query
    from server.config import CATALOG, AI

    ctype = row.get("claim_type") or ""
    occ = row.get("occupation_at_claim") or ""
    query = f"{ctype} claim occupation {occ} " + (row.get("outstanding_codes") or "")
    # A Vector Search table-valued function argument cannot be bound as a query
    # parameter, and quote-doubling is defeated by Spark backslash-escaping, so
    # allowlist the search text to a safe charset (letters/digits/space) — this
    # is a semantic query string, so dropping punctuation costs nothing.
    q = _vs_safe(query)
    try:
        rows = run_query(
            f"SELECT claim_no, doc_type, chunk_text, score "
            f"FROM {CATALOG}.{AI}.search_similar_documents('{q}') "
            f"WHERE claim_no <> :ex ORDER BY score DESC LIMIT 3", {"ex": exclude})
        return rows or []
    except Exception:
        return []


def _vs_safe(text: str) -> str:
    """Allowlist a Vector Search query string to letters/digits/space (max 200
    chars). Strips quotes, backslashes and all other punctuation so it can be
    safely interpolated into a `search_*('...')` UC-function call."""
    import re
    return re.sub(r"[^A-Za-z0-9 ]", " ", str(text or ""))[:200].strip()


def ask_claim_copilot(claim_no: str, question: str) -> str:
    from server.sql_client import run_query

    try:
        row = _fetch_claim_row(claim_no)
    except Exception:
        row = None
    if row is None:
        return ("I can't reach the claim data right now. Connect the app to "
                "Databricks to ask questions about this claim.")
    context = json.dumps({k: (str(v) if v is not None else None) for k, v in row.items()}, default=str)
    prompt = (
        "You are a claims copilot. Answer the assessor's question using ONLY the "
        "claim facts below. Be concise and cite fields you rely on. Amounts are ZAR (R).\n\n"
        f"CLAIM FACTS: {context}\n\nQUESTION: {question}"
    )
    try:
        rows = run_query(
            "SELECT ai_query(:endpoint, :prompt) AS a",
            {"endpoint": LLM_ENDPOINT, "prompt": prompt},
            use_cache=False,
        )
        return str(rows[0]["a"]) if rows else "No answer returned."
    except Exception as exc:
        return f"Copilot unavailable: {exc}"
