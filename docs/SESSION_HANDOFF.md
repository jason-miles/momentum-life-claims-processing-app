# Session Handoff — Momentum Life Claims Processing App

**Last updated:** 2026-07-19 (evening session)
**Pick-up owner:** Jason Miles
**Repo (local):** `/Users/jason.miles/vibe-coding-repos/Momentum/momentum-claims-demo`
**GitHub:** https://github.com/jason-miles/momentum-life-claims-processing-app (PUBLIC)
**Workspace:** `elexon` / `fevm-elexon-app-for-settlement-acc` (id 7474654808133980), CLI profile `elexon`
**Validation session:** with Jurgens Krynauw — was targeted for 2026-07-20.

---

## TL;DR — where we are

The **entire demo is built and deployed and working** on synthetic data. The
original **Streamlit** app is live and functional. We are **mid-way through
replacing the Streamlit frontend with a slicker, Momentum-brand-faithful
React + FastAPI app** (your request). The React **backend is done + verified
live**; the React **frontend was still building** when we paused.

**Two things need YOU (can't be done headless):**
1. **`git push`** — all work is committed locally (7 commits) but the push to
   GitHub was blocked by the harness permission gate. Run it yourself:
   ```
   cd /Users/jason.miles/vibe-coding-repos/Momentum/momentum-claims-demo
   git push -u origin main
   ```
2. Optionally provision a **eu-west-1 (Ireland)** workspace for a
   residency-faithful production deploy (demo currently on US workspace with
   synthetic-only data — fine for the demo; see docs/05).

---

## ✅ DONE and VERIFIED LIVE (on the elexon workspace)

### Data + medallion (all queried and confirmed)
- Synthetic generators, deterministic `SEED=20260706`: **5,003 policies, 603
  claims, 2,107 docs, 2,018 emails**. Code: `src/synthetic_data/`.
- 3 seeded scenarios present with correct planted signals:
  - `CLM-DEATH-CLEAN` — clean → recommend PAY
  - `CLM-DISAB-DISCREP` — occupation Clerk→Boilermaker mismatch + REQ-SPECIALIST
    outstanding → REFER/REQUEST INFO
  - `CLM-SUSPECT-FRAUD` — event 50d post-inception, benefit lapsed, risk 0.83 → INVESTIGATE
- Bronze loaded → **11 silver tables** → **6 gold views** (`claim_synopsis_view`,
  `ntu_funnel`, `ntu_at_risk`, `ops_metrics`, `decision_split`,
  `requirement_analytics`) → **6 UC Metric Views** (all `isMetric=true`).
- Physical layout: co-located schemas in `elexon_app_for_settlement_acc_catalog`:
  `momentum_claims_{bronze,silver,gold,ai,ops}` (no CREATE CATALOG on this metastore).
- Fixed a real NTU-rate bug (was 100% for every type → now realistic ~11–20%).

### AI layer (all deployed + tested live)
- **6 UC-function tools** in `momentum_claims_ai`: get_claim_context,
  get_policy_benefits, list_outstanding_requirements, check_claimability,
  get_third_party_verifications, search_claim_documents. Code: `src/ai/tools/`.
- **Vector Search index** `momentum_claims_ai.idx_documents` on
  `valterra-vs-endpoint` (reused, ONLINE), embeddings `databricks-gte-large-en`.
  DOC-91 claim_no filter verified.
- **Synopsis Agent** `src/ai/agents/synopsis_agent.py` on
  `databricks-claude-sonnet-4-6`. Verified: DS1→PAY, DS2→flags mismatch+missing
  report, DS3→INVESTIGATE. MLflow eval (`src/ai/eval/`) scored 1.0.

### Serving
- **AI/BI dashboards** (3, published): Ops/SLA `01f1839979be1818a306e0692d82431e`,
  NTU `01f18399a36b11b88d36ceea7aabe698`, Exec `01f18399b5011d95a90eb5a55fdea000`.
- **Genie space** "Momentum Claims Analyst": `01f18397532a1ba0b35d2e530bd1691a`.
- **Streamlit app** `momentum-claims-portal` — DEPLOYED + RUNNING at
  https://momentum-claims-portal-7474654808133980.aws.databricksapps.com
  - Fixed the `st.image use_container_width` crash (→ `use_column_width`).
  - Smoke test: Inbox renders 603 claims, no tracebacks. (Sidebar nav was flaky
    under the automated browser driver — a Streamlit rerun quirk. This is exactly
    why we're moving to React, which uses real URL routing.)

### App service principal grants (already applied)
SP `4b5790c0-f4df-4c53-b5bb-266e1e55481f`: USE/SELECT on gold+silver, USE/SELECT/
EXECUTE on ai, USE/SELECT/MODIFY on ops, warehouse `dcb1c3dd8d1570d6` CAN_USE,
Genie space CAN_RUN.

### Bundle + docs
- DAB: `databricks.yml` + `resources/*.yml`. `databricks bundle validate -t demo -p elexon` = **OK**.
- Docs: `README.md`, `docs/05_DEPLOYMENT.md` (residency: af-south-1 is NOT a
  Databricks region → **eu-west-1** production target), `docs/DEMO_RUNBOOK.md`
  (DS1–DS5 click-by-click), `docs/POC_TRACEABILITY.md`.

---

## 🔧 IN PROGRESS — React + FastAPI rebrand (your "make it slick + Momentum-branded" request)

New app lives alongside the Streamlit one at **`src/app_react/`**.

### ✅ Backend — DONE + verified live
- `src/app_react/app.py` — FastAPI single-process (serves React from `webroot/`).
- `src/app_react/server/` — streamlit-free ports: `sql_client.py`, `data.py`,
  `agent_client.py`, `genie_client.py`, `config.py`, `routes/claims.py`.
- `src/app_react/app.yaml` + `requirements.txt` written.
- Verified live: `/api/inbox` = 603 claims, `/api/exec` KPIs (13.8d cycle /
  17.3% NTU / 75.7% SLA), `/api/claim/CLM-DISAB-DISCREP` returns mismatch=True,
  4/5 reqs, REQ-SPECIALIST outstanding.
- **API contract** (all implemented): /api/health, /inbox, /claim/{no},
  /claim/{no}/synopsis, /copilot (POST), /genie (POST), /ntu, /ops, /exec,
  /requirements, /assessors, /admin/catalog, /action (POST).

### ⏳ Frontend — WAS BUILDING when we paused (NOT yet finished)
- A background agent was building `src/app_react/frontend/` (React 18 + Vite +
  TS + react-router + recharts) against the Momentum design system + the API
  contract above. At pause time only `main.tsx` had landed — **assume the
  frontend is INCOMPLETE**. First thing tomorrow: check whether the agent
  finished (look for `src/app_react/frontend/src/pages/*`, a working
  `npm run build`, and a `dist/`).

### Momentum design tokens (captured from momentum.co.za — use these)
- Primary **NAVY `#14205A`** (logo wordmark, main CTAs). Accent **RED `#E4002B`**
  (logo "m", Log in button) — sparingly.
- White bg, light grey `#F5F7FA`, body text `rgba(17,24,39,0.9)`, secondary `#5B6B7C`.
- **Pill buttons** (radius 999px), rounded cards (~14px) + soft shadows, generous whitespace.
- Fonts: **Poppins** (headings, ~800) + **Inter** (body) via Google Fonts —
  substitutes for Momentum's custom "The Curve".
- Logo at `src/app_react/frontend/public/momentum_life_logo.png`.

---

## ▶️ NEXT STEPS (tomorrow, in order)

1. **Push to GitHub** (you must run — permission-gated):
   `git push -u origin main`  (7 commits waiting; remote is empty, clean first push)

2. **Check the React frontend agent output** — did it finish? Is
   `src/app_react/frontend/` complete and does `npm run build` succeed?
   - If incomplete: resume/re-run the frontend build (spec is in this session's
     history; design tokens + API contract above).

3. **Deploy the React app** (replaces the Streamlit deployment on the same app name):
   ```
   cd src/app_react/frontend && npm install && npm run build
   rm -rf ../webroot && cp -r dist ../webroot        # webroot = shipped UI (sync ignores dist/)
   cd .. && databricks sync . /Workspace/Users/jason.miles@databricks.com/momentum-claims-portal-src --profile elexon --full
   databricks apps deploy momentum-claims-portal --source-code-path /Workspace/Users/jason.miles@databricks.com/momentum-claims-portal-src --profile elexon
   ```
   (App SP grants already in place; app.yaml already points at the right catalog/
   warehouse/Genie. NOTE: switching this app from Streamlit to FastAPI changes the
   entry command — that's fine, app.yaml in src/app_react has the uvicorn command.)

4. **Browser smoke-test** all 7 pages on the live URL; confirm routing works and
   Claim Detail for CLM-DISAB-DISCREP shows the mismatch + AI synopsis.

5. **Commit** the frontend + webroot, push again.

6. **Optional / production:** provision eu-west-1 workspace, set
   `var.approved_region=eu-west-1`, redeploy for residency-faithful prod.

---

## ⚠️ GOTCHAS / NOTES
- **vibe-coding-repos was reorganised** into customer subfolders mid-session; this
  repo moved to `.../Momentum/momentum-claims-demo`. All git history intact.
- **`.venv`** in the repo has a stale interpreter path from the move; recreate if
  needed: `python3 -m venv .venv && .venv/bin/pip install pandas numpy`.
- **Streamlit vs React app.yaml**: `src/app/` (Streamlit) and `src/app_react/`
  (React) both exist. `resources/app.yml` currently points `source_code_path`
  at `../src/app` (Streamlit). Update it to `../src/app_react` when you cut over,
  OR just deploy via the manual `databricks apps deploy` above.
- **The 7 pages** (both apps): Claims Inbox, Claim Detail, AI Copilot, NTU/Ops,
  Executive View, Fraud Workbench [MOCKED], Admin Console.
- Full asset inventory + IDs is in `docs/05_DEPLOYMENT.md`.
- Memory file written: `~/.claude/.../memory/momentum-claims-processing-repo.md`.

---

## KEY IDs (quick reference)
| Thing | Value |
| --- | --- |
| Catalog | `elexon_app_for_settlement_acc_catalog` |
| Schemas | `momentum_claims_{bronze,silver,gold,ai,ops}` |
| Warehouse | `dcb1c3dd8d1570d6` (Serverless Starter) |
| Claude endpoint | `databricks-claude-sonnet-4-6` |
| Embeddings | `databricks-gte-large-en` |
| VS endpoint | `valterra-vs-endpoint` (reused) |
| VS index | `momentum_claims_ai.idx_documents` |
| Genie space | `01f18397532a1ba0b35d2e530bd1691a` |
| App | `momentum-claims-portal` |
| App SP | `4b5790c0-f4df-4c53-b5bb-266e1e55481f` |
| App URL | https://momentum-claims-portal-7474654808133980.aws.databricksapps.com |
