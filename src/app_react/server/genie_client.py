"""Thin wrapper over the Databricks Genie Conversation API (streamlit-free).

``ask_genie(question, conversation_id=None) -> dict`` returns a JSON-ready
payload with the narrative, generated SQL, result rows, and a conversation id
to continue the thread. Degrades gracefully (never raises).
"""
from __future__ import annotations

from server.config import GENIE_SPACE_ID


def _workspace_client():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def _attachment_rows(w, statement_id: str) -> list[dict] | None:
    try:
        result = w.statement_execution.get_statement(statement_id)
        data = result.result
        if data is None or data.data_array is None:
            return None
        cols = [c.name for c in result.manifest.schema.columns]
        return [dict(zip(cols, row)) for row in data.data_array]
    except Exception:
        return None


def ask_genie(question: str, conversation_id: str | None = None,
              space_id: str | None = None) -> dict:
    out = {
        "ok": False, "text": "", "sql": "", "rows": None,
        "conversation_id": conversation_id, "error": "",
    }
    sid = space_id or GENIE_SPACE_ID
    if not sid:
        out["error"] = "Genie space id is not configured."
        return out

    try:
        w = _workspace_client()
        genie = w.genie

        if conversation_id:
            msg = genie.create_message_and_wait(sid, conversation_id, question)
        else:
            msg = genie.start_conversation_and_wait(sid, question)
            conversation_id = getattr(msg, "conversation_id", None)

        out["conversation_id"] = conversation_id

        texts: list[str] = []
        for att in (getattr(msg, "attachments", None) or []):
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
                    rows = _attachment_rows(w, sid)
                    if rows is not None:
                        out["rows"] = rows

        if not texts and getattr(msg, "content", None):
            texts.append(msg.content)

        out["text"] = "\n\n".join(t for t in texts if t).strip() or (
            "Genie processed the question but returned no narrative. See the results table."
        )
        out["ok"] = True
        return out
    except Exception as exc:
        out["error"] = (
            f"Genie is unavailable in this environment ({exc}). "
            "You can still use the SQL-backed pages."
        )
        return out
