"""Create the underwriting Vector Search index (idx_uw_notes).

Delta-sync index over momentum_uw_ai.uw_note_chunks on the shared endpoint,
using managed gte-large-en embeddings, with policy_no synced for metadata
filtering (spec R2.2). Idempotent — skips if the index already exists.

Run after build_uw_ai.sql (which creates uw_note_chunks). Uses the Vector
Search REST API via the SDK's authenticated WorkspaceClient, so it runs from
anywhere with a Databricks profile (no databricks-vectorsearch dependency).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from databricks.sdk import WorkspaceClient

ENDPOINT = "valterra-vs-endpoint"
INDEX = "elexon_app_for_settlement_acc_catalog.momentum_uw_ai.idx_uw_notes"
SOURCE = "elexon_app_for_settlement_acc_catalog.momentum_uw_ai.uw_note_chunks"
EMBED_ENDPOINT = "databricks-gte-large-en"


def main() -> None:
    w = WorkspaceClient()
    host = w.config.host.rstrip("/")
    headers = {**w.config.authenticate(), "Content-Type": "application/json"}

    # Already exists?
    check = urllib.request.Request(
        f"{host}/api/2.0/vector-search/indexes/{urllib.parse.quote(INDEX)}", headers=headers)
    try:
        urllib.request.urlopen(check)
        print(f"INDEX_EXISTS {INDEX}")
        return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    body = {
        "name": INDEX, "endpoint_name": ENDPOINT, "primary_key": "chunk_id",
        "index_type": "DELTA_SYNC",
        "delta_sync_index_spec": {
            "source_table": SOURCE, "pipeline_type": "TRIGGERED",
            "columns_to_sync": ["chunk_id", "policy_no", "chunk_text"],
            "embedding_source_columns": [
                {"name": "chunk_text", "embedding_model_endpoint_name": EMBED_ENDPOINT}
            ],
        },
    }
    req = urllib.request.Request(f"{host}/api/2.0/vector-search/indexes",
                                data=json.dumps(body).encode(), headers=headers, method="POST")
    urllib.request.urlopen(req)
    print(f"INDEX_CREATED {INDEX} (initial snapshot syncing — a few minutes to ONLINE)")


if __name__ == "__main__":
    main()
