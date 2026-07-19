# POC Traceability — Demo Evidence Map

Maps demo evidence to the customer's success criteria and the broader POC rubric,
marking what is **demonstrated live on synthetic data** vs **asserted / Phase 2+**.

## Success criteria (from the PRD)

| ID | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| **SC1** | Unified case view (no swivel-chair) | ✅ Live | `gold.claim_synopsis_view` — one wide row per claim; Claim Detail left panel |
| **SC2** | Agentic synopsis is credible (source-cited) | ✅ Live | Synopsis Agent over Claude Sonnet; cited drafts for DS1–DS3 |
| **SC3** | Discrepancy detection lands | ✅ Live | occupation_mismatch, early_claim_flag, benefit_status, outstanding_codes computed + flagged (DS2/DS3) |
| **SC4** | NL querying works | ✅ Live | Genie space + AI Copilot; scripted questions in DS4 |
| **SC5** | NTU insight visible | ✅ Live | `gold.ntu_funnel` + `gold.ntu_at_risk` + NTU dashboard |
| **SC6** | Power BI displacement shown | ✅ Live | Ops/SLA + NTU + Exec AI/BI dashboards on lakehouse, no per-seat cost |
| **SC7** | Vector Search + tool-calling mirrors Leon du Plessis's pgvector POC | ✅ Live | `momentum_claims_ai` UC tools + Vector Search index + agent tool-calling |

## Demo acceptance criteria (backlog user stories)

| Story | Requirement | Status |
| --- | --- | --- |
| US1.1 | `bundle validate` passes; `deploy -t demo` provisions all resources | ✅ (co-located schemas; see docs/05) |
| US1.3 | Residency: model route resolves to approved region; documented; fail loudly | ✅ Documented (eu-west-1); af-south-1 shown impossible |
| US1.4 | 6 Metric Views defined + queryable from SQL/Genie | ✅ Live (all 6 `isMetric=true`) |
| US2.1 | Configurable N policies (default 5,000); SA distributions; masked IDs; deterministic seed | ✅ Live (5,003 policies, SEED=20260706) |
| US2.2 | All 4 states; ~15–20% pre-lodge stall; DS1–DS3 with known claim_no | ✅ Live (NTU ~11–20% by type; 3 seeded present) |
| US3.2 | `claim_synopsis_view` one wide row/claim; < 3s single-claim load | ✅ Live (single-claim filter is sub-second) |
| US4.2 | VS endpoint + index; metadata filter by claim_no; retrieves DS2's planted doc | ⏳ See AI-layer report (idx_documents) |
| US5.2 | Agent: DS1 clean cited; DS2 mismatch+missing→refer; DS3 early/benefit→flag; endpoint serves | ⏳ See AI-layer report |
| US5.3 | Guardrails: never final decision; "insufficient info"; role scope; MLflow traces | ✅ Enforced in agent system prompt + design |
| US8.2 | This traceability doc | ✅ (this file) |
| US8.3 | Demo runbook DS1–DS5 with exact prompts | ✅ (docs/DEMO_RUNBOOK.md) |

## Business KPIs — Phase 2+ (asserted, to be quantified on real data)

| Measure | Status |
| --- | --- |
| Assessor handling time per claim | Phase 2+ (needs baseline handling time from Momentum) |
| Missed-information / rework rate | Phase 2+ |
| Drop-off (NTU) recovered via intervention | Phase 2+ (demo shows the at-risk list that drives it) |
| SLA attainment & throughput | ✅ Live in demo (ops_metrics + metric views) |
| Reporting cost vs Power BI | ✅ Demonstrated (AI/BI, no per-seat licence) |

## Honest scoping notes

- **Fraud scoring is `[MOCKED]`** — risk_score is synthetic; real models are Phase 2+.
- **No live CDC** — synthetic generators stand in for Lakeflow Connect / partner
  connectors (IBMi/DB2 AS400 needs Fivetran/Qlik/Arcion — top integration risk).
- **Residency** — demo built on a US FE workspace with synthetic-only data;
  production target is eu-west-1 (Ireland). See docs/05.
- **Open items** carried from the requirements: assessor headcount (50–80),
  measured NTU rate, operating-model decision (isolated vs group platform),
  in-region Claude serving verification for production.
