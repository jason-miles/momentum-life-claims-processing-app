"""Page 3 — AI Copilot [MVP]. Full-screen Genie chat over all claims."""
from __future__ import annotations

import streamlit as st

from components import GenieEmbed
from lib.config import GENIE_SPACE_ID

SUGGESTIONS = [
    "Which claims have an occupation mismatch?",
    "Show me pre-lodge claims at risk of drop-off",
    "What's the average cycle time for disability claims?",
    "How many claims breached the 20-day SLA?",
    "What is the NTU rate by claim type?",
    "Show the decision split for death claims",
    "Which requirement codes are most often outstanding?",
    "Which assessor has the highest throughput?",
    "List claims with a risk score above 0.6",
    "How many claims are in each state?",
]


def render():
    st.subheader("AI Copilot")
    st.caption(
        "Ask anything about the Momentum claims book. Backed by the "
        "**Momentum Claims Analyst** Genie space over the gold layer."
    )
    if not GENIE_SPACE_ID:
        st.warning("Genie space not configured (GENIE_SPACE_ID missing).")
        return

    st.markdown("**Try one of these:**")
    GenieEmbed(state_key="global_copilot", suggestions=SUGGESTIONS)
