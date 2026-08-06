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

Routes are not yet moved here. This file is the infrastructure scaffold.
"""

from fastapi import APIRouter, HTTPException
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
)

router = APIRouter()
