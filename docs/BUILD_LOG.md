# Build Log — Momentum Life Underwriting & Claims Intelligence Portal

Chronological record of everything built, decided, verified, and fixed. Ground
truth is git history (39 commits, 2026-07-19 → 2026-07-21); this log groups it
into phases with the reasoning and verification behind each. (Phase-1 validation
check #9 asked for a build log in the Drive folder — this is it, in-repo.)

- **Customer:** Momentum Life (life insurance, Momentum Group, Centurion, SA)
- **Workspace:** `elexon` / `fevm-elexon-app-for-settlement-acc` (US FE demo ws), synthetic data only
- **Repo:** https://github.com/jason-miles/momentum-life-claims-processing-app
- **Live app:** https://momentum-claims-portal-7474654808133980.aws.databricksapps.com
- **Sources:** Claims Drive folder `1c_7CKpQXej…`; Underwriting Drive folder `15p7u3Y8…`

---

## Phase 0 — Pre-flight decisions
- **Residency:** spec demanded af-south-1 + "nothing to USA". **af-south-1 is not
  a Databricks region** → resolved to **eu-west-1 (Ireland)** as production target
  (spec's approved secondary, non-US). Demo runs on a US FE workspace with
  synthetic data only (residency binds production data, not synthetic).
- **Catalog:** no CREATE CATALOG on the metastore → co-located medallion as
  schemas in `elexon_app_for_settlement_acc_catalog` (`momentum_claims_*`, later
  `momentum_uw_*`).
- **Models:** Claude via Databricks serving; embeddings `databricks-gte-large-en`;
  reused the ONLINE `valterra-vs-endpoint` for Vector Search.

## Phase 1 — Claims data + medallion + AI  (cf732fd, f387ff0, 7361021)
- Deterministic synthetic generator (SEED=20260706): 5,003 policies, 603 claims,
  2,107 docs; 3 seeded scenarios (CLM-DEATH-CLEAN, CLM-DISAB-DISCREP,
  CLM-SUSPECT-FRAUD). **Fixed an NTU bug** (was 100% → realistic ~11–20%).
- Medallion: 11 silver tables → 6 gold views (`claim_synopsis_view` + NTU/ops/
  decision/requirement) → 6 UC Metric Views. All verified live.
- AI: 6 UC-function tools, Vector Search index `idx_documents` (DOC-91 filter
  verified), synopsis agent (Claude), MLflow eval (1.0). First app was Streamlit
  (7 pages), 3 AI/BI dashboards, "Momentum Claims Analyst" Genie space.

## Phase 2 — React + FastAPI rebrand  (16ce4a5 → f538e12)
Replaced Streamlit with a Momentum-branded React+FastAPI app (`src/app_react`).
- **Bugs fixed along the way:** app crash on `st.image use_container_width`;
  `webroot` gitignored so `databricks sync` skipped the built UI; nested-route
  MIME error (vite `base './'`→`'/'`). All caught by browser smoke-tests.
- FastAPI single-process serves the SPA from `webroot/`; env-driven config.

## Phase 3 — Isaac review #1 + polish  (356bf90, b6998be, 4598974, 1dbf6d2)
- **Adversarial review found a CRITICAL live SQL injection**: `.replace("'","''")`
  is defeated by Spark backslash-escaping. Fixed by parameterizing ALL queries
  (`:name` binds); verified the exploit payload became literal data.
- `/api/action` regression (VALUES + bound params rejects `uuid()`) → INSERT…SELECT.
- **Enterprise redesign pass:** fixed broken logo, restrained typography, icon
  nav + active state, **paginated the 603-row inbox** (was a 35k-px dump),
  compact tables, refined charts. All 7 pages browser-verified.

## Phase 4 — Two-domain expansion: Underwriting  (c219450 → 5b1f378)
Built from the underwriting Drive spec (Underwriting_Modernization_Requirements_v1.1).
- New synthetic UW domain (`momentum_uw_*`, SEED=20260617): 4,003 applications,
  journeys, requirements, decisions (counteroffers), BPM tasks, notepad, NTU
  ~29% (buckets 62/19/12/7, matching demo slide 5). 3 seeded: UW-CLEAN-FASTTRACK,
  UW-COUNTEROFFER, UW-NTU-RISK (0.907 propensity).
- Gold `uw_case_view` (unified case, R2.1) + journey/decision/NTU/requirement/ops
  views; 3 UC metric views; 4 UC tools.
- **Underwriting Co-Pilot** (NTU-ranked queue + unified case view + AI risk
  synopsis + NTU intervention), **UW Analytics**, **UW Executive View**; renamed
  AI Copilot → **Claims Co-Pilot**. Sidebar regrouped: Co-Pilots/Underwriting/
  Claims/Platform + cross-domain **Executive Overview** landing.
- **Vector Search RAG over notepad** (`idx_uw_notes`, the spec hero beat R2.2)
  + claims-side RAG (`idx_documents`); both synopses cite [VS:notes]/[VS:docs].
- **UW Genie space** "Momentum Underwriting Analyst" + NL ask panel; UW Lakeview
  dashboard. Perf: synopsis cache + startup pre-warm; warehouse tuned.

## Phase 5 — Reproducibility, production path, review #2  (0f45b60 → 2903004)
- Extracted the imperatively-built UW layer into committed SQL (`src/pipelines/uw`)
  + DAB job `momentum_uw_build`; verified a re-run reproduces the live layer.
- **eu-west-1 `prod` DAB target** + `scripts/retarget_sql.py` + PRODUCTION_DEPLOY.md.
- Ops scripts: `teardown.sql`, `smoke_verify.sql`. UW POC traceability doc.
- **Isaac review #2:** the RAG additions RE-INTRODUCED the injection class (VS
  table-valued-function args can't be bound). Confirmed live, fixed with a
  `_vs_safe()` allowlist. + 5 frontend UX fixes (Overview loading/error, etc.).
- README rewritten as the two-domain front page.

## Phase 6 — Evals, performance, data fix  (fc563cf → 49c1c7c)
- **UW MLflow eval** (`eval_uw_synopsis.py`, all scorers 1.0) — parity with claims.
  The eval caught an over-strict guardrail scorer (fixed).
- **Perf — slow page refresh root-caused:** a fresh warehouse connection per
  query (~3.5s each). Fixed with a pooled connection: Claim Detail 20s→2.5s,
  Exec 14s→5s, Inbox 4.5s→0.9s. **A parallel-connection version SEGFAULTED
  (exit 139)** — the connector is not concurrency-safe; reverted, kept serial
  pooling. Startup pre-warm now warms the connection + common pages.
- **Synopsis model → Claude Haiku 4.5** (was Sonnet 4.6): timed 26.6s→4.7s
  (~5.6×); UW eval still 1.0. Env-overridable.
- **Data fix:** 232/603 claims (38%) rendered "Benefit: Null" — the synopsis-view
  benefit join required an exact type match the synthetic policies often didn't
  carry. Changed to rank-by-preference (matching type → in-force → largest);
  null_benefit 232→0, seeded scenarios intact, verified live in-browser.

---

## Verification summary (what was proven, not just built)
- **All 11 pages** visually confirmed in-browser (screenshots taken).
- **Backend data probe:** all 16 page data-functions return real rows (both domains).
- **Two adversarial security reviews** passed; both caught a live SQL injection, both fixed + re-verified.
- **Two MLflow agent evals** at 1.0 (claims + underwriting).
- **Seeded scenarios** verified in `claim_synopsis_view` / `uw_case_view`.
- **`bundle validate`** OK for `demo` + `prod` targets.

## Known scoping / honest caveats
- Synthetic data only (no live CDC); fraud scores `[MOCKED]`; FileNet/email ingestion Phase 2+.
- Demo on a US workspace; production target eu-west-1 (docs/05, PRODUCTION_DEPLOY.md).
- `databricks-sql-connector` is not safe for concurrent connections (segfaults) — do not re-attempt threaded queries.

## Related docs
README · 05_DEPLOYMENT · PRODUCTION_DEPLOY · DEMO_RUNBOOK · UW_DEMO_RUNBOOK ·
POC_TRACEABILITY · UW_POC_TRACEABILITY · SESSION_HANDOFF.
