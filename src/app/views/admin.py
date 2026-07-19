"""Page 7 — Admin Console [DEMO]."""
from __future__ import annotations

import streamlit as st

from lib import data
from lib.config import CATALOG, GOLD, WAREHOUSE_ID


def render():
    st.subheader("Admin Console")
    st.caption("Data-product catalog, governance and residency for the claims demo.")

    st.markdown("#### Data products (gold layer)")
    inv = data.catalog_inventory()
    if inv.empty:
        st.info("Connect the app to Databricks to inventory the gold objects.")
    else:
        st.dataframe(inv, hide_index=True, use_container_width=True)
        st.caption(f"Catalog `{CATALOG}` · schema `{GOLD}` · warehouse `{WAREHOUSE_ID}`")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Lineage")
        st.markdown(
            "- bronze → silver → gold → metric views\n"
            "- Open **Catalog Explorer → Lineage** on any gold view to trace "
            "upstream silver tables and downstream dashboards / Genie."
        )
        st.link_button(
            "Open Catalog Explorer",
            f"https://fevm-elexon-app-for-settlement-acc.cloud.databricks.com/explore/data/{CATALOG}/{GOLD}",
        )
    with c2:
        st.markdown("#### Agent eval results (placeholder)")
        import pandas as pd

        st.dataframe(
            pd.DataFrame(
                [
                    {"metric": "groundedness", "score": "—", "status": "pending"},
                    {"metric": "citation accuracy", "score": "—", "status": "pending"},
                    {"metric": "recommendation match", "score": "—", "status": "pending"},
                ]
            ),
            hide_index=True, use_container_width=True,
        )

    st.divider()
    st.info(
        "**Data residency:** all compute, storage, model serving and inference "
        "run in-region. Production target is **eu-west-1 (Ireland)** — no data "
        "leaves the approved region (US regions are explicitly disallowed).",
        icon="🌍",
    )
