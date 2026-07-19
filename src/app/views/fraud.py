"""Page 6 — Fraud Workbench [MOCKED]."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from lib import data
from lib.config import BRAND, RISK_THRESHOLD
from components import fmt_zar


def render():
    st.subheader("Fraud Workbench")
    st.warning(
        "**[MOCKED]** — Relationship flags and network links on this page are "
        "fabricated for demonstration. The underlying risk_score is real; the "
        "fraud-ring narrative is illustrative only.",
        icon="⚠",
    )

    df = data.claims_inbox()
    if df.empty:
        st.info("Connect the app to Databricks to load claims for scoring.")
        return

    df = df.sort_values("risk_score", ascending=False).copy()

    # Fabricated relationship flags (deterministic from claim_no hash).
    def _rel_flag(claim_no: str) -> str:
        h = sum(ord(c) for c in str(claim_no))
        if h % 7 == 0:
            return "shared bank account"
        if h % 5 == 0:
            return "shared address"
        if h % 3 == 0:
            return "prior claim at other insurer"
        return "—"

    df["relationship flag [MOCKED]"] = df["claim_no"].apply(_rel_flag)
    df["risk"] = df["risk_score"].round(2)
    df["sum assured"] = df["sum_assured"].apply(fmt_zar)

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.markdown("#### Claims by risk score")
        st.dataframe(
            df[[
                "claim_no", "claim_type", "state", "risk",
                "relationship flag [MOCKED]", "sum assured", "assessor",
            ]].rename(columns={"claim_no": "claim"}),
            hide_index=True, use_container_width=True,
            column_config={
                "risk": st.column_config.ProgressColumn(
                    "risk", min_value=0.0, max_value=1.0, format="%.2f"
                )
            },
        )
    with c2:
        st.markdown("#### Risk distribution")
        fig = px.histogram(
            df, x="risk_score", nbins=20,
            color_discrete_sequence=[BRAND["primary"]],
        )
        fig.add_vline(x=RISK_THRESHOLD, line_dash="dash", line_color=BRAND["bad"],
                      annotation_text="high-risk 0.6")
        fig.update_layout(height=340, margin=dict(t=10, b=10),
                          xaxis_title="risk score", yaxis_title="claims")
        st.plotly_chart(fig, use_container_width=True)

        high = int((df["risk_score"] >= RISK_THRESHOLD).sum())
        st.metric("High-risk claims (≥ 0.6)", high)
