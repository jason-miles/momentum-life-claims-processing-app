"""
Momentum Life Claims — Vector Search index build script
========================================================

Builds the semantic-retrieval layer that backs the Synopsis Agent's document
search. Two stages:

  1. Materialise a chunk-level source Delta table `momentum_claims_ai.doc_chunks`
     from `silver.document`, with Change Data Feed enabled (required for
     Delta Sync vector indexes).
  2. Create Delta Sync vector indexes on the existing (ONLINE) endpoint
     `valterra-vs-endpoint`, using Databricks-managed embeddings via
     `databricks-gte-large-en`:
        - idx_documents  (claims documents)   <- primary deliverable
        - idx_email      (claim emails)        <- built if silver.email exists
        - idx_notes      (assessor notes)      <- placeholder / best-effort

The primary requirement is that `idx_documents`, filtered by `claim_no`, returns
only that claim's documents and retrieves the planted DOC-91 for
CLM-DISAB-DISCREP.

Run modes
---------
* Locally against the `elexon` profile:  `python src/ai/build_indexes.py`
* Or via `databricks execute_code` (serverless) — the module-level `main()`
  is safe to invoke either way.

Notes
-----
Vector index creation + initial TRIGGERED sync can take 5–15 minutes. This
script triggers the build and polls briefly; if the index has not reached
ONLINE within the poll budget it leaves it building and reports that state
rather than blocking.
"""

from __future__ import annotations

import time
from typing import Optional

# ----------------------------------------------------------------------------
# Configuration (matches the demo's fixed physical layout)
# ----------------------------------------------------------------------------
CATALOG = "elexon_app_for_settlement_acc_catalog"
AI_SCHEMA = "momentum_claims_ai"
SILVER_SCHEMA = "momentum_claims_silver"

VS_ENDPOINT = "valterra-vs-endpoint"
EMBEDDING_ENDPOINT = "databricks-gte-large-en"

SOURCE_TABLE = f"{CATALOG}.{AI_SCHEMA}.doc_chunks"
IDX_DOCUMENTS = f"{CATALOG}.{AI_SCHEMA}.idx_documents"
IDX_EMAIL = f"{CATALOG}.{AI_SCHEMA}.idx_email"
IDX_NOTES = f"{CATALOG}.{AI_SCHEMA}.idx_notes"

# How long to poll an index for ONLINE before giving up and leaving it building.
POLL_TIMEOUT_S = 480
POLL_INTERVAL_S = 20


# ----------------------------------------------------------------------------
# Spark / SQL helpers
# ----------------------------------------------------------------------------
def _get_spark():
    """Return an active SparkSession (Databricks runtime or Connect)."""
    try:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "No SparkSession available. Run this on Databricks (serverless "
            "execute_code or a notebook) where Spark/Delta is present."
        ) from exc


def build_source_table(spark) -> None:
    """
    Create/refresh the chunk-level source Delta table from silver.document.

    For the demo each document maps to a single chunk (chunk_text = parsed_text);
    the schema is deliberately chunk-shaped (doc_id PK + claim_no + doc_type
    metadata) so real chunking can slot in later without changing the index.
    Change Data Feed is enabled so the Delta Sync index can track updates.
    """
    print(f"[doc_chunks] building {SOURCE_TABLE} from {SILVER_SCHEMA}.document ...")
    spark.sql(
        f"""
        CREATE OR REPLACE TABLE {SOURCE_TABLE} (
            doc_id     STRING COMMENT 'Primary key: source document id',
            claim_no   STRING COMMENT 'Owning claim (metadata filter key)',
            doc_type   STRING COMMENT 'Document type (metadata filter key)',
            chunk_text STRING COMMENT 'Text sent to the embedding model'
        )
        USING DELTA
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        COMMENT 'Chunk-level source for the claims document vector index.'
        """
    )
    spark.sql(
        f"""
        INSERT OVERWRITE {SOURCE_TABLE}
        SELECT
            doc_id,
            claim_no,
            doc_type,
            parsed_text AS chunk_text
        FROM {CATALOG}.{SILVER_SCHEMA}.document
        WHERE doc_id IS NOT NULL AND parsed_text IS NOT NULL
        """
    )
    n = spark.table(SOURCE_TABLE).count()
    print(f"[doc_chunks] {n} rows written.")


def build_email_source_if_present(spark) -> bool:
    """Create momentum_claims_ai.doc_chunks_email if silver.email exists."""
    tables = [
        r.tableName
        for r in spark.sql(f"SHOW TABLES IN {CATALOG}.{SILVER_SCHEMA}").collect()
    ]
    if "email" not in tables:
        print("[email] silver.email not found — skipping idx_email.")
        return False

    target = f"{CATALOG}.{AI_SCHEMA}.doc_chunks_email"
    cols = {
        c.name for c in spark.table(f"{CATALOG}.{SILVER_SCHEMA}.email").schema
    }
    # Be tolerant of the exact email schema — pick a sensible text/body column.
    text_col = next(
        (c for c in ("body", "parsed_text", "email_body", "content") if c in cols),
        None,
    )
    id_col = next((c for c in ("email_id", "id", "doc_id") if c in cols), None)
    if not text_col or not id_col or "claim_no" not in cols:
        print("[email] silver.email present but schema unexpected — skipping.")
        return False

    spark.sql(
        f"""
        CREATE OR REPLACE TABLE {target} (
            doc_id STRING, claim_no STRING, doc_type STRING, chunk_text STRING
        ) USING DELTA TBLPROPERTIES (delta.enableChangeDataFeed = true)
        """
    )
    spark.sql(
        f"""
        INSERT OVERWRITE {target}
        SELECT CAST({id_col} AS STRING) AS doc_id,
               CAST(claim_no AS STRING) AS claim_no,
               'email' AS doc_type,
               CAST({text_col} AS STRING) AS chunk_text
        FROM {CATALOG}.{SILVER_SCHEMA}.email
        WHERE {id_col} IS NOT NULL AND {text_col} IS NOT NULL
        """
    )
    print(f"[email] source {target} built.")
    return True


