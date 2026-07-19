"""Reusable Streamlit widgets. All are functions that render (or return) widgets.

NO html <form> elements are used anywhere — Streamlit widgets only.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from lib.config import BRAND


def fmt_zar(val) -> str:
    """Format a number as South African Rand, e.g. R1,800,000."""
    try:
        return f"R{float(val):,.0f}"
    except (TypeError, ValueError):
        return "—" if val in (None, "") else str(val)


# --------------------------------------------------------------------------- #
def KpiTile(label: str, value: str, sub: str | None = None, tone: str = "primary"):
    """A large KPI card."""
    color = BRAND.get(tone, BRAND["primary"])
    sub_html = f"<div style='color:#5b6b7c;font-size:0.8rem;margin-top:4px'>{sub}</div>" if sub else ""
    st.markdown(
        f"""
        <div style="background:#fff;border:1px solid #e3e9f0;border-left:6px solid {color};
                    border-radius:10px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="color:#5b6b7c;font-size:0.78rem;text-transform:uppercase;
                      letter-spacing:.04em;font-weight:600;">{label}</div>
          <div style="color:{color};font-size:2.0rem;font-weight:700;line-height:1.1;
                      margin-top:6px;">{value}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def DiscrepancyBadge(text: str, tone: str = "bad"):
    """A pill/badge for a discrepancy or flag."""
    color = BRAND.get(tone, BRAND["bad"])
    st.markdown(
        f"""<span style="display:inline-block;background:{color}1A;color:{color};
        border:1px solid {color}55;border-radius:14px;padding:3px 10px;margin:2px 4px 2px 0;
        font-size:0.8rem;font-weight:600;">⚠ {text}</span>""",
        unsafe_allow_html=True,
    )


def _citation_chip(text: str) -> str:
    c = BRAND["primary_light"]
    return (
        f"<span style='display:inline-block;background:{c}14;color:{c};"
        f"border:1px solid {c}44;border-radius:6px;padding:2px 8px;margin:2px 4px 2px 0;"
        f"font-family:monospace;font-size:0.75rem;'>[{text}]</span>"
    )


