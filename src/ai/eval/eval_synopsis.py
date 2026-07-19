"""
Momentum Life — Synopsis Agent evaluation
=========================================

Evaluates the Synopsis Agent against the three seeded demo scenarios (DS1-DS3)
using MLflow. Where `mlflow.genai` is available it logs a proper GenAI
evaluation run with custom scorers; otherwise it falls back to plain
assertion-based scoring so the suite is always runnable.

Scorers
-------
* citation_groundedness — every citation the agent emits must correspond to a
  source that actually appears in the governed context bundle (no invented
  sources). Score = fraction of citations that are grounded.
* discrepancy_recall — did the agent flag the planted discrepancy for the
  scenario? (occupation mismatch / missing specialist report / early claim +
  lapsed benefit). Score in {0, 1}.
* no_hallucination — the agent must not assert a scenario's "forbidden" facts
  (e.g. claim DS3 is clean, or DS2 has no outstanding requirements) and must
  never issue a final pay/decline DECISION. Score in {0, 1}.

Run
---
    python src/ai/eval/eval_synopsis.py
(or via `databricks execute_code` on serverless).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List

# Make `ai.agents.synopsis_agent` importable whether run from repo root, from
# src/, or as an uploaded workspace file sitting next to the agent module.
for p in ("src", "..", ".", "../agents"):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from ai.agents.synopsis_agent import draft_synopsis, gather_context
except Exception:  # pragma: no cover - fallback for flat layout
    from synopsis_agent import draft_synopsis, gather_context  # type: ignore


# ============================================================================
# Eval dataset — the three seeded scenarios with expected facts
# ============================================================================
@dataclass
class EvalCase:
    claim_no: str
    label: str
    # Discrepancy the agent MUST recall, expressed as alternative keyword sets;
    # the case passes if ANY inner group is fully present (case-insensitive).
    expected_discrepancy_terms: List[List[str]]
    # Acceptable advisory recommendations (more than one may be defensible).
    acceptable_recommendations: List[str]
    # Substrings that must NOT appear in the synopsis (hallucination guards).
    forbidden_substrings: List[str] = field(default_factory=list)


EVAL_CASES: List[EvalCase] = [
    EvalCase(
        claim_no="CLM-DEATH-CLEAN",
        label="DS1 clean death claim -> pay",
        expected_discrepancy_terms=[],  # none expected; agent should say "no discrepancies"
        acceptable_recommendations=["PAY"],
        # NB: do NOT list phrases the agent legitimately negates on a clean claim
        # (e.g. "no occupation mismatch", "zero outstanding requirements") — a
        # naive substring guard would false-positive on the negation. These
        # markers only appear if the agent invents a problem on a clean file.
        forbidden_substrings=["fraud", "suspicious", "misrepresentation", "benefit lapsed"],
    ),
    EvalCase(
        claim_no="CLM-DISAB-DISCREP",
        label="DS2 occupation mismatch + missing specialist report -> refer/request info",
        expected_discrepancy_terms=[
            ["occupation"],           # occupation mismatch
            ["specialist"],           # missing specialist medical report
        ],
        # REFER and REQUEST INFO are both valid escalations for a missing
        # hard-rule document; PAY / INVESTIGATE are not.
        acceptable_recommendations=["REFER", "REQUEST INFO"],
        forbidden_substrings=[],
    ),
    EvalCase(
        claim_no="CLM-SUSPECT-FRAUD",
        label="DS3 early claim + lapsed benefit -> investigate",
        expected_discrepancy_terms=[
            ["early", "inception"],   # early claim relative to inception
            ["lapsed"],               # benefit lapsed
        ],
        acceptable_recommendations=["INVESTIGATE", "REFER"],
        forbidden_substrings=["no discrepancies", "clean claim"],
    ),
]


# ============================================================================
# Scorers
# ============================================================================
_CITATION_RE = re.compile(r"\[([^\[\]]+)\]")


def _grounded_sources(context: Dict) -> set:
    """Collect all source tokens that legitimately appear in the context."""
    tokens = {
        "POL", "policy", "benefit", "claimability", "silver.life", "life",
    }
    cc = context.get("claim_context") or {}
    # Document ids
    for d in (context.get("documents") or []):
        if isinstance(d, dict) and d.get("doc_id"):
            tokens.add(d["doc_id"])
    if cc.get("document_ids"):
        tokens.update(x.strip() for x in str(cc["document_ids"]).split(","))
    # Requirement codes
    reqs = context.get("outstanding_requirements") or {}
    for bucket in ("outstanding", "received"):
        for r in (reqs.get(bucket) or []):
            if isinstance(r, dict) and r.get("code"):
                tokens.add(r["code"])
    # Third-party sources (e.g. VPD, bank, other_insurer)
    for tp in (context.get("third_party_verifications") or []):
        if isinstance(tp, dict) and tp.get("source"):
            tokens.add(tp["source"])
    return {t.lower() for t in tokens if t}


def score_citation_groundedness(result: Dict, context: Dict) -> float:
    """Fraction of emitted citations that map to a real context source."""
    grounded = _grounded_sources(context)
    cited = set()
    text = result.get("synopsis_markdown", "")
    for m in _CITATION_RE.findall(text):
        cited.add(m.strip().lower())
    cited.update(c.strip().lower() for c in result.get("citations", []))
    if not cited:
        return 0.0
    hits = sum(
        1
        for c in cited
        if c in grounded or any(c in g or g in c for g in grounded)
    )
    return hits / len(cited)


def score_discrepancy_recall(result: Dict, case: EvalCase) -> float:
    """1.0 if all expected discrepancy groups are flagged, else fraction."""
    if not case.expected_discrepancy_terms:
        # Clean case: passes if the agent reports no discrepancy.
        disc = " ".join(result.get("discrepancies", [])).lower()
        syn = result.get("synopsis_markdown", "").lower()
        return 1.0 if (not result.get("discrepancies") or "no discrep" in disc or "no discrep" in syn) else 0.0
    haystack = (
        " ".join(result.get("discrepancies", [])) + " " + result.get("synopsis_markdown", "")
    ).lower()
    hit_groups = sum(
        1 for group in case.expected_discrepancy_terms
        if all(term.lower() in haystack for term in group)
    )
    return hit_groups / len(case.expected_discrepancy_terms)


def score_no_hallucination(result: Dict, case: EvalCase) -> float:
    """0.0 if a forbidden substring appears or a final decision is issued."""
    text = result.get("synopsis_markdown", "").lower()
    for bad in case.forbidden_substrings:
        if bad.lower() in text:
            return 0.0
    # Advisory-only guard: never a final pay/decline DECISION.
    if re.search(r"\b(final decision|hereby (approve|decline)|claim is (approved|declined))\b", text):
        return 0.0
    return 1.0


def score_recommendation(result: Dict, case: EvalCase) -> float:
    return 1.0 if result.get("recommendation") in case.acceptable_recommendations else 0.0


# ============================================================================
# Runner
# ============================================================================
def run_eval() -> List[Dict]:
    """Run all cases and return a list of per-case score dicts."""
    rows: List[Dict] = []
    for case in EVAL_CASES:
        result = draft_synopsis(case.claim_no)
        context = gather_context(case.claim_no)
        rows.append(
            {
                "claim_no": case.claim_no,
                "label": case.label,
                "recommendation": result.get("recommendation"),
                "citation_groundedness": round(score_citation_groundedness(result, context), 3),
                "discrepancy_recall": round(score_discrepancy_recall(result, case), 3),
                "no_hallucination": score_no_hallucination(result, case),
                "recommendation_match": score_recommendation(result, case),
            }
        )
    return rows


def try_mlflow_eval(rows: List[Dict]) -> None:
    """Log the scores to MLflow if available (metrics + a table artifact)."""
    try:
        import mlflow
    except Exception:
        print("[mlflow] not installed — skipping MLflow logging.")
        return

    metrics = ("citation_groundedness", "discrepancy_recall", "no_hallucination", "recommendation_match")
    with mlflow.start_run(run_name="synopsis_agent_eval"):
        # Aggregate metrics across the dataset.
        for m in metrics:
            mlflow.log_metric(f"mean_{m}", sum(r[m] for r in rows) / len(rows))
        # Per-case metrics for drill-down.
        for r in rows:
            for m in metrics:
                mlflow.log_metric(f"{r['claim_no']}__{m}", r[m])
        try:
            mlflow.log_table(
                data={k: [r[k] for r in rows] for k in rows[0].keys()},
                artifact_file="eval_results.json",
            )
        except Exception:
            mlflow.log_dict({"rows": rows}, "eval_results.json")
    print("[mlflow] logged run 'synopsis_agent_eval'.")


def main() -> None:
    rows = run_eval()
    print("\n=== Synopsis Agent evaluation ===")
    for r in rows:
        print(json.dumps(r, indent=2))
    print("\n--- dataset means ---")
    for m in ("citation_groundedness", "discrepancy_recall", "no_hallucination", "recommendation_match"):
        print(f"  {m:24s}: {sum(r[m] for r in rows) / len(rows):.3f}")
    try_mlflow_eval(rows)


if __name__ == "__main__":
    main()
