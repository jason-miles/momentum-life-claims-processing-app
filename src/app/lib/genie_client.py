"""Thin wrapper over the Databricks Genie Conversation API.

Exposes ``ask_genie(question, conversation_id=None) -> dict`` returning a
normalised payload::

    {
      "ok": bool,
      "text": "<natural language answer / narrative>",
      "sql": "<generated SQL, if any>",
      "dataframe": <pandas.DataFrame or None>,
      "conversation_id": "<id to continue the thread>",
      "error": "<message if ok is False>",
    }

Uses the Databricks SDK's Genie client when available. Degrades gracefully:
if the SDK / space / auth is unavailable it returns ``ok=False`` with a message
rather than raising, so the app never crashes.
"""
from __future__ import annotations

import pandas as pd

from lib.config import GENIE_SPACE_ID, WAREHOUSE_ID


def _workspace_client():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def _attachment_to_df(w, statement_id: str) -> pd.DataFrame | None:
    """Fetch the result rows for a Genie query attachment."""
    try:
        result = w.statement_execution.get_statement(statement_id)
        data = result.result
        if data is None or data.data_array is None:
            return None
        cols = [c.name for c in result.manifest.schema.columns]
        return pd.DataFrame(data.data_array, columns=cols)
    except Exception:
        return None


def ask_genie(question: str, conversation_id: str | None = None) -> dict:
    """Ask the Momentum Claims Analyst Genie space a question."""
    out = {
        "ok": False,
        "text": "",
        "sql": "",
        "dataframe": None,
        "conversation_id": conversation_id,
        "error": "",
    }
    if not GENIE_SPACE_ID:
        out["error"] = "GENIE_SPACE_ID is not configured."
        return out

    try:
        w = _workspace_client()
        genie = w.genie

        if conversation_id:
            msg = genie.create_message_and_wait(
                GENIE_SPACE_ID, conversation_id, question
            )
        else:
            msg = genie.start_conversation_and_wait(GENIE_SPACE_ID, question)
            conversation_id = getattr(msg, "conversation_id", None)

        out["conversation_id"] = conversation_id

        texts: list[str] = []
        attachments = getattr(msg, "attachments", None) or []
        for att in attachments:
            text_att = getattr(att, "text", None)
            if text_att is not None and getattr(text_att, "content", None):
                texts.append(text_att.content)
            query_att = getattr(att, "query", None)
            if query_att is not None:
                out["sql"] = getattr(query_att, "query", "") or out["sql"]
                desc = getattr(query_att, "description", None)
                if desc:
                    texts.append(desc)
                sid = getattr(query_att, "statement_id", None)
                if sid:
                    df = _attachment_to_df(w, sid)
                    if df is not None:
                        out["dataframe"] = df

        # Fallback content on the message itself.
        if not texts and getattr(msg, "content", None):
            texts.append(msg.content)

        out["text"] = "\n\n".join(t for t in texts if t).strip() or (
            "Genie processed the question but returned no narrative. "
            "See the results table below."
        )
        out["ok"] = True
        return out
    except Exception as exc:  # never crash the app
        out["error"] = (
            f"Genie is unavailable in this environment ({exc}). "
            "You can still use the SQL-backed pages."
        )
        return out