def ClaimCard(row: dict):
    """Compact header card for a single claim (used on Claim Detail)."""
    risk = float(row.get("risk_score") or 0)
    risk_tone = "bad" if risk >= 0.6 else ("warn" if risk >= 0.3 else "good")
    st.markdown(
        f"""
        <div style="background:{BRAND['primary']};color:#fff;border-radius:12px;
                    padding:16px 20px;margin-bottom:8px;">
          <div style="font-size:1.4rem;font-weight:700;">{row.get('claim_no','?')}
             <span style="font-size:0.9rem;font-weight:500;opacity:.85;">
             · {str(row.get('claim_type','')).title()} · {row.get('province','')}</span>
          </div>
          <div style="opacity:.9;margin-top:4px;font-size:0.9rem;">
             State: <b>{row.get('state','?')}</b> &nbsp;·&nbsp;
             Assessor: <b>{row.get('assessor','?')}</b> &nbsp;·&nbsp;
             Sum assured: <b>{fmt_zar(row.get('sum_assured'))}</b>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='color:{BRAND[risk_tone]};font-weight:700;'>Risk {risk:.2f}</span>",
        unsafe_allow_html=True,
    )


def RequirementChecklist(reqs: pd.DataFrame):
    """Render a requirement checklist (received = green check, outstanding = red)."""
    if reqs is None or reqs.empty:
        st.caption("No requirement records found.")
        return
    for _, r in reqs.iterrows():
        received = str(r.get("status", "")).lower() == "received"
        icon = "✅" if received else "⛔"
        color = BRAND["good"] if received else BRAND["bad"]
        st.markdown(
            f"<div style='padding:3px 0;'>{icon} "
            f"<b style='color:{color};'>{r.get('code','')}</b> — "
            f"{r.get('description','')}"
            f"<span style='color:#8a97a6;font-size:0.8rem;'> ({r.get('status','')})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def DocumentViewer(docs: pd.DataFrame):
    """List claim documents with type; expandable parsed text."""
    if docs is None or docs.empty:
        st.caption("No documents linked to this claim.")
        return
    for _, d in docs.iterrows():
        title = f"📄 {d.get('doc_id','?')} · {str(d.get('doc_type','')).replace('_',' ').title()}"
        with st.expander(title):
            st.caption(f"FileNet ref: {d.get('filenet_ref','—')}")
            txt = d.get("parsed_text")
            if txt:
                st.write(txt)
            else:
                st.caption("No parsed text available.")


def SynopsisPanel(synopsis: dict):
    """Render the AI synopsis: markdown body + discrepancy badges + citations + rec."""
    st.markdown(
        f"<div style='color:{BRAND['warn']};font-weight:600;font-size:0.8rem;'>"
        "AI Synopsis (draft — review before use)</div>",
        unsafe_allow_html=True,
    )
    src = synopsis.get("source", "")
    if src:
        st.caption(f"generated via: {src}")

    st.markdown(synopsis.get("markdown", "_No synopsis available._"))

    discrepancies = synopsis.get("discrepancies") or []
    if discrepancies:
        st.markdown("**Discrepancies**")
        for d in discrepancies:
            DiscrepancyBadge(d)

    citations = synopsis.get("citations") or []
    if citations:
        chips = "".join(_citation_chip(c) for c in citations)
        st.markdown("**Citations** " + chips, unsafe_allow_html=True)

    rec = synopsis.get("recommendation", "N/A")
    rec_tone = "bad" if rec.startswith(("REFER", "DECLINE")) else (
        "warn" if rec.startswith("PEND") else "good"
    )
    st.markdown(
        f"<div style='margin-top:10px;padding:8px 12px;border-radius:8px;"
        f"background:{BRAND[rec_tone]}14;border:1px solid {BRAND[rec_tone]}55;'>"
        f"<b style='color:{BRAND[rec_tone]};'>Recommend: {rec}</b></div>",
        unsafe_allow_html=True,
    )


def CopilotChat(state_key: str, on_ask, suggestions: Iterable[str] | None = None,
                placeholder: str = "Ask about this claim…"):
    """A chat box backed by ``on_ask(question) -> str``.

    ``state_key`` namespaces the message history in session_state.
    """
    hist_key = f"copilot_hist_{state_key}"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    if suggestions:
        cols = st.columns(min(3, len(list(suggestions))) or 1)
        for i, q in enumerate(suggestions):
            if cols[i % len(cols)].button(q, key=f"{state_key}_sugg_{i}"):
                st.session_state[f"{state_key}_pending"] = q

    for msg in st.session_state[hist_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pop(f"{state_key}_pending", None)
    typed = st.chat_input(placeholder, key=f"{state_key}_input")
    question = typed or pending
    if question:
        st.session_state[hist_key].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                answer = on_ask(question)
            st.markdown(answer)
        st.session_state[hist_key].append({"role": "assistant", "content": answer})


def GenieEmbed(state_key: str = "genie", suggestions: Iterable[str] | None = None):
    """Chat surface wired to the Genie space via ask_genie."""
    from lib.genie_client import ask_genie

    conv_key = f"genie_conv_{state_key}"

    def _on_ask(question: str) -> str:
        conv_id = st.session_state.get(conv_key)
        res = ask_genie(question, conversation_id=conv_id)
        if res.get("conversation_id"):
            st.session_state[conv_key] = res["conversation_id"]
        if not res.get("ok"):
            return res.get("error", "Genie is unavailable.")
        parts = [res.get("text", "")]
        df = res.get("dataframe")
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        if res.get("sql"):
            with st.expander("Generated SQL"):
                st.code(res["sql"], language="sql")
        return "\n\n".join(p for p in parts if p) or "(no narrative)"

    CopilotChat(
        state_key=state_key,
        on_ask=_on_ask,
        suggestions=suggestions,
        placeholder="Ask the Momentum Claims Analyst…",
    )
