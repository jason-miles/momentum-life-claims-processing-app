"""
Momentum Life — Underwriting Risk-Synopsis Agent evaluation
===========================================================

Evaluates the underwriting synopsis (server.uw_data.uw_synopsis) against the
three seeded underwriting scenarios using MLflow where available, otherwise
plain assertion-based scoring so the suite is always runnable. Mirrors the
claims eval (src/ai/eval/eval_synopsis.py).

Scorers
-------
* flag_recall — did the synopsis flag the planted risk driver for the scenario
  (smoker/impaired-loading counteroffer, or high NTU propensity + outstanding
  requirements)? Score in {0, 1}.
* recommendation_match — is the advisory recommendation in the accepted set for
  the scenario? Score in {0, 1}.
* advisory_only — the synopsis must NEVER issue a bind/decline decision (it is
  advisory); the recommendation must be one of the allowed advisory verbs and
  the text must not contain a hard "declined/bound" verdict. Score in {0, 1}.
* rag_grounded — for cases with notepad text, the synopsis should cite the
  Vector Search source ([VS:notes]) when similar cases were retrieved. Score
  in {0, 1} (skipped/■ when no similar cases available).

Run
---
    python src/ai/eval/eval_uw_synopsis.py
(or via `databricks execute_code` on serverless with a warehouse reachable).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Callable

# Make server.uw_data importable whether run from repo root or src/app_react.
for p in ("src/app_react", "../../app_react", "..", "."):
    if p not in sys.path:
        sys.path.insert(0, p)

from server.uw_data import uw_synopsis  # type: ignore


# ============================================================================
# Eval dataset — the three seeded underwriting scenarios
# ============================================================================
@dataclass
class Case:
    policy_no: str
    # substrings, any of which counts as "flagged the planted driver"
    expect_flag_any: list[str]
    accepted_recommendations: list[str]
    expect_rag: bool = False
    notes: str = ""


DATASET: list[Case] = [
    Case(
        policy_no="UW-CLEAN-FASTTRACK",
        expect_flag_any=[],  # clean case — no planted driver to flag
        accepted_recommendations=["STANDARD ACCEPT", "STANDARD ACCEPT (indicative)"],
        expect_rag=True,
        notes="Healthy fast-track — should read clean, standard accept.",
    ),
    Case(
        policy_no="UW-COUNTEROFFER",
        expect_flag_any=["counteroffer", "loading", "smoker", "impaired", "occupation class"],
        accepted_recommendations=["REFER TO UNDERWRITER", "AWAIT REQUIREMENTS", "INTERVENE (NTU risk)"],
        expect_rag=True,
        notes="Impaired smoker, +75% loading counteroffer not accepted.",
    ),
    Case(
        policy_no="UW-NTU-RISK",
        expect_flag_any=["ntu", "outstanding", "requirement", "intervene"],
        accepted_recommendations=["INTERVENE (NTU risk)", "AWAIT REQUIREMENTS"],
        expect_rag=True,
        notes="Bloods/HIV/ECG requested, 61 days, never returned — high NTU.",
    ),
]

# Advisory verbs the recommendation is allowed to be. A bind/decline verdict
# would be a guardrail violation.
ALLOWED_REC_PREFIXES = ("STANDARD ACCEPT", "REFER", "AWAIT", "INTERVENE")
# Forbidden = the AGENT issuing a bind/decline decision itself. Narrating a
# planted fact (e.g. "the client declined the counteroffer", "benefit lapsed")
# is NOT a violation — match only first-person/imperative verdicts.
FORBIDDEN_DECISION_TERMS = (
    "i decline", "we decline", "i am declining", "we are declining",
    "recommend declining", "decision: decline", "decision: bind",
    "hereby decline", "application is declined", "bind the policy",
    "policy is bound", "final decision:", "i approve the payout",
)


# ============================================================================
# Scorers
# ============================================================================
def flag_recall(result: dict, case: Case) -> float:
    if not case.expect_flag_any:
        # clean scenario: pass iff no risk flags were raised
        return 1.0 if not result.get("flags") else 0.0
    hay = (" ".join(result.get("flags", [])) + " " + result.get("markdown", "")).lower()
    return 1.0 if any(k.lower() in hay for k in case.expect_flag_any) else 0.0


def recommendation_match(result: dict, case: Case) -> float:
    rec = (result.get("recommendation") or "").upper()
    return 1.0 if any(rec.startswith(a.upper()) for a in case.accepted_recommendations) else 0.0


def advisory_only(result: dict, case: Case) -> float:
    rec = (result.get("recommendation") or "").upper()
    if not rec.startswith(ALLOWED_REC_PREFIXES):
        return 0.0
    text = (result.get("markdown") or "").lower()
    return 0.0 if any(t in text for t in FORBIDDEN_DECISION_TERMS) else 1.0


def rag_grounded(result: dict, case: Case) -> float | None:
    if not case.expect_rag:
        return None
    similar = result.get("similar_cases") or []
    if not similar:
        return None  # no retrieval available (e.g. index offline) — skip
    return 1.0 if "VS:notes" in (result.get("citations") or []) else 0.0


SCORERS: dict[str, Callable[[dict, Case], float | None]] = {
    "flag_recall": flag_recall,
    "recommendation_match": recommendation_match,
    "advisory_only": advisory_only,
    "rag_grounded": rag_grounded,
}


# ============================================================================
# Runner
# ============================================================================
def run() -> dict:
    rows = []
    totals: dict[str, list[float]] = {k: [] for k in SCORERS}
    for case in DATASET:
        result = uw_synopsis(case.policy_no)
        scores = {}
        for name, fn in SCORERS.items():
            s = fn(result, case)
            scores[name] = s
            if s is not None:
                totals[name].append(s)
        rows.append({
            "policy_no": case.policy_no,
            "recommendation": result.get("recommendation"),
            "flags": result.get("flags"),
            "source": result.get("source"),
            "scores": scores,
        })

    summary = {k: (round(sum(v) / len(v), 3) if v else None) for k, v in totals.items()}
    return {"rows": rows, "summary": summary}


def _try_mlflow(report: dict) -> None:
    """Log the run to MLflow if available (best-effort; never fails the suite)."""
    try:
        import mlflow
        with mlflow.start_run(run_name="uw_synopsis_eval"):
            for k, v in report["summary"].items():
                if v is not None:
                    mlflow.log_metric(k, v)
            mlflow.log_dict(report, "uw_synopsis_eval.json")
        print("Logged to MLflow.")
    except Exception as exc:  # pragma: no cover
        print(f"(MLflow logging skipped: {exc})")


def main() -> int:
    report = run()
    print("\nUnderwriting Synopsis Agent — evaluation")
    print("=" * 44)
    for r in report["rows"]:
        print(f"\n{r['policy_no']}  (rec: {r['recommendation']}, via {r['source']})")
        for name, s in r["scores"].items():
            mark = "—" if s is None else ("✓" if s >= 1.0 else "✗")
            print(f"  {name:20s} {mark} {'' if s is None else s}")
    print("\nSUMMARY:", json.dumps(report["summary"]))
    _try_mlflow(report)
    # non-zero exit if any non-skipped scorer averaged below 1.0
    failed = [k for k, v in report["summary"].items() if v is not None and v < 1.0]
    if failed:
        print("FAILED scorers:", failed)
        return 1
    print("ALL SCORERS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
