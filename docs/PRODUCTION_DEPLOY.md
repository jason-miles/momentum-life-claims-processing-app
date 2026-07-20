# Production Deploy Runbook — eu-west-1 (residency-compliant)

How to stand up the Momentum demo on a **residency-compliant production
workspace**. The current demo runs on a US Field-Engineering workspace with
**synthetic data only** — fine, because residency binds *production* data, not
synthetic. For a real pilot on real (or realistic) data, deploy to **eu-west-1
(Ireland)** so all compute, storage, serving and inference stay **out of the
USA**. (`af-south-1` / Cape Town is not a Databricks region — see docs/05.)

> Nothing here changes the demo. It's the migration path, parameterized so the
> move is config + one retarget script, not a rewrite.

---

## 0. Prerequisites (gated — needs a human)

1. **A eu-west-1 Databricks workspace** (provision via go/fevm → AWS → Ireland,
   Serverless). Create a CLI profile: `databricks auth login --host <host> --profile <eu-profile>`.
2. **In-region Claude serving (US1.3 — fail loudly if unavailable):** confirm a
   Claude Sonnet serving path that keeps inference in eu-west-1 — either the
   built-in `databricks-claude-sonnet-*` FM endpoint if available in-region, or
   an AI-Gateway external-model route to Bedrock Claude in eu-west-1. **Do not
   deploy the agent if inference would route to the USA** — escalate instead.
3. **CREATE CATALOG rights** (prod workspaces usually have them) so you can use a
   dedicated catalog + clean schema names instead of the demo's co-located ones.

## 1. Catalog & schemas

On a workspace with catalog rights, create a dedicated catalog with a managed
location, then clean schemas:

```sql
CREATE CATALOG IF NOT EXISTS momentum_claims_demo
  MANAGED LOCATION 's3://<eu-west-1-bucket>/momentum';   -- in-region bucket
-- schemas are created by the retargeted build SQL (CREATE SCHEMA IF NOT EXISTS)
```

The `prod` bundle target defaults `var.catalog=momentum_claims_demo`. Claims
schemas become `bronze/silver/gold/ai/ops`; underwriting becomes `uw_bronze/…/uw_ai`.

## 2. Retarget the build SQL

The committed SQL hard-codes the demo's co-located FQNs. Rewrite them once:

```bash
python scripts/retarget_sql.py --catalog momentum_claims_demo --out build/prod_sql
# -> build/prod_sql/** with elexon_..._catalog.momentum_claims_<layer> => momentum_claims_demo.<layer>
#    and ...momentum_uw_<layer> => momentum_claims_demo.uw_<layer>
```

Point the DAB job `sql_task.file.path`s at `build/prod_sql/...` for the prod
target (or copy over the originals in a prod branch). Review the diff before running.

## 3. Vector Search + serving (in-region)

- Create an **in-region Vector Search endpoint** `ml_claims_vs` (prod default in
  the bundle) instead of reusing the demo's `valterra-vs-endpoint`.
- `src/ai/build_indexes.py` / `build_uw_index.py` read the endpoint from the
  bundle var — set `var.vs_endpoint=ml_claims_vs` (already the prod default).
- Confirm the embedding endpoint (`databricks-gte-large-en`) and the Claude
  endpoint resolve in eu-west-1 (step 0.2).

## 4. Deploy

```bash
databricks bundle validate -t prod -p <eu-profile>
databricks bundle deploy   -t prod -p <eu-profile>
# build both domains:
databricks bundle run momentum_claims_build -t prod -p <eu-profile>
databricks bundle run momentum_uw_build     -t prod -p <eu-profile>
# then the VS indexes:
python src/ai/build_indexes.py      # claims idx_documents (reads bundle vars)
python src/ai/build_uw_index.py     # underwriting idx_uw_notes
```

## 5. App config

The app is env-driven (backward-compatible defaults = demo layout). For prod,
set in `src/app_react/app.yaml`:

```yaml
env:
  - {name: MOMENTUM_CATALOG,           value: "momentum_claims_demo"}
  - {name: MOMENTUM_GOLD_SCHEMA,       value: "gold"}
  - {name: MOMENTUM_SILVER_SCHEMA,     value: "silver"}
  - {name: MOMENTUM_OPS_SCHEMA,        value: "ops"}
  - {name: MOMENTUM_AI_SCHEMA,         value: "ai"}
  - {name: MOMENTUM_UW_GOLD_SCHEMA,    value: "uw_gold"}
  - {name: MOMENTUM_UW_SILVER_SCHEMA,  value: "uw_silver"}
  - {name: MOMENTUM_UW_AI_SCHEMA,      value: "uw_ai"}
  - {name: DATABRICKS_WAREHOUSE_ID,    value: "<eu-west-1 warehouse id>"}
  - {name: GENIE_SPACE_ID,             value: "<prod claims genie>"}
  - {name: UW_GENIE_SPACE_ID,          value: "<prod uw genie>"}
  - {name: MOMENTUM_LLM_ENDPOINT,      value: "<in-region Claude endpoint>"}
```

Both `server/config.py` (claims) and `server/uw_data.py` (underwriting) read
these, so no code change is needed — only env.

## 6. Grants, Genie, dashboards

- Grant the prod app service principal USE/SELECT (+ EXECUTE on ai, MODIFY on
  ops) on the schemas, CAN_USE on the warehouse, CAN_RUN on both Genie spaces,
  CAN_QUERY on the Claude endpoint (see the demo grants in docs/05 for the shape).
- Recreate the two Genie spaces + dashboards in the prod workspace (their
  table_identifiers just need the retargeted catalog/schema names).

## 7. Verify

```sql
-- run scripts/smoke_verify.sql (retargeted) against the prod warehouse
```
Confirm row counts, seeded scenarios, metric views, and NTU buckets — same
checks as the demo.

## 8. Residency sign-off (US1.3)

Record in the deploy log: workspace region = eu-west-1, warehouse region,
VS endpoint region, and the resolved Claude serving region. **All must be
eu-west-1 (or another approved non-US region). If any resolves to `us-*`, stop.**

---

## What stays the same
The entire application, SQL logic, synthetic generators, agents, and UI are
identical — production is a **config + retarget** exercise, not a rebuild. The
only true code dependency is env vars (already wired). That's the whole point of
the parameterization.