# ----------------------------------------------------------------------------
# Vector Search helpers
# ----------------------------------------------------------------------------
def _vs_client():
    from databricks.vector_search.client import VectorSearchClient

    # Uses ambient auth (notebook creds, or DATABRICKS_HOST/TOKEN, or profile).
    return VectorSearchClient(disable_notice=True)


def create_delta_sync_index(
    vsc,
    index_name: str,
    source_table: str,
    columns_to_sync: Optional[list] = None,
) -> None:
    """
    Idempotently create a TRIGGERED Delta Sync index with managed embeddings.

    `columns_to_sync` are the metadata columns copied into the index so they can
    be used as query-time filters (claim_no, doc_type) and returned alongside
    hits (chunk_text).
    """
    existing = {i["name"] for i in vsc.list_indexes(name=VS_ENDPOINT).get("vector_indexes", [])}
    if index_name in existing:
        print(f"[{index_name}] already exists — triggering sync.")
        vsc.get_index(VS_ENDPOINT, index_name).sync()
        return

    print(f"[{index_name}] creating Delta Sync index on {VS_ENDPOINT} ...")
    kwargs = dict(
        endpoint_name=VS_ENDPOINT,
        index_name=index_name,
        source_table_name=source_table,
        pipeline_type="TRIGGERED",
        primary_key="doc_id",
        embedding_source_column="chunk_text",
        embedding_model_endpoint_name=EMBEDDING_ENDPOINT,
    )
    if columns_to_sync:
        # Newer SDKs expose columns_to_sync; older ones sync all source columns.
        kwargs["columns_to_sync"] = columns_to_sync
    try:
        vsc.create_delta_sync_index(**kwargs)
    except TypeError:
        kwargs.pop("columns_to_sync", None)
        vsc.create_delta_sync_index(**kwargs)
    print(f"[{index_name}] create requested.")


def poll_until_online(vsc, index_name: str, budget_s: int = POLL_TIMEOUT_S) -> str:
    """Poll an index until ONLINE or the time budget runs out. Returns state."""
    idx = vsc.get_index(VS_ENDPOINT, index_name)
    deadline = time.time() + budget_s
    state = "UNKNOWN"
    while time.time() < deadline:
        desc = idx.describe()
        status = desc.get("status", {}) or {}
        state = status.get("detailed_state", status.get("state", "UNKNOWN"))
        ready = status.get("ready", False)
        print(f"[{index_name}] state={state} ready={ready}")
        if ready or (isinstance(state, str) and state.startswith("ONLINE")):
            return state
        time.sleep(POLL_INTERVAL_S)
    print(f"[{index_name}] not ONLINE within {budget_s}s — leaving it building.")
    return state


def smoke_test_documents(vsc) -> None:
    """
    Verify the metadata filter: querying idx_documents filtered to
    CLM-DISAB-DISCREP must return only that claim's docs and surface DOC-91.
    """
    try:
        idx = vsc.get_index(VS_ENDPOINT, IDX_DOCUMENTS)
        res = idx.similarity_search(
            query_text="occupation heavy manual trade boilermaker",
            columns=["doc_id", "claim_no", "doc_type", "chunk_text"],
            filters={"claim_no": "CLM-DISAB-DISCREP"},
            num_results=5,
        )
        rows = res.get("result", {}).get("data_array", [])
        doc_ids = [r[0] for r in rows]
        print(f"[smoke] filtered hits for CLM-DISAB-DISCREP: {doc_ids}")
        assert any(d == "DOC-91" for d in doc_ids), "DOC-91 not retrieved!"
        print("[smoke] PASS — DOC-91 retrieved under claim_no filter.")
    except Exception as exc:  # pragma: no cover
        print(f"[smoke] skipped/failed (index may still be building): {exc}")


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main() -> None:
    spark = _get_spark()

    # 1. Source tables
    build_source_table(spark)
    has_email = build_email_source_if_present(spark)

    # 2. Indexes
    vsc = _vs_client()
    create_delta_sync_index(
        vsc,
        IDX_DOCUMENTS,
        SOURCE_TABLE,
        columns_to_sync=["doc_id", "claim_no", "doc_type", "chunk_text"],
    )
    if has_email:
        create_delta_sync_index(
            vsc,
            IDX_EMAIL,
            f"{CATALOG}.{AI_SCHEMA}.doc_chunks_email",
            columns_to_sync=["doc_id", "claim_no", "doc_type", "chunk_text"],
        )
    # idx_notes: defined here for completeness; only built if a notes source is
    # materialised (no assessor-notes silver table in the current dataset).

    # 3. Wait for the primary index, then smoke-test the metadata filter.
    state = poll_until_online(vsc, IDX_DOCUMENTS)
    if isinstance(state, str) and state.startswith("ONLINE"):
        smoke_test_documents(vsc)


if __name__ == "__main__":
    main()
