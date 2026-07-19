# Momentum Life — Assessment Analytics Portal

Databricks App (Streamlit) for the Momentum Life claims-processing demo.

## Pages
1. **Claims Inbox** [MVP] — filterable/sortable work queue with SLA, risk and occupation-mismatch flags. Select a row to open Claim Detail.
2. **Claim Detail** [MVP] — the centerpiece. Left: unified case view (policy/benefit, occupation compare, requirement checklist, third-party chips, timeline, documents). Right: AI synopsis (agent → `ai_query` → heuristic fallback) with discrepancy badges, citation chips, recommendation, and a per-claim copilot. Bottom: referral assign, mocked fraud score, and Accept/Edit/Record-referral actions that write to `momentum_claims_ops.app_events`.
3. **AI Copilot** [MVP] — full-screen Genie chat over the gold layer with suggested-question chips.
4. **NTU / Ops Dashboard** [MVP] — Plotly NTU funnel, at-risk pre-lodge list, SLA breaches, per-assessor throughput.
5. **Executive View** [DEMO] — KPI tiles from metric views, decision-split donut, claims-by-province, embedded Genie.
6. **Fraud Workbench** [MOCKED] — clearly-labelled mocked relationship flags + real risk-score distribution.
7. **Admin Console** [DEMO] — data-product catalog with row counts, lineage links, agent-eval placeholder, residency note.

Plus a **"View as"** role switcher (Assessor / Manager / Exec / Investigator / Admin) and a Momentum-branded header.

## Run locally
```bash
cd src/app
pip install -r requirements.txt
# auth: either a PAT ...
export DATABRICKS_HOST=https://fevm-elexon-app-for-settlement-acc.cloud.databricks.com
export DATABRICKS_TOKEN=<pat>
# ... or a CLI profile
export DATABRICKS_CONFIG_PROFILE=elexon
streamlit run app.py
```
With no credentials the app runs in **demo mode** (friendly "connect to Databricks" messages and the deterministic heuristic synopsis) rather than crashing.

## Deploy as a Databricks App
```bash
databricks sync src/app /Workspace/Users/<you>/momentum-claims-app -p elexon
databricks apps create momentum-claims-portal -p elexon
databricks apps deploy momentum-claims-portal \
  --source-code-path /Workspace/Users/<you>/momentum-claims-app -p elexon
```
Config lives in `app.yaml` (warehouse id `dcb1c3dd8d1570d6`, Genie space `01f18397532a1ba0b35d2e530bd1691a`, catalog/schemas, LLM endpoint). Add the SQL warehouse and Genie space as app resources so the service principal has access (see `resources/app.yml`).

## Layout
```
src/app/
├── app.py              # entry: header, sidebar nav, role switcher
├── app.yaml            # Databricks App config
├── requirements.txt
├── assets/             # bundled logos
├── lib/                # config, sql_client, genie_client, agent_client, data
├── components/         # ClaimCard, SynopsisPanel, CopilotChat, ... (widgets.py)
└── views/              # one module per page
```
