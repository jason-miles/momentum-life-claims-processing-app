"""Page 4 — NTU / Ops Dashboard [MVP]."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from lib import data
from lib.config import BRAND

_SEQ = [BRAND["primary"], BRAND["accent"], BRAND["warn"], BRAND["good"], BRAND["bad"]]


def render():
    st.subheader("NTU / Ops Dashboard")
    st.caption("Pre-lodge drop-off (Not-Taken-Up) leakage and operational throughput / SLA.")

    funnel = data.ntu_funnel()
    at_risk = data.ntu_at_risk()
    ops = data.ops_metrics()

    if funnel.empty and ops.empty:
        st.info("No data — connect the app to Databricks to populate these charts.")
        return

    # --- NTU funnel ----------------------------------------------------------
    st.markdown("#### NTU funnel by claim type & state")
    if not funnel.empty:
        fig = px.bar(
            funnel.sort_values(["claim_type", "state"]),
            x="state", y="n_claims", color="claim_type", barmode="group",
            color_discrete_sequence=_SEQ,
            labels={"n_claims": "claims", "state": "state"},
        )
        fig.update_layout(height=340, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("NTU count overlaid where present.")
        ntu_only = funnel[funnel["n_ntu"] > 0]
        if not ntu_only.empty:
            st.dataframe(
                ntu_only[["claim_type", "state", "n_claims", "n_ntu"]],
                hide_index=True, use_container_width=True,
            )

    # --- At-risk list --------------------------------------------------------
    st.markdown("#### Pre-lodge claims at risk of drop-off")
    if not at_risk.empty:
        st.dataframe(
            at_risk,
            hide_index=True, use_container_width=True,
            column_config={
                "drop_off_propensity": st.column_config.ProgressColumn(
                    "drop-off propensity", min_value=0.0, max_value=1.0, format="%.2f"
                )
            },
        )
    else:
        st.caption("No at-risk pre-lodge claims.")

    # --- SLA + throughput ----------------------------------------------------
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### SLA breaches")
        if not ops.empty:
            decided = ops.dropna(subset=["sla_breach"])
            breaches = int(decided["sla_breach"].sum()) if not decided.empty else 0
            total = len(decided)
            st.metric("SLA breaches (decided claims)", f"{breaches} / {total}")
            breach_df = decided[decided["sla_breach"] == True][  # noqa: E712
                ["claim_no", "claim_type", "assessor", "days_lodge_to_decision"]
            ].sort_values("days_lodge_to_decision", ascending=False)
            if not breach_df.empty:
                st.dataframe(breach_df.head(20), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("#### Throughput per assessor")
        tp = data.throughput_per_assessor()
        if not tp.empty:
            fig = px.bar(
                tp, x="assessor", y="n_decided",
                color_discrete_sequence=[BRAND["primary"]],
                labels={"n_decided": "decided claims"},
            )
            fig.update_layout(height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
