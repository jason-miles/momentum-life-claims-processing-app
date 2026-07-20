# Underwriting Demo Runbook — Momentum Life (On-site working session)

A click-by-click walk of the **Underwriting Modernization** demo, following the
9-beat storyboard from `Underwriting_Modernization_Requirements_v1.1`. Audience:
Marsel Blom (BA/process owner), Zelda Ngobeni, Leon du Plessis, Chris Steenkamp.
Databricks: Jason (SA), Kyle Ross. Session: Tuesday 1pm SAST.

> **Golden rule (say it up front):** we are **not** replacing AS400 or IBM BPM.
> Databricks owns the *governed read layer + AI assist + operational analytics*.
> Lead with the swivel-chair problem; land on analytics; don't oversell.

**App:** https://momentum-claims-portal-7474654808133980.aws.databricksapps.com
**Pre-warm:** open the 3 seeded UW cases once before the room (synopses cache →
instant live). Warehouse is warm (Medium, 2 clusters, 60-min auto-stop).

---

## Beat 1 — Platform overview (5–10 min, slides)
One platform: Lakehouse + Unity Catalog + Mosaic AI + AI/BI + Apps. "You don't
need another tool." (Answers Leon's question directly.)

## Beat 2 — Governance wedge
Open **Admin Console**. Show the data-product catalog (governed gold objects +
row counts) spanning both `momentum_uw_*` and `momentum_claims_*`, and the
residency note. Message: *this is the data team's stated entry point — catalog,
lineage, consistent metrics as data products (R5.1).* 

## Beat 3 — Intake & risk capture
Note the journey types on any case (Magnum digital / broker / tele). Maps to
Myriad underwriting journeys — the first-pass routing captured as data.

## Beat 4 + 5 — Unified case view + AI assist (THE HERO BEAT)
Open **Underwriting Co-Pilot** → select **`UW-COUNTEROFFER`**.
- **Left — Unified Case View**: one screen, keyed on policy number, pulling
  AS400 (policy, sum-at-risk R4.2m, life), BPM (task/SLA), requirements, and the
  **underwriter notepad** — *no swivel chair* (R2.1).
- **Right — AI Risk Synopsis**: the agent drafts a source-cited risk assessment
  (smoker, class C manual, impaired risk → **+75% loading counteroffer**),
  **advisory only, never a bind/decline**. 
  > *"This is Leon's Claude + pgvector POC — re-built natively on Mosaic AI
  > Vector Search + an agent, governed by Unity Catalog (R2.2/R2.3). Same idea,
  > now on one governed platform."* — the objection-neutralising line.

## Beat 6 — NTU predict → act (the worked example)
Still in **Underwriting Co-Pilot**, select **`UW-NTU-RISK`**.
- **NTU Intervention panel**: **91% NTU propensity**, 3 requirements outstanding
  61 days, bucket = *requirements never returned*. Recommended interventions:
  nudge the broker / nurse home visit / simplify requirements / proactive call.
- Message: *compute it (governed data product), predict it (score at the moment
  requirements are set — features: requirement type/count, journey, sum-at-risk
  band, age, time-in-diary, broker), act on it before the case goes quiet.*

## Beat 7 — Operational reporting (displace Power BI)
Open **UW Analytics**.
- KPI tiles: **STP 29.9%**, **NTU 28.9%**, **turnaround 19.1 days**.
- **First-pass journey split** (donut) + **manual decision split** (bar, incl.
  counteroffers) — R4.1/R4.3.
- **NTU drop-off** (bar): *"almost two-thirds is requirements that never come
  back — a single, addressable failure mode, not random churn"* (matches the
  29% worked example: 62/19/12/7). At-risk table ranked by propensity × SAR.
- **Requirements analytics**: which evidence, return rate, avg days (R4.2).
- Message: *this is the Power BI ops roll-up, reproduced as governed AI/BI at no
  per-seat cost (R4.6, R6.4).* 

## Beat 8 — Genie (democratize)
On **UW Analytics**, use **"Ask the Underwriting Analyst"**. Ask the scripted
question verbatim:
> *"Which open cases set requirements over 14 days ago with no result returned,
> ranked by sum at risk?"*
Then: *"What percentage of applications go straight-through?"* Message:
*consistent business terminology as data products; anyone can ask (R2.4).* 

## Beat 9 — Close on phasing
- **P1** — analytics wedge (govern data, displace Power BI ops roll-ups): now.
- **P2** — unified case view + AI assist (Vector Search/RAG over notepad,
  FileNet, email; agent; NTU prediction): validated pilot.
- **P3** — operational ambition (near-real-time backbone; Lakebase/Apps in the
  underwriter's flow). **Not an AS400/BPM replacement claim.**

---

## Seeded scenarios (fixed policy numbers)
| Policy | Story | Shows |
| --- | --- | --- |
| `UW-CLEAN-FASTTRACK` | Healthy, fast-track, standard accept | STP happy path, no requirements |
| `UW-COUNTEROFFER` | Impaired (smoker, class C) → +75% loading, not accepted | AI risk synopsis + counteroffer + NTU (counteroffer bucket) |
| `UW-NTU-RISK` | Bloods/HIV/ECG requested, 61 days, never returned | 91% NTU propensity + intervention panel (hero) |

## Confirm-before-ROI (open questions to raise, not answer)
Underwriter headcount (15–50?), AS400 (IBM i) CDC mechanism/latency, FileNet
volume/formats, agreed definition of "real-time", Power BI coexist-or-replace.

## If something misbehaves
- Synopsis slow first time → it's Claude (~30s); the seeded cases are pre-warmed
  so they're instant. The rest of the page never blocks on it.
- Genie odd answer → fall back to the on-screen charts/tables.
- Warehouse cold → shouldn't happen (60-min auto-stop); pre-warm with any page.
