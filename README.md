# Momentum Life — Underwriting & Claims Intelligence Portal

A demo-grade Databricks build for **Momentum Life** (the life-insurance business
unit of Momentum Group, Centurion, South Africa) spanning **two domains on one
governed lakehouse**:

- **Underwriting** — new-business risk assessment: a unified case view keyed on
  policy number (AS400 + BPM + notepad + evidence), an AI risk synopsis with
  Vector Search retrieval over underwriter notes, and NTU (Not-Taken-Up)
  drop-off *prediction and intervention*.
- **Claims** — assessment: a unified case view, an AI-drafted source-cited
  synopsis with discrepancy detection, drop-off analytics, and governed reporting
  that displaces per-seat Power BI.

Everything runs on **synthetic data — no real PII.** Live app (React + FastAPI on
Databricks Apps):
`https://momentum-claims-portal-7474654808133980.aws.databricksapps.com`

---

## What's in the box

Both domains share the same substrate: a UC-governed medallion, UC Metric Views,
UC-function agent tools, Mosaic AI Vector Search RAG, a Claude synopsis agent, a
Genie space, and an enterprise-grade React UI.

| Area | Underwriting | Claims |
| --- | --- | --- |
| **Co-Pilot** | Risk workbench: NTU-ranked queue + unified case view + AI risk synopsis + NTU intervention | Genie NL assistant over all claims |
| **Executive View** | STP / NTU / turnaround KPIs + journey & decision mix + recoverable-value card | Cycle time / NTU / SLA KPIs + decision donut + province |
| **Analytics** | Journey split, decision split, NTU funnel, requirement analytics | Inbox (paginated), NTU/Ops, Fraud Workbench `[MOCKED]` |
| **AI synopsis** | Claude via ai_query + **Vector Search RAG** over notepad (`[VS:notes]`) | Claude + discrepancy flags + **Vector Search RAG** over docs (`[VS:docs]`) |
| **Genie space** | "Momentum Underwriting Analyst" | "Momentum Claims Analyst" |
| **Metric Views** | STP rate, turnaround, NTU rate | cycle time, NTU rate, SLA, decision split, pre-lodge days, throughput |

Front door: a cross-domain **Executive Overview** with both portfolios side by side.

Scope tags: `[MVP]` fully functional on synthetic data · `[MOCKED]` present for
narrative, canned data (fraud scores) · `[PHASE 2+]` named, not built (live CDC,
FileNet/email ingestion).

---

## Seeded demo scenarios (fixed IDs)

**Claims** — in `gold.claim_synopsis_view`:

| `claim_no` | Planted condition | Synopsis produces |
| --- | --- | --- |
| `CLM-DEATH-CLEAN` | Benefits in force, reqs complete, no mismatch | Clean cited synopsis → **PAY** |
| `CLM-DISAB-DISCREP` | occ@claim *Boilermaker* ≠ inception *Clerk*; specialist report outstanding | Flags mismatch + missing report → **REFER/PEND** |
| `CLM-SUSPECT-FRAUD` | Event 50d after inception; benefit lapsed; risk 0.83 | Early-claim + benefit flags → **INVESTIGATE** |

**Underwriting** — in `momentum_uw_gold.uw_case_view`:

| `policy_no` | Planted condition | Co-Pilot shows |
| --- | --- | --- |
| `UW-CLEAN-FASTTRACK` | Healthy, fast-track | Standard accept, low NTU |
| `UW-COUNTEROFFER` | Impaired (smoker, class C) | +75% loading counteroffer, not accepted |
| `UW-NTU-RISK` | Bloods/HIV/ECG requested, 61 days, never returned | **91% NTU propensity** + intervention list |

---

## Physical layout

Co-located medallion schemas in `elexon_app_for_settlement_acc_catalog` (the demo
workspace can't create a dedicated catalog — see [docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md)):

```
momentum_claims_{bronze,silver,gold,ai,ops}      # claims domain
momentum_uw_{bronze,silver,gold,ai}              # underwriting domain
```

## Repo structure

```
momentum-claims-demo/
├── databricks.yml              # DAB root (targets: demo, prod)
├── resources/                  # jobs (momentum_claims_build, momentum_uw_build), app
├── src/
│   ├── synthetic_data/         # deterministic generators (claims + underwriting)
│   ├── pipelines/{silver,gold,uw}/  # consolidated build SQL for the DAB jobs
│   ├── ai/{tools,agents,eval}  # UC tools, synopsis agent, VS index builders, eval
│   └── app_react/              # React + FastAPI "Intelligence Portal" (deployed)
│       ├── server/             # FastAPI: data/uw_data, agent/genie clients, routes
│       └── frontend/           # React + Vite + recharts SPA (Momentum brand)
├── sql/                        # per-object SQL (source of truth)
├── scripts/                    # retarget_sql, teardown, smoke_verify
├── dashboards/                 # AI/BI dashboard JSON (claims + underwriting)
├── docs/                       # deployment, production, runbooks, POC traceability
└── logo/                       # Momentum brand assets
```

> Note: `src/app/` (the original Streamlit app) is kept for reference; the
> deployed app is `src/app_react/`.

## Deploy

See [docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md) (demo) and
[docs/PRODUCTION_DEPLOY.md](docs/PRODUCTION_DEPLOY.md) (eu-west-1 prod). TL;DR:

```bash
databricks bundle validate -t demo -p <profile>
databricks bundle deploy   -t demo -p <profile>
databricks bundle run momentum_claims_build -t demo -p <profile>
databricks bundle run momentum_uw_build     -t demo -p <profile>
python src/ai/build_indexes.py       # claims Vector Search index
python src/ai/build_uw_index.py      # underwriting Vector Search index
# app: build frontend, copy dist -> src/app_react/webroot, sync, apps deploy
```

Ops scripts: `scripts/smoke_verify.sql` (health check), `scripts/teardown.sql`
(reset), `scripts/retarget_sql.py` (re-point to a prod catalog).

## Demo scripts

- [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md) — claims walk-through
- [docs/UW_DEMO_RUNBOOK.md](docs/UW_DEMO_RUNBOOK.md) — underwriting 9-beat storyboard
- [docs/UW_POC_TRACEABILITY.md](docs/UW_POC_TRACEABILITY.md) — requirements → evidence map

## Data residency

`af-south-1` is not a Databricks region; the residency-compliant production home
is **eu-west-1 (Ireland)** — not the USA. The demo uses only synthetic data.
Full justification in [docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md); migration
path in [docs/PRODUCTION_DEPLOY.md](docs/PRODUCTION_DEPLOY.md).
