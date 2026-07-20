"""Deterministic synthetic-data generator for the Momentum Life UNDERWRITING demo.

Models the new-business underwriting journey described in the requirements
(Underwriting_Modernization_Requirements_v1.1):

  application   one new-business case, keyed on policy_no (the join key)
  uw_life       the life underwritten (age, smoker, occupation class, sum-at-risk)
  first_pass    Decision Manager first-pass outcome (4 journeys)
  uw_requirement  evidence requested (bloods/ECG/GP/nurse/HIV/cotinine) + timing
  uw_decision   manual underwriter outcome (4 outcomes incl. counteroffer)
  uw_case_note  underwriter notepad free-text (RAG/agent corpus)
  bpm_task      case/task state for SLA + throughput analytics
  ntu           Not-Taken-Up records with the 4 composition buckets + propensity

Everything is fabricated — no real PII. Deterministic via SEED.

Three seeded scenarios (known policy numbers) drive the demo:
  UW-CLEAN-FASTTRACK   healthy, fast-track, standard accept
  UW-COUNTEROFFER      raised BP + cholesterol -> premium loading counteroffer
  UW-NTU-RISK          bloods requested 20+ days ago, never returned -> high NTU risk
"""
from __future__ import annotations

import argparse
import datetime as dt
import random

import numpy as np
import pandas as pd

SEED = 20260617  # requirements doc date
BASE_DATE = dt.date(2026, 6, 15)

N_APPLICATIONS = 4_000

# First-pass journey split (Decision Manager) — the 4 outcomes.
JOURNEY_MIX = {
    "auto_requirements": 0.42,   # rules auto-set + request evidence, no human
    "refer_underwriter": 0.28,   # rules suggest, flag for human review first
    "fast_track": 0.20,          # healthy enough, accept, skip human
    "tele_underwriting": 0.10,   # client-direct phone, immediate decision
}

# Manual underwriter decision outcomes (for cases that reach a decision).
DECISION_MIX = {
    "standard_accept": 0.58,
    "counteroffer": 0.22,        # exclusion or loading -> new quote
    "more_requirements": 0.08,   # avoided where possible (poor CX)
    "decline_defer_postpone": 0.12,
}

# Overall share of applications that end Not-Taken-Up (spec worked example ~29%).
NTU_RATE = 0.29
# NTU composition buckets (must sum to 1.0) — from slide 5.
NTU_BUCKETS = {
    "requirements_never_returned": 0.62,
    "counteroffer_not_accepted": 0.19,
    "withdrew_at_quote": 0.12,
    "postpone_lapsed": 0.07,
}

BENEFIT_TYPES = ["death", "disability", "critical_illness", "income", "combined"]
CHANNELS = ["Magnum digital", "Broker", "Tele", "Direct"]
BROKERS = ["Momentum Consult", "PSG Wealth", "Alexforbes", "Liberty Advisers",
           "NMG Benefits", "Independent Broker Network", "Direct"]
PROVINCES = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Free State", "Limpopo"]
PROVINCE_W = [0.30, 0.20, 0.18, 0.12, 0.10, 0.10]
OCCUPATION_CLASS = ["A (professional)", "B (skilled)", "C (manual)", "D (hazardous)"]
OCCUPATION_CLASS_W = [0.40, 0.32, 0.20, 0.08]

# Evidence / requirement catalogue (code, description, typical trigger).
REQUIREMENT_CATALOG = [
    ("REQ-BLOODS", "Full blood panel"),
    ("REQ-HIV", "HIV test"),
    ("REQ-COTININE", "Cotinine (smoker) test"),
    ("REQ-ECG", "Resting ECG"),
    ("REQ-GP", "GP / attending physician report"),
    ("REQ-NURSE", "Nurse home visit"),
    ("REQ-CHOL", "Cholesterol / lipogram"),
    ("REQ-FIN", "Financial underwriting / income proof"),
]

UNDERWRITERS = [f"uw_{i:02d}" for i in range(1, 17)]  # ~16 production underwriters (spec)

# Sum-at-risk bands (ZAR).
def _sum_at_risk(rng: random.Random) -> float:
    v = float(np.round(np.random.lognormal(mean=14.0, sigma=0.75), -3))
    return min(max(v, 100_000), 25_000_000)


def _sar_band(v: float) -> str:
    if v < 1_000_000: return "<R1m"
    if v < 3_000_000: return "R1m-3m"
    if v < 10_000_000: return "R3m-10m"
    return ">R10m"


def _weighted(rng: random.Random, mapping: dict[str, float]) -> str:
    keys = list(mapping)
    return rng.choices(keys, weights=[mapping[k] for k in keys], k=1)[0]


def _rand_date(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=rng.randint(0, max((end - start).days, 1)))


