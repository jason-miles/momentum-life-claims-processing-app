"""Momentum Life — Assessment Analytics Portal (Databricks App).

Streamlit entry point. Sidebar navigation across 7 pages plus a "View as"
role switcher and a Momentum-branded header. Degrades gracefully when not
connected to Databricks.

Run locally:  cd src/app && streamlit run app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# Ensure local package imports work regardless of CWD.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.config import BRAND, ROLES  # noqa: E402
from views import (  # noqa: E402
    inbox,
    claim_detail,
    copilot,
    ntu_ops,
    exec_view,
    fraud,
    admin,
)

st.set_page_config(
    page_title="Momentum Life — Assessment Analytics Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Global styling ---------------------------------------------------------
st.markdown(
    f"""
    <style>
      .stApp {{ background: {BRAND['bg_soft']}; }}
      section[data-testid="stSidebar"] {{ background: {BRAND['primary']}; }}
      section[data-testid="stSidebar"] * {{ color: #ffffff; }}
      section[data-testid="stSidebar"] .stRadio label p {{ color:#ffffff; }}
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = {
    "Claims Inbox": ("🗂️", "MVP", inbox.render),
    "Claim Detail": ("🔍", "MVP", claim_detail.render),
    "AI Copilot": ("🤖", "MVP", copilot.render),
    "NTU / Ops Dashboard": ("📉", "MVP", ntu_ops.render),
    "Executive View": ("📊", "DEMO", exec_view.render),
    "Fraud Workbench": ("🕵️", "MOCKED", fraud.render),
    "Admin Console": ("⚙️", "DEMO", admin.render),
}


def _header():
    logo_candidates = [
        APP_DIR / ".." / ".." / "logo" / "momentum_life_logo.png",
        APP_DIR / "assets" / "momentum_life_logo.png",
    ]
    c1, c2 = st.columns([1, 6])
    logo_path = next((p for p in logo_candidates if p.exists()), None)
    with c1:
        if logo_path:
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown(
                f"<div style='font-size:2rem'>🛡️</div>", unsafe_allow_html=True
            )
    with c2:
        st.markdown(
            f"<div style='padding-top:6px'>"
            f"<span style='color:{BRAND['primary']};font-size:1.5rem;font-weight:800'>"
            f"Momentum Life</span><br>"
            f"<span style='color:#5b6b7c;font-size:0.95rem'>Assessment Analytics Portal</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _sidebar() -> str:
    st.sidebar.markdown("### Assessment Analytics Portal")

    role = st.sidebar.selectbox(
        "👤 View as", ROLES, index=ROLES.index(st.session_state.get("role", "Assessor"))
    )
    st.session_state["role"] = role

    st.sidebar.markdown("---")
    labels = [f"{icon}  {name}" for name, (icon, _tag, _fn) in PAGES.items()]
    names = list(PAGES.keys())

    # Honour programmatic nav (e.g. Inbox -> Claim Detail).
    default_name = st.session_state.get("nav", names[0])
    if default_name not in names:
        default_name = names[0]
    default_idx = names.index(default_name)

    choice = st.sidebar.radio(
        "Navigate", labels, index=default_idx, label_visibility="collapsed"
    )
    selected = names[labels.index(choice)]
    st.session_state["nav"] = selected

    tag = PAGES[selected][1]
    st.sidebar.caption(f"Page status: {tag}")

    # Connection status.
    st.sidebar.markdown("---")
    try:
        from lib.sql_client import connection_ok

        ok, msg = connection_ok()
    except Exception as exc:  # pragma: no cover
        ok, msg = False, str(exc)
    if ok:
        st.sidebar.success("Connected to Databricks", icon="✅")
    else:
        st.sidebar.warning("Demo mode — not connected", icon="🔌")

    st.sidebar.caption("Data residency: eu-west-1 (Ireland). No US regions.")
    return selected


def main():
    _header()
    st.markdown(
        f"<hr style='border:none;border-top:2px solid {BRAND['primary']};margin:6px 0 14px'>",
        unsafe_allow_html=True,
    )
    selected = _sidebar()

    icon, tag, render_fn = PAGES[selected]
    st.markdown(
        f"<span style='background:{BRAND['primary']};color:#fff;border-radius:6px;"
        f"padding:2px 8px;font-size:0.7rem;font-weight:700'>{tag}</span>",
        unsafe_allow_html=True,
    )
    try:
        render_fn()
    except Exception as exc:  # never show a raw stack trace to demo audiences
        st.error(
            "This page hit an unexpected error. If you are running locally, "
            "connect the app to Databricks (DATABRICKS_HOST + DATABRICKS_TOKEN)."
        )
        with st.expander("Technical detail"):
            st.exception(exc)


if __name__ == "__main__":
    main()
