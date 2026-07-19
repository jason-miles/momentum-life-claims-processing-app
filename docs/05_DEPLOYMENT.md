# 05 — Deployment & Data Residency

## Data residency (US1.3) — the hard constraint

> "Anything to the USA is not allowed."

Every resource — workspace, serverless SQL, jobs, Vector Search, model/agent
serving — must stay out of the USA. This document records how the demo meets
that, and the one honest caveat.

### The af-south-1 finding

The requirements name **AWS `af-south-1` (Cape Town)** as the primary demo
region. **`af-south-1` is not a supported Databricks region.** Databricks on
AWS runs in 16 regions; Cape Town is not one of them, so no workspace,
serverless, Vector Search, Model Serving, or App can be created there. This is
a hard platform fact, not a configuration choice.

### Resolution — eu-west-1 (Ireland)

The spec names **`eu-west-1` (Ireland)** as the approved secondary region.
`eu-west-1`:

- is a fully-supported Databricks region (serverless SQL, Vector Search, Model
  Serving, Databricks Apps all available);
- **satisfies the actual constraint** — it is not in the USA;
- keeps Anthropic Claude inference in-region (Bedrock/Claude is available in
  `eu-west-1`).

**For production, `eu-west-1` (Ireland) is the residency-compliant home for
this workload.** The synthetic-data demo build documented here was provisioned
on an existing Field Engineering demo workspace to hit the validation-session
date; because the dataset is **100% synthetic (no real PII)**, POPIA residency
does not bind the demo itself — it binds production. The migration path is a
`bundle deploy -t demo` against a `eu-west-1` workspace with `var.approved_region`
set to `eu-west-1`; the bundle is region-independent by construction.

| Concern | Demo (synthetic) | Production target |
| --- | --- | --- |
| Region | FE demo workspace (US) — synthetic data only | **eu-west-1 (Ireland)** |
| Real PII | None (fabricated SA IDs, masked) | UC masking + classification + purpose-based access |
| Claude serving | `databricks-claude-sonnet-4-6` via Model Serving + AI Gateway | Same, pinned in-region (eu-west-1) |
| Residency risk | Not applicable (no PII leaves anywhere) | Enforced: no `us-*` compute/serving |

> **Build fails loudly if no in-region option (US1.3):** on a production deploy,
> if the Claude serving route does not resolve to an approved region, the
> deploy step must stop and escalate rather than silently route out-of-region.
> See `src/ai/agents/synopsis_agent.py` region assertion.

## Physical layout (co-located schemas)

The demo workspace's metastore has Default Storage with no storage root, so
`CREATE CATALOG` is unavailable to the deploying user. The medallion is
co-located as five schemas inside the existing managed catalog:

```
elexon_app_for_settlement_acc_catalog
├── momentum_claims_bronze   raw synthetic landing
├── momentum_claims_silver   conformed / typed / deduped
├── momentum_claims_gold     serving views + 6 UC Metric Views
├── momentum_claims_ai       UC-function tools + Vector Search index + agent
└── momentum_claims_ops      app write-state / audit
```

On a workspace with catalog-creation rights, set `var.catalog =
momentum_claims_demo` and rename the schemas to `bronze/silver/gold/ai/ops`.

## Deploy

Prerequisites: Databricks CLI ≥ 0.292.0 (verified on v0.299.0), a profile for a
target workspace, and a serverless SQL warehouse id.

```bash
# 1. Validate
databricks bundle validate -t demo -p <profile>

# 2. Deploy resources (jobs, app)
databricks bundle deploy -t demo -p <profile>

# 3. Build the medallion + AI assets (generate synthetic data, silver, gold,
#    metric views, UC tools, vector index)
databricks bundle run momentum_claims_build -t demo -p <profile>

# 4. Deploy the app source
databricks bundle run --help    # or: databricks apps deploy momentum-claims-portal ...
```

Sizing (small, cheap, legible): one serverless SQL warehouse (auto-stop), one
small Vector Search endpoint (reused), scale-to-zero agent serving, small
serverless jobs.

## Deployed demo assets (elexon workspace)

Live as of the build (all on `fevm-elexon-app-for-settlement-acc`):

| Asset | Location |
| --- | --- |
| App — Assessment Analytics Portal | https://momentum-claims-portal-7474654808133980.aws.databricksapps.com |
| Dashboard — Ops & SLA | `/sql/dashboardsv3/01f1839979be1818a306e0692d82431e` |
| Dashboard — NTU / Drop-off | `/sql/dashboardsv3/01f18399a36b11b88d36ceea7aabe698` |
| Dashboard — Executive View | `/sql/dashboardsv3/01f18399b5011d95a90eb5a55fdea000` |
| Genie space — Momentum Claims Analyst | `01f18397532a1ba0b35d2e530bd1691a` |
| Vector Search index | `momentum_claims_ai.idx_documents` on `valterra-vs-endpoint` |
| SQL warehouse | `dcb1c3dd8d1570d6` (Serverless Starter) |

App service principal `4b5790c0-f4df-4c53-b5bb-266e1e55481f` is granted: USE/SELECT
on the gold + silver schemas, USE/SELECT/EXECUTE on `ai`, USE/SELECT/MODIFY on
`ops`, `CAN_USE` on the warehouse, and `CAN_RUN` on the Genie space.

## Teardown

```bash
databricks bundle destroy -t demo -p <profile>
# then drop the co-located schemas if desired:
#   DROP SCHEMA elexon_app_for_settlement_acc_catalog.momentum_claims_bronze CASCADE; (x5)
```
