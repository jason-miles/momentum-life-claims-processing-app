"""API routes for the Underwriting Co-Pilot + underwriting analytics."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from server import uw_data
from server.genie_client import ask_genie
from server.config import UW_GENIE_SPACE_ID

router = APIRouter(prefix="/api/uw")


class UwGenieIn(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/genie")
def genie(body: UwGenieIn):
    return ask_genie(body.question, body.conversation_id, space_id=UW_GENIE_SPACE_ID)


@router.get("/inbox")
def inbox():
    return {"cases": uw_data.uw_inbox()}


@router.get("/case/{policy_no}")
def case(policy_no: str):
    return uw_data.uw_case(policy_no)


@router.get("/case/{policy_no}/synopsis")
def synopsis(policy_no: str):
    return uw_data.uw_synopsis(policy_no)


@router.get("/exec")
def exec_view():
    return uw_data.uw_exec()


@router.get("/ntu")
def ntu():
    return uw_data.uw_ntu()


@router.get("/requirements")
def requirements():
    return {"analytics": uw_data.uw_requirements()}


@router.get("/ops")
def ops():
    return {"ops": uw_data.uw_ops()}
