"""Page 5 — Executive View [DEMO]. KPI tiles + decision donut + Genie ask."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from lib import data
from lib.config import BRAND
from components import KpiTile, GenieEmbed

_DECISION_COLORS = {
    "pay": BRAND["good"],
    "decline": BRAND["bad"],
    "refer": BRAND["warn"],
}


def render():
    st.subheader("Executive View")
    st.caption("Momentum Life claims — health at a glance. Phone-friendly.")

    cycle = data.kpi_cycle_time()
    ntu = data.kpi_ntu_rate()
    sla = data.kpi_sla_attainment()
    split = data.decision_split()

    # KPI tiles (stack on narrow screens).
    c1, c2, c3 = st.columns(3)
    with c1:
        KpiTile(
            "Avg cycle time",
            f"{cycle:.1f} d" if cycle is not None else "—",
            "lodge → decision", tone="primary",
        )
    with c2:
        KpiTile(
            "NTU rate",
            f"{ntu*100:.1f}%" if ntu is not None else "—",
            "pre-lodge drop-off", tone="warn",
        )
    with c3:
        KpiTile(
            "SLA attainment",
            f"{sla:.0f}%" if sla is not None else "—",
            "within 20 days", tone="good",
        )

    if cycle is None and ntu is None and sla is None and split.empty:
        st.info("Connect the app to Databricks to populate the executive KPIs.")
        return

    st.markdown("")
    d1, d2 = st.columns([1, 1])
    with d1:
        st.markdown("#### Decision split")
        if not split.empty:
            agg = split.groupby("decision", as_index=False)["n"].sum()
            fig = px.pie(
                agg, names="decision", values="n", hole=0.55,
                color="decision", color_discrete_map=_DECISION_COLORS,
            )
            fig.update_layout(height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with d2:
        st.markdown("#### Claims by province")
        prov = data.claims_by_province()
        if not prov.empty:
            fig = px.bar(
                prov, x="n_claims", y="province", orientation="h",
                color_discrete_sequence=[BRAND["primary"]],
            )
            fig.update_layout(height=320, margin=dict(t=10, b=10),
                              yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("#### Ask the numbers")
    GenieEmbed(
        state_key="exec_genie",
        suggestions=[
            "What is the overall NTU rate?",
            "Which claim type has the worst SLA attainment?",
            "Total sum assured across paid claims?",
        ],
    )
