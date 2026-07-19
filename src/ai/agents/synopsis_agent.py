"""
Momentum Life — Synopsis Agent
==============================

A senior life-claims assessment assistant that drafts a SOURCE-CITED synopsis
for a claim. It follows the Mosaic AI Agent Framework pattern: gather governed
context by calling the Unity Catalog function tools, then ask Claude (served on
Databricks Model Serving) to synthesise an advisory synopsis.

Design principles
-----------------
* Governed context: all facts come from the UC function tools
  (get_claim_context, list_outstanding_requirements, check_claimability,
  get_third_party_verifications, search_claim_documents) executed on the
  serverless SQL warehouse. The agent never queries base tables directly.
* Advisory only: it recommends a NEXT ACTION (PAY / REFER / REQUEST INFO /
  INVESTIGATE) but NEVER issues a final pay/decline DECISION.
* Source-cited: every material statement carries a citation chip such as
  [POL], [DOC-91], [REQ-5], [silver.life], [VPD].
* Safe: it says "insufficient information" when data is missing and never
  reveals unmasked PII.

Public API
----------
    from ai.agents.synopsis_agent import draft_synopsis
    result = draft_synopsis("CLM-DISAB-DISCREP")
    # -> {synopsis_markdown, discrepancies, recommendation, citations}

Auth
----
Host/token are read from env (DATABRICKS_HOST / DATABRICKS_TOKEN) with a
fallback to the databricks-sdk Config (profile / notebook credentials). The
Claude endpoint is called through the Databricks serving OpenAI-compatible
client at `<host>/serving-endpoints`.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# ----------------------------------------------------------------------------
# Fixed configuration for the demo
# ----------------------------------------------------------------------------
CATALOG = "elexon_app_for_settlement_acc_catalog"
AI_SCHEMA = "momentum_claims_ai"
WAREHOUSE_ID = "dcb1c3dd8d1570d6"

LLM_ENDPOINT = "databricks-claude-sonnet-4-6"

_AI = f"{CATALOG}.{AI_SCHEMA}"

# Valid advisory actions. The agent must pick exactly one.
RECOMMENDATIONS = ("PAY", "REFER", "REQUEST INFO", "INVESTIGATE")

SYSTEM_PROMPT = """\
You are a senior life-claims assessment assistant for Momentum Life (South \
Africa). You draft a concise, SOURCE-CITED assessment synopsis for a single \
claim to help a human assessor. You are ADVISORY ONLY.

STRICT RULES
1. Cite the source of every material fact with an inline chip in square \
brackets, drawn from the context you are given, e.g. [POL], [DOC-91], \
[REQ-SPECIALIST], [silver.life], [VPD], [claimability]. Do not invent \
citations — only cite sources that appear in the provided context.
2. Explicitly FLAG discrepancies: occupation mismatch, outstanding \
requirements, early claim (event soon after inception), and benefit/policy \
status mismatches. If none exist, say so.
3. Recommend exactly one NEXT ACTION from: PAY, REFER, REQUEST INFO, \
INVESTIGATE. This is a recommendation for a human — you must NEVER state a \
final pay or decline DECISION yourself.
4. If a needed fact is missing from the context, write "insufficient \
information" rather than guessing.
5. Never reveal unmasked personal information (ID numbers, full DOB, contact \
details). Refer to the life generically.

