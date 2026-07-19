# Momentum Life — Claims Processing App (App 2)

A demo-grade Databricks build for **Momentum Life** (the life-insurance business
unit of Momentum Group, Centurion, South Africa) that modernises the claims
**assessment** experience: one unified case view, an AI-drafted, source-cited
**synopsis** with discrepancy detection, drop-off (NTU) analytics, natural-language
querying over governed data, and governed reporting that displaces per-seat Power BI.

Everything runs on **synthetic data** — no real PII.

> **App 2** of a two-app vision (sibling to *App 1 — Underwriting Copilot*) on a
> shared lakehouse substrate.

---

## What's in the box

| Layer | Asset | Scope |
| --- | --- | --- |
| **Data** | Synthetic generators → bronze → silver → gold medallion | `[MVP]` |
| **Data** | `gold.claim_synopsis_view` (anti-swivel-chair, one wide row / claim) | `[MVP]` |
| **Data** | NTU funnel, at-risk early-warning, ops/SLA, decision split, requirement analytics | `[MVP]` |
| **Metrics** | 6 UC Metric Views (cycle time, NTU rate, SLA, decision split, pre-lodge days, throughput) | `[MVP]` |
| **AI** | 6 UC-function agent tools (governed, SQL-callable) | `[DEMO]` |
| **AI** | Vector Search index over parsed documents | `[MVP]` |
| **AI** | Synopsis Agent — Claude Sonnet via Model Serving + AI Gateway | `[MVP]` |
| **AI** | MLflow agent eval (citation groundedness, discrepancy recall, no-hallucination) | `[DEMO]` |
| **Serve** | Streamlit "Assessment Analytics Portal" — 7 pages | `[MVP]`/`[DEMO]`/`[MOCKED]` |
| **Serve** | AI/BI dashboards — Ops/SLA · NTU · Exec | `[DEMO]` |
| **Serve** | Genie space "Momentum Claims Analyst" | `[MVP]` |

Scope tags: `[MVP]` fully functional on synthetic data · `[DEMO]` functional but
narrower · `[MOCKED]` present for narrative, canned data · `[PHASE 2+]` named, not built.

---

## The three seeded demo scenarios

These exist with fixed claim numbers and drive the whole demo:

| `claim_no` | Type | Planted condition | Agent should produce |
| --- | --- | --- | --- |
| `CLM-DEATH-CLEAN` | Death | Benefits in force, reqs complete, VPD confirms, no mismatch | Clean cited synopsis → **recommend pay** |
| `CLM-DISAB-DISCREP` | Disability | occ@claim *Boilermaker* ≠ occ@inception *Clerk*; specialist report outstanding | Flags mismatch + missing report → **refer** |
| `CLM-SUSPECT-FRAUD` | Death | Event 50 days after inception; benefit lapsed; risk 0.83 | Early-claim + benefit flags → **investigate** (labelled heuristic) |

All three are verified in `gold.claim_synopsis_view` (occupation_mismatch,
early_claim_flag, benefit_status, outstanding_codes all land correctly).

---

## Physical layout

Co-located medallion schemas in `elexon_app_for_settlement_acc_catalog` (the demo
workspace can't create a dedicated catalog — see
[docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md)):

```
momentum_claims_bronze / _silver / _gold / _ai / _ops
```

## Repo structure

```
momentum-claims-demo/
├── databricks.yml              # DAB root (targets: demo)
├── resources/                  # catalog, jobs, app resource definitions
├── src/
│   ├── synthetic_data/         # deterministic generators (SEED=20260706)
│   ├── pipelines/{silver,gold} # consolidated build SQL for the DAB job
│   ├── ai/{tools,agents,eval}  # UC tools, synopsis agent, eval
│   └── app/                    # Streamlit "Assessment Analytics Portal"
├── sql/{02_silver,03_gold,04_metric_views}/   # per-object SQL (source of truth)
├── dashboards/                 # AI/BI dashboard JSON
├── genie/                      # Genie space config
├── docs/                       # requirements + deployment + runbook + traceability
└── logo/                       # Momentum brand assets
```

## Deploy

See [docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md). TL;DR:

```bash
databricks bundle validate -t demo -p <profile>
databricks bundle deploy   -t demo -p <profile>
databricks bundle run momentum_claims_build -t demo -p <profile>
```

## Demo script

See [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md) — click-by-click walk of DS1–DS5
with exact Genie/copilot prompts and expected outputs.

## Data residency

`af-south-1` is not a Databricks region; the residency-compliant production home
is **eu-west-1 (Ireland)** — not the USA. The demo uses only synthetic data.
Full justification in [docs/05_DEPLOYMENT.md](docs/05_DEPLOYMENT.md).
