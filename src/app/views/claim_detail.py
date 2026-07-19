"""Page 2 — Claim Detail [MVP]. The centerpiece unified case view + AI synopsis."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from lib import data
from lib.config import BRAND, o
from components import (
    ClaimCard,
    SynopsisPanel,
    RequirementChecklist,
    DocumentViewer,
    CopilotChat,
    fmt_zar,
)


def _record_event(claim_no: str, role: str, action: str, payload: dict) -> tuple[bool, str]:
    """Write an app event to the ops schema. Returns (ok, message)."""
    from lib.sql_client import execute, ConnectionUnavailable

    ev_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    payload_str = json.dumps(payload).replace("'", "''")
    action_s = action.replace("'", "''")
    role_s = role.replace("'", "''")
    sql = (
        f"INSERT INTO {o('app_events')} (event_id, claim_no, user_role, action, payload, ts) "
        f"VALUES ('{ev_id}', '{claim_no}', '{role_s}', '{action_s}', '{payload_str}', "
        f"TIMESTAMP '{ts}')"
    )
    try:
        execute(sql)
        return True, f"Recorded '{action}' for {claim_no}."
    except ConnectionUnavailable as exc:
        return False, f"Not connected — action not persisted ({exc})."
    except Exception as exc:
        return False, f"Could not persist action: {exc}"


def _timeline(events: pd.DataFrame):
    if events is None or events.empty:
        st.caption("No timeline events.")
        return
    for _, e in events.iterrows():
        ts = e.get("event_ts")
        ts_str = pd.to_datetime(ts).strftime("%Y-%m-%d") if ts is not None else "—"
        st.markdown(
            f"<div style='border-left:3px solid {BRAND['accent']};padding:2px 0 2px 12px;margin:2px 0;'>"
            f"<b>{e.get('event','')}</b> "
            f"<span style='color:#8a97a6;font-size:0.8rem;'>· {ts_str}</span></div>",
            unsafe_allow_html=True,
        )


def render():
    role = st.session_state.get("role", "Assessor")
    claim_no = st.session_state.get("selected_claim")

    if not claim_no:
        inbox = data.claims_inbox()
        if inbox.empty:
            st.info("Connect to Databricks and pick a claim from the Claims Inbox.")
            return
        claim_no = st.selectbox("Select a claim", inbox["claim_no"].tolist())
        st.session_state["selected_claim"] = claim_no

    detail = data.claim_detail(claim_no)
    row = detail["row"]
    if row is None:
        st.warning(f"Could not load {claim_no}. Not connected, or claim not found.")
        return

    ClaimCard(row)

    left, right = st.columns([1.05, 1.0])

    # ------------------------------------------------------------------ LEFT
    with left:
        st.markdown("### Unified Case View")

        in_force = str(row.get("policy_status")) == "in_force"
        st.markdown(
            f"**Policy in force:** {'✔' if in_force else '✘'} "
            f"<span style='color:#8a97a6'>({row.get('policy_status')})</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**Benefit:** {row.get('benefit_type','?')} · "
            f"**{fmt_zar(row.get('sum_assured'))}** · status: {row.get('benefit_status','?')}"
        )

        occ_i = row.get("occupation_at_inception")
        occ_c = row.get("occupation_at_claim")
        mismatch = bool(row.get("occupation_mismatch"))
        occ_color = BRAND["bad"] if mismatch else "#2b3a4a"
        st.markdown(
            f"**Occupation:** <span style='color:{occ_color}'>inception "
            f"'{occ_i}' → claim '{occ_c}'{' ⚠ MISMATCH' if mismatch else ''}</span>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**Requirements:** {row.get('reqs_received')}/{row.get('reqs_total')} received"
        )
        RequirementChecklist(detail["requirements"])

        tp = row.get("tp_summary")
        if tp:
            st.markdown("**Third-party checks**")
            for chip in str(tp).split(";"):
                chip = chip.strip()
                if chip:
                    st.markdown(
                        f"<span style='display:inline-block;background:{BRAND['bg_soft']};"
                        f"border:1px solid #d7e0ea;border-radius:12px;padding:3px 10px;"
                        f"margin:2px 4px 2px 0;font-size:0.8rem;'>{chip}</span>",
                        unsafe_allow_html=True,
                    )

        st.markdown("**Timeline**")
        _timeline(detail["events"])

        st.markdown("**Documents**")
        DocumentViewer(detail["documents"])

    # ------------------------------------------------------------------ RIGHT
    with right:
        cache_key = f"synopsis_{claim_no}"
        if cache_key not in st.session_state:
            with st.spinner("Drafting AI synopsis…"):
                from lib.agent_client import draft_synopsis

                st.session_state[cache_key] = draft_synopsis(claim_no)
        synopsis = st.session_state[cache_key]
        SynopsisPanel(synopsis)

        if st.button("↻ Re-draft synopsis", key=f"redraft_{claim_no}"):
            st.session_state.pop(cache_key, None)
            st.rerun()

        st.markdown("---")
        st.markdown("**Copilot — ask about this claim**")
        from lib.agent_client import ask_claim_copilot

        CopilotChat(
            state_key=f"claim_{claim_no}",
            on_ask=lambda q: ask_claim_copilot(claim_no, q),
            suggestions=[
                "Why is this flagged?",
                "What is still outstanding?",
                "Is the policy in force?",
            ],
            placeholder="Ask about this claim…",
        )

    # ------------------------------------------------------------------ BOTTOM
    st.divider()
    st.markdown("### Actions")
    risk = float(row.get("risk_score") or 0)
    fraud_tone = BRAND["bad"] if risk >= 0.6 else (BRAND["warn"] if risk >= 0.3 else BRAND["good"])
    st.markdown(
        f"Fraud score <span style='color:{fraud_tone};font-weight:700'>{risk:.2f}</span> "
        f"<span style='background:#eee;border-radius:6px;padding:1px 6px;font-size:0.75rem'>[MOCKED]</span>",
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns(3)
    assessor_list = data.assessors()

    with b1:
        referral_to = st.selectbox("Assign referral to", assessor_list, key=f"ref_{claim_no}")
        comment = st.text_input("Comment", key=f"comment_{claim_no}", placeholder="Add a note…")

    with b2:
        st.write("")
        if st.button("Accept synopsis", type="primary", key=f"accept_{claim_no}"):
            ok, msg = _record_event(
                claim_no, role, "accept_synopsis",
                {"recommendation": synopsis.get("recommendation"), "comment": comment},
            )
            (st.success if ok else st.warning)(msg)
        if st.button("Edit synopsis", key=f"edit_{claim_no}"):
            st.session_state[f"editing_{claim_no}"] = True

    with b3:
        st.write("")
        if st.button("Record referral", key=f"recref_{claim_no}"):
            ok, msg = _record_event(
                claim_no, role, "record_referral",
                {"assigned_to": referral_to, "comment": comment},
            )
            (st.success if ok else st.warning)(msg)

    if st.session_state.get(f"editing_{claim_no}"):
        edited = st.text_area(
            "Edit synopsis markdown", value=synopsis.get("markdown", ""),
            height=200, key=f"editarea_{claim_no}",
        )
        if st.button("Save edited synopsis", key=f"savesyn_{claim_no}"):
            synopsis["markdown"] = edited
            st.session_state[cache_key] = synopsis
            ok, msg = _record_event(
                claim_no, role, "edit_synopsis", {"comment": comment}
            )
            st.session_state[f"editing_{claim_no}"] = False
            (st.success if ok else st.warning)(msg)
            st.rerun()