OUTPUT FORMAT — return a single JSON object, nothing else:
{
  "synopsis_markdown": "<2-5 short paragraphs / bullet markdown, with inline [citation] chips>",
  "discrepancies": ["<short phrase per discrepancy, each with a [citation]>"],
  "recommendation": "<one of PAY | REFER | REQUEST INFO | INVESTIGATE>",
  "citations": ["<every distinct citation chip you used, without brackets>"]
}
"""


# ============================================================================
# SQL warehouse execution (UC tool calls)
# ============================================================================
def _get_workspace_client():
    """Return a databricks-sdk WorkspaceClient using env or profile creds."""
    from databricks.sdk import WorkspaceClient

    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    if host and token:
        return WorkspaceClient(host=host, token=token)
    # Fallback: default config chain (profile, notebook, env).
    return WorkspaceClient()


def _sql_scalar(w, sql: str) -> Optional[str]:
    """Execute a single-cell SQL statement on the warehouse and return it."""
    from databricks.sdk.service.sql import StatementState

    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=sql,
        wait_timeout="50s",
    )
    # Poll if the warehouse needed more than the inline wait.
    import time

    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        time.sleep(1)
        resp = w.statement_execution.get_statement(resp.statement_id)

    if not resp.status or resp.status.state != StatementState.SUCCEEDED:
        err = getattr(getattr(resp, "status", None), "error", None)
        raise RuntimeError(f"SQL failed: {err}\nSQL: {sql}")

    if not resp.result or not resp.result.data_array:
        return None
    return resp.result.data_array[0][0]


def _call_tool(w, fn: str, *args: str) -> Any:
    """Invoke a UC function tool and JSON-decode its string result."""
    quoted = ", ".join("'" + a.replace("'", "''") + "'" for a in args)
    raw = _sql_scalar(w, f"SELECT {_AI}.{fn}({quoted})")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


# ============================================================================
# Context gathering — the agent's "tool use" phase
# ============================================================================
def gather_context(claim_no: str, w=None) -> Dict[str, Any]:
    """
    Call the governed UC tools and assemble the structured context bundle the
    LLM will reason over. Returns a dict keyed by tool.
    """
    w = w or _get_workspace_client()

    ctx = _call_tool(w, "get_claim_context", claim_no)
    if not ctx:
        return {"claim_no": claim_no, "found": False}

    policy_no = ctx.get("policy_no", "")
    return {
        "claim_no": claim_no,
        "found": True,
        "claim_context": ctx,
        "policy_benefits": _call_tool(w, "get_policy_benefits", policy_no)
        if policy_no
        else [],
        "outstanding_requirements": _call_tool(
            w, "list_outstanding_requirements", claim_no
        ),
        "claimability": _call_tool(w, "check_claimability", claim_no),
        "third_party_verifications": _call_tool(
            w, "get_third_party_verifications", claim_no
        ),
        "documents": _call_tool(w, "search_claim_documents", claim_no, ""),
    }


# ============================================================================
# LLM synthesis
# ============================================================================
def _openai_client(w=None):
    """
    OpenAI-compatible client pointed at the Databricks serving endpoints.

    Resolution order:
      1. Explicit DATABRICKS_HOST + DATABRICKS_TOKEN env (Streamlit app / local).
      2. The databricks-sdk's native OpenAI client, which resolves whatever
         auth the environment provides (PAT, OAuth, notebook / serverless
         credential provider). This makes the agent portable across the app,
         serverless jobs and notebooks without a hard-coded PAT.
    """
    from openai import OpenAI

    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    if host and token:
        return OpenAI(api_key=token, base_url=host.rstrip("/") + "/serving-endpoints")

    # SDK-native path: handles OAuth / serverless credential providers.
    from databricks.sdk import WorkspaceClient

    w = w or WorkspaceClient()
    return w.serving_endpoints.get_open_ai_client()


def _build_user_prompt(context: Dict[str, Any]) -> str:
    """Render the gathered context as a compact, labelled prompt."""
    return (
        "Draft the assessment synopsis for claim "
        f"{context['claim_no']}.\n\n"
        "Here is the governed context retrieved from Unity Catalog tools. "
        "Cite these sources: use [POL]/[policy] for policy facts, [benefit] for "
        "benefits, [REQ-<code>] for requirements, [claimability] for rule "
        "results, the third-party source name (e.g. [VPD], [other_insurer]) for "
        "verifications, [<DOC-ID>] for documents, and [silver.life] for life "
        "details.\n\n"
        "```json\n" + json.dumps(context, indent=2, default=str) + "\n```"
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Best-effort extraction of the JSON object from the model's reply."""
    text = text.strip()
    # Strip markdown fences if present.
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = text.find("{")
        last = text.rfind("}")
        if brace != -1 and last != -1:
            text = text[brace : last + 1]
    return json.loads(text)


def draft_synopsis(claim_no: str) -> Dict[str, Any]:
    """
    Produce an advisory, source-cited synopsis for a claim.

    Returns a dict:
      {
        "claim_no": str,
        "synopsis_markdown": str,
        "discrepancies": [str, ...],
        "recommendation": "PAY" | "REFER" | "REQUEST INFO" | "INVESTIGATE",
        "citations": [str, ...],
      }
    """
    w = _get_workspace_client()
    context = gather_context(claim_no, w=w)

    if not context.get("found"):
        return {
            "claim_no": claim_no,
            "synopsis_markdown": (
                f"**Insufficient information.** No claim context was found for "
                f"`{claim_no}` in the governed data layer."
            ),
            "discrepancies": [],
            "recommendation": "REQUEST INFO",
            "citations": [],
        }

    client = _openai_client(w=w)
    completion = client.chat.completions.create(
        model=LLM_ENDPOINT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(context)},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    raw = completion.choices[0].message.content or ""

    try:
        parsed = _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        # Degrade gracefully: surface the raw text rather than crashing the app.
        return {
            "claim_no": claim_no,
            "synopsis_markdown": raw,
            "discrepancies": [],
            "recommendation": "REFER",
            "citations": [],
        }

    rec = str(parsed.get("recommendation", "")).upper().strip()
    if rec not in RECOMMENDATIONS:
        rec = "REFER"

    return {
        "claim_no": claim_no,
        "synopsis_markdown": parsed.get("synopsis_markdown", ""),
        "discrepancies": parsed.get("discrepancies", []) or [],
        "recommendation": rec,
        "citations": parsed.get("citations", []) or [],
    }


# ============================================================================
# Manual test harness — runs the 3 seeded scenarios
# ============================================================================
SEEDED_SCENARIOS = ["CLM-DEATH-CLEAN", "CLM-DISAB-DISCREP", "CLM-SUSPECT-FRAUD"]


def _print_result(res: Dict[str, Any]) -> None:
    print("=" * 78)
    print(f"CLAIM: {res['claim_no']}   ->  RECOMMENDATION: {res['recommendation']}")
    print("-" * 78)
    print(res["synopsis_markdown"])
    print("\nDISCREPANCIES:")
    for d in res["discrepancies"]:
        print(f"  - {d}")
    print("\nCITATIONS:", ", ".join(res["citations"]))
    print()


if __name__ == "__main__":
    for claim in SEEDED_SCENARIOS:
        _print_result(draft_synopsis(claim))
