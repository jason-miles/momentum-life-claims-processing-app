# Underwriting POC Traceability — Demo Evidence Map

Maps the underwriting demo to the requirement IDs and demo storyboard in
`Underwriting_Modernization_Requirements_v1.1`, marking each as
**✅ Live** (demonstrated on synthetic data), **◐ Partial/Asserted**, or
**⏳ Phase 2+** (named, not built). Leave-behind for the Tuesday on-site.

Legend: **P1** analytics wedge · **P2** unified case view + AI assist · **P3** operational app.

---

## 1. Data ingestion & integration

| ID | Requirement | Phase | Status | Evidence in the demo |
| --- | --- | --- | --- | --- |
| R1.1 | Near-real-time / CDC from AS400 (policy, life, sum-at-risk, role players, journey type, Decision Manager notepad) | P1 | ◐ Asserted | Synthetic generator stands in for CDC (no live customer network). `application`, `uw_life`, `first_pass` model the AS400 shapes; notepad modelled in `uw_case_note`. Live CDC is the top integration risk — Phase 2. |
| R1.2 | Ingest Postgres quote/application + operational data | P1 | ◐ Asserted | Modelled in `application` (channel, broker, journey). |
| R1.3 | Ingest Decision Manager rules-engine output | P1 | ◐ Asserted | `first_pass` (auto_requirements / referred_to_uw) + `uw_requirement` model the first-pass output. |
| R1.4 | Ingest BPM (IBM BAW) task state, SLA, throughput | P1 | ✅ Live | `bpm_task` (opened/closed, cycle_days, sla_breach) → `uw_ops_metrics`, per-underwriter throughput. |
| R1.5 | Parse & ingest FileNet documents (unstructured) | P2 | ⏳ Phase 2+ | Notepad text stands in as the unstructured corpus for the RAG demo; FileNet volume/formats to confirm. |
| R1.6 | Ingest case-linked email (lab/blood results, broker comms) | P2 | ⏳ Phase 2+ | Not modelled; named in roadmap. |
| R1.7 | Capture underwriter notepad free text (rationale/IP) | P2 | ✅ Live | `uw_case_note` — the free-text corpus behind the AI synopsis + Vector Search. |
| R1.8 | Third-party enrichment (LOA register, health-cloud, geo/claims-rate) | P2/P3 | ⏳ Phase 2+ | Risk score proxies impairment; external enrichment named for later. |

## 2. Unified workspace — kill the swivel chair

