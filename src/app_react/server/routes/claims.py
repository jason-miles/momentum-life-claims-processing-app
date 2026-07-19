"""API routes for the Momentum Claims portal."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from server import data
from server.agent_client import draft_synopsis, ask_claim_copilot
from server.genie_client import ask_genie
from server.sql_client import connection_ok, execute
from server.config import o

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    ok, msg = connection_ok()
    return {"status": "ok", "app": "momentum-claims-portal", "db_connected": ok, "db_message": msg}


@router.get("/inbox")
def inbox():
    return {"claims": data.claims_inbox()}


@router.get("/claim/{claim_no}")
def claim(claim_no: str):
    return data.claim_detail(claim_no)


@router.get("/claim/{claim_no}/synopsis")
def synopsis(claim_no: str):
    return draft_synopsis(claim_no)


class CopilotIn(BaseModel):
    claim_no: str
    question: str


@router.post("/copilot")
def copilot(body: CopilotIn):
    return {"answer": ask_claim_copilot(body.claim_no, body.question)}


class GenieIn(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/genie")
def genie(body: GenieIn):
    return ask_genie(body.question, body.conversation_id)


@router.get("/ntu")
def ntu():
    return {"funnel": data.ntu_funnel(), "at_risk": data.ntu_at_risk()}


@router.get("/ops")
def ops():
    return {"metrics": data.ops_metrics(), "throughput": data.throughput_per_assessor()}


@router.get("/exec")
def exec_view():
    return {
        "kpis": data.exec_kpis(),
        "decision_split": data.decision_split(),
        "by_province": data.claims_by_province(),
    }


@router.get("/requirements")
def requirements():
    return {"analytics": data.requirement_analytics()}


@router.get("/assessors")
def assessors():
    return {"assessors": data.assessors()}


@router.get("/admin/catalog")
def admin_catalog():
    return {"inventory": data.catalog_inventory()}


class ActionIn(BaseModel):
    claim_no: str
    user_role: str
    action: str
    payload: str | None = ""


@router.post("/action")
def record_action(body: ActionIn):
    """Persist an Accept/Edit/Record-referral action to the ops audit table."""
    safe = lambda x: (x or "").replace("'", "''")
    try:
        execute(
            f"INSERT INTO {o('app_events')} "
            f"(event_id, claim_no, user_role, action, payload, ts) VALUES "
            f"(uuid(), '{safe(body.claim_no)}', '{safe(body.user_role)}', "
            f"'{safe(body.action)}', '{safe(body.payload)}', current_timestamp())"
        )
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
