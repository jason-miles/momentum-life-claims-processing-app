"""Page 1 — Claims Inbox [MVP]."""
from __future__ import annotations

import streamlit as st

from lib import data
from lib.config import RISK_THRESHOLD
from components import fmt_zar


def render():
    st.subheader("Claims Inbox")
    st.caption("Work queue across all claims. Filter, sort, and open a claim to see the unified case view.")

    df = data.claims_inbox()
    if df.empty:
        st.info(
            "No claims loaded. If you are running locally, connect the app to "
            "Databricks (set DATABRICKS_HOST + DATABRICKS_TOKEN) to see the live queue."
        )
        return

    c1, c2, c3 = st.columns([2, 2, 2])
    types = sorted(df["claim_type"].dropna().unique().tolist())
    states = sorted(df["state"].dropna().unique().tolist())
    sel_types = c1.multiselect("Claim type", types, default=types)
    sel_states = c2.multiselect("State", states, default=states)
    sort_by = c3.selectbox(
        "Sort by", ["risk_score", "days_in_stage", "event_date", "claim_no"], index=0
    )

    only_flags = st.checkbox("Show only flagged (high risk or occupation mismatch)", value=False)

    view = df[df["claim_type"].isin(sel_types) & df["state"].isin(sel_states)].copy()
    if only_flags:
        view = view[(view["high_risk"]) | (view["occupation_mismatch"])]
    ascending = sort_by in ("event_date", "claim_no")
    view = view.sort_values(sort_by, ascending=ascending)

    # Presentation columns with badges.
    def _risk_badge(v):
        return f"🔴 {v:.2f}" if v >= RISK_THRESHOLD else (f"🟠 {v:.2f}" if v >= 0.3 else f"🟢 {v:.2f}")

    disp = view.copy()
    disp["risk"] = disp["risk_score"].apply(_risk_badge)
    disp["SLA"] = disp["days_in_stage"].apply(lambda d: "⚠ over 20d" if d and d > 20 else "ok")
    disp["occ. mismatch"] = disp["occupation_mismatch"].apply(lambda x: "⚠ yes" if x else "—")
    disp["reqs"] = disp.apply(lambda r: f"{r['reqs_received']}/{r['reqs_total']}", axis=1)
    disp["sum assured"] = disp["sum_assured"].apply(fmt_zar)

    table = disp[[
        "claim_no", "claim_type", "state", "days_in_stage", "SLA", "risk",
        "occ. mismatch", "reqs", "sum assured", "assessor", "province",
    ]].rename(columns={"claim_no": "claim", "days_in_stage": "days in stage"})

    st.markdown(f"**{len(table)}** claims")
    event = st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Row selection -> open Claim Detail.
    selected_claim = None
    rows = event.selection.rows if event and event.selection else []
    if rows:
        selected_claim = table.iloc[rows[0]]["claim"]

    st.divider()
    fallback = st.selectbox(
        "…or pick a claim to open",
        options=view["claim_no"].tolist(),
        index=0,
    )
    chosen = selected_claim or fallback
    if st.button("Open in Claim Detail →", type="primary"):
        st.session_state["selected_claim"] = chosen
        st.session_state["nav"] = "Claim Detail"
        st.rerun()

    if selected_claim:
        st.success(f"Selected {selected_claim} — click 'Open in Claim Detail' to view.")