| ID | Requirement | Phase | Status | Evidence |
| --- | --- | --- | --- | --- |
| R2.1 | Single UC-governed view keyed on **policy number**, structured + unstructured | P2 | ✅ Live | `gold.uw_case_view` (one row/policy: application + life + requirements + decision + BPM + NTU) rendered as the **Underwriting Co-Pilot "Unified Case View"**. |
| R2.2 | Mosaic AI Vector Search over notepad, **metadata-filtered by policy number** (native re-build of Leon's pgvector POC) | P2 | ✅ Live | `idx_uw_notes` on `valterra-vs-endpoint` (gte-large-en, 4,003 notes, ONLINE); policy_no metadata-filter verified; synopsis retrieves similar cases, cited `[VS:notes]`. **The hero beat.** |
| R2.3 | Agentic retrieval with tool-use over governed Delta tables | P2 | ✅ Live | UC-function tools `get_uw_case`, `list_uw_requirements`, `get_uw_notes`, `ntu_risk_reason`, `search_uw_notes`; the AI Risk Synopsis composes them. |
| R2.4 | Genie NL Q&A over curated, consistently-named datasets | P1 | ✅ Live | "Momentum Underwriting Analyst" Genie space over 7 gold tables; "Ask the Underwriting Analyst" panel on UW Analytics; scripted questions answered live. |

## 3. AI / ML

| ID | Requirement | Phase | Status | Evidence |
| --- | --- | --- | --- | --- |
| R3.1 | RAG over the unstructured corpus for in-context case assessment | P2 | ✅ Live | Synopsis RAG-retrieves similar prior cases from `idx_uw_notes`. |
| R3.2 | Risk / decisioning augmentation from questionnaire + behaviours | P2 | ◐ Partial | Synopsis flags risk drivers (smoker, occupation class, impaired risk); advisory only, never binds/declines. |
| R3.3 | Requirement-recommendation insight (when ECG vs GP vs bloods, by profile) | P2 | ◐ Partial | `uw_requirement_analytics` (which requirement, return rate, timing) surfaces the pattern; a recommender model is Phase 2. |
| R3.4 | NTU / drop-off prediction with intervention triggers | P2 | ✅ Live | `ntu_propensity` scored per case (features: days outstanding, outstanding reqs, risk, SAR band); NTU Intervention panel lists triggers; at-risk list ranks the book. |
| R3.5 | External-data risk signals (claims rate by area) | P3 | ⏳ Phase 2+ | Named; not built. |

## 4. Analytics & reporting (augment, then displace Power BI)

| ID | Requirement | Phase | Status | Evidence |
| --- | --- | --- | --- | --- |
| R4.1 | First-pass journey split (auto-req / refer / fast-track / tele) | P1 | ✅ Live | `uw_journey_split` → donut on UW Analytics + Exec View. |
| R4.2 | Requirements analytics (which requirement, which lives, timing) | P1 | ✅ Live | `uw_requirement_analytics` table. |
| R4.3 | Decision split + counteroffer reasons | P1 | ✅ Live | `uw_decision_split` (n_loadings, n_exclusions) → decision-mix chart. |
| R4.4 | NTU funnel analysis (where & why drop-off) | P1 | ✅ Live | `uw_ntu_funnel` (62/19/12/7 buckets, matching demo slide 5) → drop-off chart + recoverable-value card. |
| R4.5 | Operational / workflow analytics from BPM (SLA, overdue, throughput, per-UW) | P1 | ✅ Live | `uw_ops_metrics`; SLA breach + per-underwriter throughput. |
| R4.6 | Genie-first democratization; thin exec dashboards; metrics as data products | P1 | ✅ Live | Genie space + Underwriting Executive View + published Lakeview dashboard + UC Metric Views (STP, turnaround, NTU rate). |

## 5. Governance

| ID | Requirement | Phase | Status | Evidence |
| --- | --- | --- | --- | --- |
| R5.1 | UC cataloging, lineage, consistent business metrics as data products | P1 | ✅ Live | All objects in governed `momentum_uw_*` schemas; 3 UC Metric Views deliver consistent terminology; Admin Console lists the catalog. |

## 6. Non-functional & constraints

| ID | Requirement | Status | Note |
| --- | --- | --- | --- |
| R6.1 | AWS-primary; respect group federation; Power BI on Azure | ◐ | Demo on an AWS FE workspace; production target eu-west-1 (see docs/05). |
| R6.2 | Validate "real-time" = near-real-time CDC + fresh BPM state; AS400 CDC = key risk | ⏳ | To confirm: journal-based CDC vs partner connector vs batch. |
| R6.3 | Phasing analytics-first → operational later (months, not weeks) | ✅ | Roadmap slide + this doc's P1/P2/P3 tags reflect it. |
| R6.4 | Power BI licensing pressure (F32 downgrade, per-seat) — displacement target | ✅ | AI/BI + Genie reproduce ops roll-ups at no per-seat cost. |

---

## Demo storyboard coverage (9 beats)

| Beat | Status | Where |
| --- | --- | --- |
| 1 Platform overview | ✅ | Slides + Executive Overview landing |
| 2 Governance wedge | ✅ | Admin Console (catalog, both domains) |
| 3 Intake & risk capture | ✅ | Journey types on any case |
| 4 Unified case view | ✅ | Underwriting Co-Pilot — Unified Case View |
| 5 AI assist (hero — Leon's POC graduated) | ✅ | AI Risk Synopsis + Vector Search RAG `[VS:notes]` |
| 6 Decisioning & case tracking | ✅ | Case queue by NTU propensity + BPM task state |
| 7 Operational reporting | ✅ | UW Analytics + Executive View (Power BI displacement) |
| 8 Genie | ✅ | "Ask the Underwriting Analyst" |
| 9 Close on phasing | ✅ | Roadmap; "not an AS400/BPM replacement" |

## Honest scoping (say these out loud)
- **Synthetic data only** — no live CDC; generators stand in for AS400/BPM/FileNet/email.
- **Advisory AI** — the synopsis never issues a bind/decline; it flags and recommends.
- **Databricks does not replace** AS400 (system of record) or IBM BAW (workflow) in any PoC timeframe — it owns the governed read layer + AI assist + analytics.
- **Residency** — production target eu-west-1 (not USA); af-south-1 is not a Databricks region (docs/05).

## Confirm-before-ROI (open questions)
Underwriter headcount (15–50?) · AS400 (IBM i) CDC mechanism & latency · FileNet
volume/formats/access · agreed definition of "real-time" · Power BI coexist-or-replace
given group federation.
