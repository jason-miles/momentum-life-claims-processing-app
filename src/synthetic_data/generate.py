"""Deterministic synthetic-data generator for the Momentum Life Claims demo.

Produces the full bronze estate as pandas DataFrames and writes them to the
bronze schema as Delta tables. Everything is fabricated — no real PII.

Entities (silver-conformed shapes, landed 1:1 in bronze):
  policy, life, role_player, benefit, claim, claim_event, requirement,
  document, email, tp_verification, claimability_rule

The three seeded scenarios (DS1-DS3) are appended last with known claim numbers:
  CLM-DEATH-CLEAN     — clean death claim, recommend pay
  CLM-DISAB-DISCREP   — occupation mismatch + missing specialist report, refer
  CLM-SUSPECT-FRAUD   — early claim + benefit-status mismatch, investigate (mocked risk)

Run as a Databricks job task (see resources/jobs.yml) or locally for a dry run:
    python -m src.synthetic_data.generate --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import random

import numpy as np
import pandas as pd

from .config import (
    BENEFIT_TYPES, BROKERS, CLAIM_TYPE_MIX, CLAIMS_PER_100_POLICIES,
    DECISION_MIX, DOC_TYPES, N_POLICIES, NTU_RATE, OCCUPATIONS, PROVINCES,
    PROVINCE_WEIGHTS, REQUIREMENTS_BY_TYPE, SEED, STATE_MIX, TP_SOURCES,
)

BASE_DATE = dt.date(2026, 7, 1)   # "today" for the demo dataset


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _weighted(rng: random.Random, mapping: dict[str, float]) -> str:
    keys = list(mapping)
    return rng.choices(keys, weights=[mapping[k] for k in keys], k=1)[0]


def _sa_id_masked(rng: random.Random, dob: dt.date, is_female: bool) -> str:
    """Structurally-valid but fabricated SA ID number, then masked.

    SA ID: YYMMDD SSSS C A Z  (13 digits). We mask the middle so no plausible
    real identity is emitted, keeping only the DOB prefix + last digit shape.
    """
    yy = dob.strftime("%y")
    mm = dob.strftime("%m")
    dd = dob.strftime("%d")
    gender = rng.randint(0, 4999) if is_female else rng.randint(5000, 9999)
    prefix = f"{yy}{mm}{dd}"
    return f"{prefix}*******{rng.randint(0, 9)}"  # middle masked


def _rand_date(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    span = (end - start).days
    return start + dt.timedelta(days=rng.randint(0, max(span, 1)))


# ----------------------------------------------------------------------------
# Generators
# ----------------------------------------------------------------------------
def gen_policies(rng: random.Random, n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        inception = _rand_date(rng, dt.date(2008, 1, 1), dt.date(2025, 12, 31))
        signed = inception - dt.timedelta(days=rng.randint(3, 45))
        rows.append({
            "policy_no": f"POL-{i:05d}",
            "signed_date": signed,
            "inception_date": inception,
            "broker": rng.choice(BROKERS),
            "status": rng.choices(["in_force", "lapsed", "paid_up"],
                                  weights=[0.86, 0.09, 0.05], k=1)[0],
            "insurable_interest": rng.choice(["own_life", "spouse", "keyman", "cessionary"]),
        })
    return pd.DataFrame(rows)


def gen_lives(rng: random.Random, policies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in policies.iterrows():
        n_lives = rng.choices([1, 2], weights=[0.8, 0.2], k=1)[0]
        for j in range(n_lives):
            is_female = rng.random() < 0.48
            dob = _rand_date(rng, dt.date(1955, 1, 1), dt.date(2000, 12, 31))
            occ = rng.choice(OCCUPATIONS)
            rows.append({
                "life_id": f"{p.policy_no}-L{j+1}",
                "policy_no": p.policy_no,
                "id_number_masked": _sa_id_masked(rng, dob, is_female),
                "dob": dob,
                "occupation_at_inception": occ,
                "smoker_flag": rng.random() < 0.22,
                "province": rng.choices(PROVINCES, weights=PROVINCE_WEIGHTS, k=1)[0],
                "sensitivity": "L2" if rng.random() < 0.3 else "L1",
            })
    return pd.DataFrame(rows)


def gen_role_players(rng: random.Random, policies: pd.DataFrame) -> pd.DataFrame:
    rels = ["spouse", "child", "parent", "estate", "sibling"]
    rows = []
    for _, p in policies.iterrows():
        rows.append({"policy_no": p.policy_no, "role": "policyholder",
                     "relationship": "self", "name": f"Holder {p.policy_no[-5:]}"})
        rows.append({"policy_no": p.policy_no, "role": "payer",
                     "relationship": "self", "name": f"Payer {p.policy_no[-5:]}"})
        for b in range(rng.randint(1, 3)):
            rows.append({"policy_no": p.policy_no, "role": "beneficiary",
                         "relationship": rng.choice(rels),
                         "name": f"Beneficiary {p.policy_no[-5:]}-{b+1}"})
    return pd.DataFrame(rows)


def gen_benefits(rng: random.Random, policies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in policies.iterrows():
        n = rng.randint(1, 4)
        chosen = rng.sample(BENEFIT_TYPES, k=min(n, len(BENEFIT_TYPES)))
        for bt in chosen:
            sum_assured = float(np.round(np.random.lognormal(mean=13.4, sigma=0.7), -3))
            rows.append({
                "benefit_id": f"{p.policy_no}-B-{bt[:3].upper()}",
                "policy_no": p.policy_no,
                "benefit_type": bt,
                "sum_assured": min(max(sum_assured, 50_000), 15_000_000),
                "status": rng.choices(["in_force", "lapsed", "excluded"],
                                      weights=[0.9, 0.06, 0.04], k=1)[0],
                "loadings": rng.choice(["", "", "smoker+50%", "occupation+25%", "medical+30%"]),
                "exclusions": rng.choice(["", "", "pre-existing cardiac", "hazardous pursuits", "suicide<24m"]),
            })
    return pd.DataFrame(rows)


def gen_claims(rng: random.Random, policies: pd.DataFrame, lives: pd.DataFrame):
    """Return (claims, claim_events, requirements) DataFrames."""
    n_claims = int(len(policies) * CLAIMS_PER_100_POLICIES / 100)
    claim_rows, event_rows, req_rows = [], [], []
    life_by_policy = lives.groupby("policy_no").first()

    claimed_policies = rng.sample(list(policies.policy_no), k=min(n_claims, len(policies)))
    for i, policy_no in enumerate(claimed_policies, start=1):
        claim_no = f"CLM-{i:05d}"
        claim_type = _weighted(rng, CLAIM_TYPE_MIX)
        state = _weighted(rng, STATE_MIX)

        life = life_by_policy.loc[policy_no] if policy_no in life_by_policy.index else None
        occ_inception = life.occupation_at_inception if life is not None else "Clerk"
        # small chance of a genuine occupation change over the life of the policy
        occ_claim = occ_inception if rng.random() > 0.08 else rng.choice(OCCUPATIONS)

        event_date = _rand_date(rng, dt.date(2026, 1, 1), BASE_DATE)
        is_pre_lodge = state in ("initiated",)
        # NTU_RATE is the share of PRE-LODGE (initiated) claims that stall and are
        # never taken up, so it applies directly to the initiated population.
        is_ntu = is_pre_lodge and (rng.random() < NTU_RATE)
        lodge_date = None if is_pre_lodge else event_date + dt.timedelta(days=rng.randint(3, 14))

        decision = None
        decided_date = None
        if state in ("decided", "paid"):
            decision = _weighted(rng, DECISION_MIX)
            decided_date = (lodge_date or event_date) + dt.timedelta(days=rng.randint(2, 25))

        claim_rows.append({
            "claim_no": claim_no,
            "policy_no": policy_no,
            "claim_type": claim_type,
            "event_date": event_date,
            "lodge_date": lodge_date,
            "state": state,
            "occupation_at_claim": occ_claim,
            "decision": decision,
            "decided_date": decided_date,
            "assessor": f"assessor_{rng.randint(1, 24):02d}",
            "risk_score": round(rng.betavariate(2, 6), 2),  # mocked fraud propensity
            "is_ntu": bool(is_ntu),
        })

        # events
        seq = [("initiated", event_date)]
        if not is_pre_lodge:
            seq.append(("lodged", lodge_date))
            if state in ("in_assessment", "decided", "paid"):
                seq.append(("in_assessment", lodge_date + dt.timedelta(days=rng.randint(1, 4))))
            if state in ("decided", "paid"):
                seq.append(("decided", decided_date))
            if state == "paid":
                seq.append(("paid", decided_date + dt.timedelta(days=rng.randint(1, 7))))
        for st, ts in seq:
            event_rows.append({"claim_no": claim_no, "event": st, "event_ts": ts})

        # requirements
        reqs = REQUIREMENTS_BY_TYPE[claim_type]
        n_received = len(reqs) if not is_pre_lodge else rng.randint(1, len(reqs) - 1)
        for k, (code, desc) in enumerate(reqs):
            received = k < n_received
            requested_ts = event_date + dt.timedelta(days=1)
            req_rows.append({
                "claim_no": claim_no,
                "code": code,
                "description": desc,
                "status": "received" if received else "outstanding",
                "requested_ts": requested_ts,
                "received_ts": (requested_ts + dt.timedelta(days=rng.randint(1, 10))) if received else None,
            })

    return (pd.DataFrame(claim_rows), pd.DataFrame(event_rows), pd.DataFrame(req_rows))


def gen_documents(rng: random.Random, claims: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in claims.iterrows():
        n_docs = rng.randint(2, 5)
        for d in range(n_docs):
            doc_type = rng.choice(DOC_TYPES)
            rows.append({
                "doc_id": f"DOC-{c.claim_no[-5:]}-{d+1}",
                "claim_no": c.claim_no,
                "doc_type": doc_type,
                "filenet_ref": f"FN-{rng.randint(100000, 999999)}",
                "parsed_text": _synth_doc_text(doc_type, c),
                "extracted_json": _synth_doc_fields(doc_type, c),
            })
    return pd.DataFrame(rows)


def _synth_doc_text(doc_type: str, c) -> str:
    if doc_type == "death_certificate":
        return (f"REPUBLIC OF SOUTH AFRICA — DEATH CERTIFICATE. "
                f"Cause of death recorded. Date of event {c.event_date}. "
                f"Registered under claim {c.claim_no}.")
    if doc_type == "specialist_medical_report":
        return (f"SPECIALIST MEDICAL REPORT. Assessment of functional impairment "
                f"for {c.claim_type} claim {c.claim_no}. Occupation stated as "
                f"{c.occupation_at_claim}. Clinical findings support the diagnosis.")
    if doc_type == "op_form":
        return f"CLAIM (OP) FORM for {c.claim_no}. Claimant declaration and consent signed."
    if doc_type == "bank_letter":
        return f"BANK VERIFICATION for {c.claim_no}. Account confirmed active."
    if doc_type == "ID":
        return f"CERTIFIED IDENTITY DOCUMENT attached for {c.claim_no}."
    return f"CLAIM FORM {c.claim_no}. Standard submission."


def _synth_doc_fields(doc_type: str, c) -> str:
    import json
    return json.dumps({
        "doc_type": doc_type,
        "claim_no": c.claim_no,
        "occupation": getattr(c, "occupation_at_claim", None),
        "event_date": str(c.event_date),
    })


def gen_emails(rng: random.Random, claims: pd.DataFrame) -> pd.DataFrame:
    rows = []
    subjects_out = ["Outstanding requirements for your claim",
                    "Reminder: documents required", "Update on your claim assessment"]
    subjects_in = ["Re: documents attached", "Submitting requested forms",
                   "Query about my claim"]
    for _, c in claims.iterrows():
        for _ in range(rng.randint(1, 6)):
            direction = rng.choice(["outbound", "inbound"])
            rows.append({
                "email_id": f"EM-{c.claim_no[-5:]}-{rng.randint(1000, 9999)}",
                "claim_no": c.claim_no,
                "direction": direction,
                "subject": rng.choice(subjects_out if direction == "outbound" else subjects_in),
                "body": (f"Regarding claim {c.claim_no} ({c.claim_type}). "
                         f"Please action the outstanding items at your earliest convenience."),
                "attachments": rng.choice(["", "op_form.pdf", "id.pdf", "specialist_report.pdf"]),
                "sent_ts": c.event_date + dt.timedelta(days=rng.randint(0, 20)),
            })
    return pd.DataFrame(rows)


def gen_tp_verifications(rng: random.Random, claims: pd.DataFrame) -> pd.DataFrame:
    import json
    rows = []
    for _, c in claims.iterrows():
        for src in rng.sample(TP_SOURCES, k=rng.randint(1, len(TP_SOURCES))):
            result = {"VPD": {"deceased_confirmed": c.claim_type == "death"},
                      "other_insurer": {"claims_last_3y": rng.randint(0, 2)},
                      "bank": {"account_active": True},
                      "identity": {"verified": True}}[src]
            rows.append({
                "claim_no": c.claim_no,
                "source": src,
                "result_json": json.dumps(result),
                "result_summary": ("confirmed" if list(result.values())[0] in (True,) else "see detail"),
                "checked_ts": c.event_date + dt.timedelta(days=rng.randint(0, 5)),
            })
    return pd.DataFrame(rows)


def gen_claimability_rules() -> pd.DataFrame:
    """Externalised claimability rules — out of spreadsheets, into a governed table."""
    rows = [
        ("RULE-DEATH-01", "death", "policy_in_force", "Policy must be in force at event date", "hard"),
        ("RULE-DEATH-02", "death", "death_cert_received", "Death certificate must be received", "hard"),
        ("RULE-DEATH-03", "death", "not_within_suicide_exclusion", "Event outside 24m suicide exclusion", "hard"),
        ("RULE-DISAB-01", "disability", "specialist_report_received", "Specialist medical report received", "hard"),
        ("RULE-DISAB-02", "disability", "occupation_consistent", "Occupation at claim consistent with inception", "soft"),
        ("RULE-CI-01", "critical_illness", "diagnosis_confirmed", "Confirmed diagnosis on approved list", "hard"),
        ("RULE-INCOME-01", "income", "income_proof_received", "Proof of income received", "hard"),
        ("RULE-ALL-01", "all", "beneficiary_nominated", "At least one beneficiary nominated", "soft"),
        ("RULE-ALL-02", "all", "benefit_in_force", "Claimed benefit must be in force", "hard"),
    ]
    return pd.DataFrame(rows, columns=["rule_id", "claim_type", "rule_key", "description", "severity"])


# ----------------------------------------------------------------------------
# Seeded scenarios (DS1-DS3) — appended with known claim numbers.
# ----------------------------------------------------------------------------
def append_seeded_scenarios(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    import json
    policies, lives, benefits = data["policy"], data["life"], data["benefit"]
    claims, events, reqs = data["claim"], data["claim_event"], data["requirement"]
    docs, emails, tps = data["document"], data["email"], data["tp_verification"]

    def add_policy(policy_no, occ_inception, benefit_type, benefit_status="in_force"):
        policies.loc[len(policies)] = {
            "policy_no": policy_no, "signed_date": dt.date(2024, 1, 5),
            "inception_date": dt.date(2024, 1, 10), "broker": "Momentum Consult",
            "status": "in_force", "insurable_interest": "own_life",
        }
        lives.loc[len(lives)] = {
            "life_id": f"{policy_no}-L1", "policy_no": policy_no,
            "id_number_masked": "8001015*******7", "dob": dt.date(1980, 1, 1),
            "occupation_at_inception": occ_inception, "smoker_flag": False,
            "province": "Gauteng", "sensitivity": "L2",
        }
        benefits.loc[len(benefits)] = {
            "benefit_id": f"{policy_no}-B", "policy_no": policy_no,
            "benefit_type": benefit_type, "sum_assured": 1_800_000.0,
            "status": benefit_status, "loadings": "", "exclusions": "",
        }

    # ---- DS1: CLM-DEATH-CLEAN — clean death claim, recommend pay ----
    p = "POL-DEATH-CLEAN"
    add_policy(p, "Accountant", "death")
    claims.loc[len(claims)] = {
        "claim_no": "CLM-DEATH-CLEAN", "policy_no": p, "claim_type": "death",
        "event_date": dt.date(2026, 5, 20), "lodge_date": dt.date(2026, 5, 28),
        "state": "in_assessment", "occupation_at_claim": "Accountant",
        "decision": None, "decided_date": None, "assessor": "assessor_03",
        "risk_score": 0.08, "is_ntu": False,
    }
    for st, ts in [("initiated", dt.date(2026, 5, 20)), ("lodged", dt.date(2026, 5, 28)),
                   ("in_assessment", dt.date(2026, 5, 30))]:
        events.loc[len(events)] = {"claim_no": "CLM-DEATH-CLEAN", "event": st, "event_ts": ts}
    for code, desc in REQUIREMENTS_BY_TYPE["death"]:
        reqs.loc[len(reqs)] = {"claim_no": "CLM-DEATH-CLEAN", "code": code, "description": desc,
                               "status": "received", "requested_ts": dt.date(2026, 5, 21),
                               "received_ts": dt.date(2026, 5, 26)}
    docs.loc[len(docs)] = {"doc_id": "DOC-DEATHCLEAN-1", "claim_no": "CLM-DEATH-CLEAN",
                           "doc_type": "death_certificate", "filenet_ref": "FN-500001",
                           "parsed_text": "REPUBLIC OF SOUTH AFRICA — DEATH CERTIFICATE. Cause of death: natural causes. Date of event 2026-05-20. All particulars consistent with policy records.",
                           "extracted_json": json.dumps({"doc_type": "death_certificate", "claim_no": "CLM-DEATH-CLEAN", "cause": "natural"})}
    tps.loc[len(tps)] = {"claim_no": "CLM-DEATH-CLEAN", "source": "VPD",
                         "result_json": json.dumps({"deceased_confirmed": True}),
                         "result_summary": "deceased confirmed", "checked_ts": dt.date(2026, 5, 22)}

    # ---- DS2: CLM-DISAB-DISCREP — occupation mismatch + missing specialist report ----
    p = "POL-DISAB-DISCREP"
    add_policy(p, "Clerk", "disability")           # inception occupation = Clerk
    claims.loc[len(claims)] = {
        "claim_no": "CLM-DISAB-DISCREP", "policy_no": p, "claim_type": "disability",
        "event_date": dt.date(2026, 6, 2), "lodge_date": dt.date(2026, 6, 12),
        "state": "in_assessment", "occupation_at_claim": "Boilermaker",   # mismatch
        "decision": None, "decided_date": None, "assessor": "assessor_07",
        "risk_score": 0.34, "is_ntu": False,
    }
    for st, ts in [("initiated", dt.date(2026, 6, 2)), ("lodged", dt.date(2026, 6, 12)),
                   ("in_assessment", dt.date(2026, 6, 14))]:
        events.loc[len(events)] = {"claim_no": "CLM-DISAB-DISCREP", "event": st, "event_ts": ts}
    for k, (code, desc) in enumerate(REQUIREMENTS_BY_TYPE["disability"]):
        # specialist report is the outstanding one
        received = code != "REQ-SPECIALIST"
        reqs.loc[len(reqs)] = {"claim_no": "CLM-DISAB-DISCREP", "code": code, "description": desc,
                               "status": "received" if received else "outstanding",
                               "requested_ts": dt.date(2026, 6, 3),
                               "received_ts": dt.date(2026, 6, 9) if received else None}
    docs.loc[len(docs)] = {"doc_id": "DOC-91", "claim_no": "CLM-DISAB-DISCREP",
                           "doc_type": "op_form", "filenet_ref": "FN-500091",
                           "parsed_text": "CLAIM (OP) FORM for CLM-DISAB-DISCREP. Claimant states current occupation: Boilermaker (heavy manual trade). Declaration signed.",
                           "extracted_json": json.dumps({"doc_type": "op_form", "claim_no": "CLM-DISAB-DISCREP", "occupation": "Boilermaker"})}
    tps.loc[len(tps)] = {"claim_no": "CLM-DISAB-DISCREP", "source": "bank",
                         "result_json": json.dumps({"account_active": True}),
                         "result_summary": "account confirmed", "checked_ts": dt.date(2026, 6, 5)}

    # ---- DS3: CLM-SUSPECT-FRAUD — early claim + benefit-status mismatch ----
    p = "POL-SUSPECT-FRAUD"
    add_policy(p, "Driver", "death", benefit_status="lapsed")   # benefit status mismatch
    claims.loc[len(claims)] = {
        "claim_no": "CLM-SUSPECT-FRAUD", "policy_no": p, "claim_type": "death",
        "event_date": dt.date(2024, 3, 1),      # shortly after 2024-01-10 inception
        "lodge_date": dt.date(2024, 3, 20), "state": "in_assessment",
        "occupation_at_claim": "Driver", "decision": None, "decided_date": None,
        "assessor": "assessor_11", "risk_score": 0.83, "is_ntu": False,
    }
    for st, ts in [("initiated", dt.date(2024, 3, 1)), ("lodged", dt.date(2024, 3, 20)),
                   ("in_assessment", dt.date(2024, 3, 22))]:
        events.loc[len(events)] = {"claim_no": "CLM-SUSPECT-FRAUD", "event": st, "event_ts": ts}
    for code, desc in REQUIREMENTS_BY_TYPE["death"]:
        reqs.loc[len(reqs)] = {"claim_no": "CLM-SUSPECT-FRAUD", "code": code, "description": desc,
                               "status": "received", "requested_ts": dt.date(2024, 3, 2),
                               "received_ts": dt.date(2024, 3, 10)}
    docs.loc[len(docs)] = {"doc_id": "DOC-SUSPECT-1", "claim_no": "CLM-SUSPECT-FRAUD",
                           "doc_type": "death_certificate", "filenet_ref": "FN-500777",
                           "parsed_text": "DEATH CERTIFICATE. Date of event 2024-03-01 — 50 days after policy inception (2024-01-10). Cause pending confirmation.",
                           "extracted_json": json.dumps({"doc_type": "death_certificate", "claim_no": "CLM-SUSPECT-FRAUD", "days_since_inception": 50})}
    tps.loc[len(tps)] = {"claim_no": "CLM-SUSPECT-FRAUD", "source": "other_insurer",
                         "result_json": json.dumps({"claims_last_3y": 2}),
                         "result_summary": "2 prior claims at other insurers", "checked_ts": dt.date(2024, 3, 5)}

    return data


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------
def build_all() -> dict[str, pd.DataFrame]:
    rng = random.Random(SEED)
    np.random.seed(SEED)

    policies = gen_policies(rng, N_POLICIES)
    lives = gen_lives(rng, policies)
    role_players = gen_role_players(rng, policies)
    benefits = gen_benefits(rng, policies)
    claims, events, reqs = gen_claims(rng, policies, lives)
    docs = gen_documents(rng, claims)
    emails = gen_emails(rng, claims)
    tps = gen_tp_verifications(rng, claims)
    rules = gen_claimability_rules()

    data = {
        "policy": policies, "life": lives, "role_player": role_players,
        "benefit": benefits, "claim": claims, "claim_event": events,
        "requirement": reqs, "document": docs, "email": emails,
        "tp_verification": tps, "claimability_rule": rules,
    }
    data = append_seeded_scenarios(data)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Build in-memory and print row counts only.")
    ap.add_argument("--catalog", default=None, help="Override target catalog.")
    args = ap.parse_args()

    data = build_all()
    print("Synthetic data generated (row counts):")
    for name, df in data.items():
        print(f"  {name:20s} {len(df):>8,d}")
    for s in ("CLM-DEATH-CLEAN", "CLM-DISAB-DISCREP", "CLM-SUSPECT-FRAUD"):
        assert (data["claim"].claim_no == s).any(), f"Missing seeded scenario {s}"
    print("Seeded scenarios present: CLM-DEATH-CLEAN, CLM-DISAB-DISCREP, CLM-SUSPECT-FRAUD")

    if args.dry_run:
        return

    # In-workspace write path (Spark available). Writes each frame to bronze.
    from pyspark.sql import SparkSession
    from .config import CATALOG, SCHEMAS
    catalog = args.catalog or CATALOG
    spark = SparkSession.builder.getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{SCHEMAS['bronze']}")
    for name, df in data.items():
        sdf = spark.createDataFrame(df)
        target = f"{catalog}.{SCHEMAS['bronze']}.{name}"
        sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(target)
        print(f"  wrote {target} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