def build_all() -> dict[str, pd.DataFrame]:
    rng = random.Random(SEED)
    np.random.seed(SEED)

    apps, lives, first_pass = [], [], []
    reqs, decisions, notes, tasks, ntus = [], [], [], [], []

    for i in range(1, N_APPLICATIONS + 1):
        policy_no = f"UWP-{i:05d}"
        submitted = _rand_date(rng, dt.date(2026, 1, 1), BASE_DATE)
        channel = rng.choices(CHANNELS, weights=[0.5, 0.35, 0.1, 0.05], k=1)[0]
        broker = "Direct" if channel in ("Tele", "Direct") else rng.choice(BROKERS)
        benefit = rng.choice(BENEFIT_TYPES)
        sar = _sum_at_risk(rng)
        age = rng.randint(18, 68)
        smoker = rng.random() < 0.24
        occ_class = rng.choices(OCCUPATION_CLASS, weights=OCCUPATION_CLASS_W, k=1)[0]
        province = rng.choices(PROVINCES, weights=PROVINCE_W, k=1)[0]
        journey = _weighted(rng, JOURNEY_MIX)

        # health/risk signal (0=healthy .. 1=impaired), drives requirements + decision
        risk = min(1.0, max(0.0, rng.betavariate(2, 5)
                            + (0.15 if smoker else 0) + (age - 40) / 200
                            + (0.12 if occ_class.startswith(("C", "D")) else 0)))

        apps.append({
            "policy_no": policy_no, "submitted_date": submitted, "channel": channel,
            "broker": broker, "benefit_type": benefit, "sum_at_risk": sar,
            "sar_band": _sar_band(sar), "province": province, "journey_type": journey,
            "underwriter": rng.choice(UNDERWRITERS),
        })
        lives.append({
            "policy_no": policy_no, "age": age, "smoker_flag": smoker,
            "occupation_class": occ_class, "id_number_masked": _masked_id(rng, age),
            "risk_score": round(risk, 3),
        })

        # first-pass record
        fp_ts = submitted + dt.timedelta(days=rng.randint(0, 2))
        first_pass.append({
            "policy_no": policy_no, "journey_type": journey,
            "first_pass_ts": fp_ts,
            "auto_requirements_set": journey == "auto_requirements",
            "referred_to_uw": journey == "refer_underwriter",
        })

        # requirements: fast-track/tele usually none; others get 1-4 by risk
        n_reqs = 0
        if journey in ("auto_requirements", "refer_underwriter"):
            n_reqs = 1 + int(round(risk * 3))
        elif journey == "tele_underwriting":
            n_reqs = rng.choice([0, 0, 1])
        chosen = rng.sample(REQUIREMENT_CATALOG, k=min(n_reqs, len(REQUIREMENT_CATALOG)))
        # decide NTU up-front so requirement return can reflect it
        is_ntu = rng.random() < NTU_RATE
        ntu_bucket = _weighted(rng, NTU_BUCKETS) if is_ntu else None

        for code, desc in chosen:
            requested = fp_ts + dt.timedelta(days=rng.randint(1, 3))
            # if NTU-by-requirements, some requirements never return
            never = is_ntu and ntu_bucket == "requirements_never_returned" and rng.random() < 0.7
            returned = None if never else requested + dt.timedelta(days=rng.randint(3, 21))
            reqs.append({
                "policy_no": policy_no, "code": code, "description": desc,
                "requested_ts": requested, "returned_ts": returned,
                "status": "outstanding" if returned is None else "returned",
            })

        # decision (only for cases that get far enough and aren't withdrawn/never-returned)
        decided = None
        decision_outcome = None
        loading_pct = None
        exclusion = None
        reached_decision = journey in ("fast_track", "tele_underwriting") or (
            not is_ntu or ntu_bucket in ("counteroffer_not_accepted", "postpone_lapsed"))
        if reached_decision:
            if journey == "fast_track":
                decision_outcome = "standard_accept"
            else:
                decision_outcome = _weighted(rng, DECISION_MIX)
            base = max(fp_ts, max([r["requested_ts"] for r in reqs if r["policy_no"] == policy_no] or [fp_ts]))
            decided = base + dt.timedelta(days=rng.randint(1, 12))
            if decision_outcome == "counteroffer":
                if rng.random() < 0.6:
                    loading_pct = rng.choice([25, 50, 75, 100, 150])
                else:
                    exclusion = rng.choice(["lower back", "cardiac", "hazardous pursuits",
                                            "mental health", "left knee"])
            decisions.append({
                "policy_no": policy_no, "outcome": decision_outcome,
                "decided_ts": decided, "loading_pct": loading_pct,
                "exclusion": exclusion,
                "counteroffer_accepted": (None if decision_outcome != "counteroffer"
                                          else (ntu_bucket != "counteroffer_not_accepted")),
            })

        # NTU record
        if is_ntu:
            ntus.append({
                "policy_no": policy_no, "ntu_bucket": ntu_bucket,
                "sar_band": _sar_band(sar), "journey_type": journey,
                "sum_at_risk": sar,
                "days_in_diary": rng.randint(14, 60),
            })

        # underwriter notepad note (free text — the RAG/agent corpus)
        notes.append({
            "policy_no": policy_no,
            "note_ts": (decided or fp_ts),
            "author": apps[-1]["underwriter"],
            "note_text": _note_text(rng, journey, decision_outcome, smoker, occ_class,
                                    age, sar, loading_pct, exclusion, risk),
        })

        # BPM task state (SLA + throughput)
        opened = fp_ts
        closed = decided if decided else (None if is_ntu else fp_ts + dt.timedelta(days=rng.randint(5, 40)))
        sla_days = 15
        cycle = (closed - opened).days if closed else (BASE_DATE - opened).days
        tasks.append({
            "policy_no": policy_no, "assignee": apps[-1]["underwriter"],
            "opened_ts": opened, "closed_ts": closed,
            "status": "closed" if closed else "open",
            "cycle_days": cycle, "sla_days": sla_days,
            "sla_breach": cycle > sla_days,
        })

    data = {
        "application": pd.DataFrame(apps),
        "uw_life": pd.DataFrame(lives),
        "first_pass": pd.DataFrame(first_pass),
        "uw_requirement": pd.DataFrame(reqs),
        "uw_decision": pd.DataFrame(decisions),
        "uw_case_note": pd.DataFrame(notes),
        "bpm_task": pd.DataFrame(tasks),
        "ntu": pd.DataFrame(ntus),
    }
    _append_seeded(data)
    return data


