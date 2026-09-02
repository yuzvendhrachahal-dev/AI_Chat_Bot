"""
Agent Router
============
Handles routes for:
  - GET  /agent/events
  - POST /agent/login
  - GET  /agent/sessions
  - GET  /agent/all-sessions
  - GET  /agent/history/{session_id}
  - POST /agent/claim/{session_id}
  - POST /agent/reply
  - POST /agent/close
  - GET  /agent/dashboard
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.agent_service import (
    build_agent_events_response,
    process_agent_login,
    process_agent_sessions,
    process_agent_all_sessions,
    process_agent_history,
    process_agent_claim,
    process_agent_reply,
    process_agent_close,
    process_session_analytics,
)

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class AgentLoginRequest(BaseModel):
    username: str; password: str

class AgentReplyRequest(BaseModel):
    session_id: str; agent_name: str; message: str

class CloseSessionRequest(BaseModel):
    session_id: str


# ── Dashboard HTML ─────────────────────────────────────────────────────────────
# ── Enhanced Agent Dashboard HTML ─────────────────────────────────────────────
templates = Jinja2Templates(directory="templates")


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/agent/events")
@router.get("/support/events")
async def agent_events():
    """SSE stream for dashboard — pushes new session alerts"""
    return build_agent_events_response()


@router.post("/agent/login")
@router.post("/support/login")
async def agent_login(req: AgentLoginRequest):
    try:
        return process_agent_login(req.username, req.password)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/sessions")
@router.get("/support/sessions")
async def agent_sessions():
    try:
        return process_agent_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/history/{session_id}")
@router.get("/support/history/{session_id}")
async def agent_history(session_id: str):
    try:
        return process_agent_history(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/claim/{session_id}")
@router.post("/support/claim/{session_id}")
async def agent_claim(session_id: str, agent_name: str):
    try:
        return process_agent_claim(session_id, agent_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/reply")
@router.post("/support/reply")
async def agent_reply(req: AgentReplyRequest):
    try:
        return process_agent_reply(req.session_id, req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/close")
@router.post("/support/close")
async def agent_close(req: CloseSessionRequest):
    try:
        return process_agent_close(req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/all-sessions")
@router.get("/support/all-sessions")
async def agent_all_sessions():
    """Returns ALL sessions including closed ones for history view"""
    try:
        return process_agent_all_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/analytics")
@router.get("/support/analytics")
async def agent_analytics():
    """Returns aggregated analytics data and recent users from MongoDB"""
    try:
        return process_session_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/dashboard", response_class=HTMLResponse)
@router.get("/support/dashboard", response_class=HTMLResponse)
async def agent_dashboard_page(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="agent_dashboard.html",
    context={
        "request": request
    }
)