def _masked_id(rng: random.Random, age: int) -> str:
    yy = (2026 - age) % 100
    return f"{yy:02d}{rng.randint(1,12):02d}{rng.randint(1,28):02d}*******{rng.randint(0,9)}"


def _note_text(rng, journey, outcome, smoker, occ, age, sar, loading, exclusion, risk) -> str:
    bits = [f"Life age {age}, occupation class {occ}, {'smoker' if smoker else 'non-smoker'}."]
    bits.append(f"Sum at risk R{sar:,.0f} on a {journey.replace('_',' ')} journey.")
    if risk > 0.5:
        bits.append("Impaired risk profile noted; elevated BP and cholesterol on bloods.")
    if outcome == "counteroffer":
        if loading:
            bits.append(f"Counteroffer issued: +{loading}% premium loading pending client acceptance.")
        elif exclusion:
            bits.append(f"Counteroffer issued: {exclusion} exclusion applied.")
    elif outcome == "decline_defer_postpone":
        bits.append("Referred for decline/postpone pending further evidence.")
    elif outcome == "standard_accept":
        bits.append("Standard rates accepted, no loading.")
    return " ".join(bits)


def _append_seeded(data: dict[str, pd.DataFrame]) -> None:
    """Three fixed demo cases with known policy numbers."""
    def add(df_key, row):
        df = data[df_key]
        df.loc[len(df)] = row

    # UW-CLEAN-FASTTRACK — healthy, fast-track, standard accept
    p = "UW-CLEAN-FASTTRACK"
    add("application", {"policy_no": p, "submitted_date": dt.date(2026, 6, 1), "channel": "Magnum digital",
                        "broker": "Momentum Consult", "benefit_type": "death", "sum_at_risk": 1_500_000.0,
                        "sar_band": "R1m-3m", "province": "Gauteng", "journey_type": "fast_track", "underwriter": "uw_03"})
    add("uw_life", {"policy_no": p, "age": 32, "smoker_flag": False, "occupation_class": "A (professional)",
                    "id_number_masked": "9406015*******7", "risk_score": 0.08})
    add("first_pass", {"policy_no": p, "journey_type": "fast_track", "first_pass_ts": dt.date(2026, 6, 2),
                       "auto_requirements_set": False, "referred_to_uw": False})
    add("uw_decision", {"policy_no": p, "outcome": "standard_accept", "decided_ts": dt.date(2026, 6, 2),
                        "loading_pct": None, "exclusion": None, "counteroffer_accepted": None})
    add("uw_case_note", {"policy_no": p, "note_ts": dt.date(2026, 6, 2), "author": "uw_03",
                         "note_text": "Life age 32, class A professional, non-smoker. Sum at risk R1,500,000 on a fast track journey. Clean bloods, standard rates accepted, no loading."})
    add("bpm_task", {"policy_no": p, "assignee": "uw_03", "opened_ts": dt.date(2026, 6, 2),
                     "closed_ts": dt.date(2026, 6, 3), "status": "closed", "cycle_days": 1, "sla_days": 15, "sla_breach": False})

    # UW-COUNTEROFFER — impaired, loading counteroffer
    p = "UW-COUNTEROFFER"
    add("application", {"policy_no": p, "submitted_date": dt.date(2026, 5, 20), "channel": "Broker",
                        "broker": "PSG Wealth", "benefit_type": "disability", "sum_at_risk": 4_200_000.0,
                        "sar_band": "R3m-10m", "province": "Western Cape", "journey_type": "refer_underwriter", "underwriter": "uw_07"})
    add("uw_life", {"policy_no": p, "age": 51, "smoker_flag": True, "occupation_class": "C (manual)",
                    "id_number_masked": "7503015*******3", "risk_score": 0.71})
    add("first_pass", {"policy_no": p, "journey_type": "refer_underwriter", "first_pass_ts": dt.date(2026, 5, 22),
                       "auto_requirements_set": False, "referred_to_uw": True})
    for code, desc in [("REQ-BLOODS", "Full blood panel"), ("REQ-CHOL", "Cholesterol / lipogram"), ("REQ-ECG", "Resting ECG")]:
        add("uw_requirement", {"policy_no": p, "code": code, "description": desc,
                               "requested_ts": dt.date(2026, 5, 23), "returned_ts": dt.date(2026, 5, 30), "status": "returned"})
    add("uw_decision", {"policy_no": p, "outcome": "counteroffer", "decided_ts": dt.date(2026, 6, 4),
                        "loading_pct": 75, "exclusion": None, "counteroffer_accepted": False})
    add("uw_case_note", {"policy_no": p, "note_ts": dt.date(2026, 6, 4), "author": "uw_07",
                         "note_text": "Life age 51, class C manual, smoker. Sum at risk R4,200,000 on a refer to underwriter journey. Raised blood pressure and cholesterol on bloods; impaired risk. Counteroffer issued: +75% premium loading pending client acceptance."})
    add("bpm_task", {"policy_no": p, "assignee": "uw_07", "opened_ts": dt.date(2026, 5, 22),
                     "closed_ts": dt.date(2026, 6, 4), "status": "closed", "cycle_days": 13, "sla_days": 15, "sla_breach": False})
    add("ntu", {"policy_no": p, "ntu_bucket": "counteroffer_not_accepted", "sar_band": "R3m-10m",
                "journey_type": "refer_underwriter", "sum_at_risk": 4_200_000.0, "days_in_diary": 22})

    # UW-NTU-RISK — bloods requested 20+ days ago, never returned
    p = "UW-NTU-RISK"
    add("application", {"policy_no": p, "submitted_date": dt.date(2026, 5, 18), "channel": "Broker",
                        "broker": "Alexforbes", "benefit_type": "critical_illness", "sum_at_risk": 8_000_000.0,
                        "sar_band": "R3m-10m", "province": "KwaZulu-Natal", "journey_type": "auto_requirements", "underwriter": "uw_11"})
    add("uw_life", {"policy_no": p, "age": 44, "smoker_flag": False, "occupation_class": "B (skilled)",
                    "id_number_masked": "8202015*******1", "risk_score": 0.38})
    add("first_pass", {"policy_no": p, "journey_type": "auto_requirements", "first_pass_ts": dt.date(2026, 5, 19),
                       "auto_requirements_set": True, "referred_to_uw": False})
    for code, desc in [("REQ-BLOODS", "Full blood panel"), ("REQ-HIV", "HIV test"), ("REQ-ECG", "Resting ECG")]:
        add("uw_requirement", {"policy_no": p, "code": code, "description": desc,
                               "requested_ts": dt.date(2026, 5, 20), "returned_ts": None, "status": "outstanding"})
    add("uw_case_note", {"policy_no": p, "note_ts": dt.date(2026, 5, 20), "author": "uw_11",
                         "note_text": "Life age 44, class B skilled, non-smoker. Sum at risk R8,000,000 on an auto requirements journey. Bloods, HIV and ECG requested; awaiting results, case quiet in diary."})
    add("bpm_task", {"policy_no": p, "assignee": "uw_11", "opened_ts": dt.date(2026, 5, 19),
                     "closed_ts": None, "status": "open", "cycle_days": 27, "sla_days": 15, "sla_breach": True})
    add("ntu", {"policy_no": p, "ntu_bucket": "requirements_never_returned", "sar_band": "R3m-10m",
                "journey_type": "auto_requirements", "sum_at_risk": 8_000_000.0, "days_in_diary": 27})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = build_all()
    print("Underwriting synthetic data (row counts):")
    for k, df in data.items():
        print(f"  {k:16s} {len(df):>8,d}")
    for s in ("UW-CLEAN-FASTTRACK", "UW-COUNTEROFFER", "UW-NTU-RISK"):
        assert (data["application"].policy_no == s).any(), f"missing {s}"
    print("Seeded scenarios present.")


if __name__ == "__main__":
    main()
