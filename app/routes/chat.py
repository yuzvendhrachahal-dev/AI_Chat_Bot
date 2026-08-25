"""
Chat Router
===========
Handles routes for:
  - POST /chat
  - GET  /poll/{session_id}
  - POST /session/start
  - POST /user/register
"""

import httpx
import uuid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.config.rate_limit import limiter

from app.config.settings import ASTROVED_API_BASE, ASTROVED_JWT_TOKEN
from app.services.chat_service import process_chat
from app.services.agent_service import process_poll_session
from app.database.mongodb import (
    create_or_update_session,
    save_user_registration,
    save_message,
    create_or_update_handoff,
    get_session_restore_data
)

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str; message: str; user_name: str = ""; user_email: str = ""; user_phone: str = ""

class RegisterRequest(BaseModel):
    session_id: str
    user_name: str = ""
    user_email: str = ""
    user_phone: str = ""
    country_code: str = "+91"

class HandoffRequest(BaseModel):
    session_id: str; user_name: str = ""; user_email: str = ""
    user_phone: str = ""; issue_type: str = "general"; priority: str = "normal"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/chat", include_in_schema=False)
@router.post("/api/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    return await process_chat(req)


@router.get("/poll/{session_id}", include_in_schema=False)
@router.get("/api/poll/{session_id}")
async def poll_session(session_id: str, since_id: int = 0):
    try:
        res = process_poll_session(session_id, since_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/restore/{session_id}", include_in_schema=False)
@router.get("/api/session/restore/{session_id}")
async def restore_session(session_id: str):
    try:
        data = get_session_restore_data(session_id)
        if not data:
            return {"status": "ended"}
        return {"status": "active", "session": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/start", include_in_schema=False)
@router.post("/api/session")
@limiter.limit("10/minute")
async def session_start(request: Request):
    try:
        return {"session_id": f"sess_{uuid.uuid4().hex}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/register", include_in_schema=False)
@router.post("/api/register")
@limiter.limit("5/minute")
async def register_user(request: Request, req: RegisterRequest):
    print(f"Register attempt: {req.user_name} | {req.user_email} | {req.user_phone}")

    # If no JWT token configured, still save to local DB and proceed
    if not ASTROVED_JWT_TOKEN:
        print("WARNING: ASTROVED_JWT_TOKEN not set — saving to local DB only")
        save_user_registration(req.session_id, req.user_name, req.user_email, req.user_phone, req.country_code, 0)
        return {"StatusCode": 200, "Status": "OK", "Message": "Saved locally"}

    synced = 0
    api_response = {"StatusCode": 200, "Status": "OK", "Message": "Saved with fallback"}
    
    # IMMEDIATELY create the session in MongoDB so it exists if the user refreshes
    # during the slow AstroVed API call.
    create_or_update_session(req.session_id, req.user_name, req.user_email, req.user_phone)
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{ASTROVED_API_BASE}/UserAccount/AddChatBotDetails",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ASTROVED_JWT_TOKEN}"
                },
                json={
                    "CustomerName": req.user_name,
                    "CurrencyCode": "INR",
                    "CountryCode": req.country_code,
                    "MobileNo": req.user_phone,
                    "EmailAddress": req.user_email
                }
            )
            print(f"AstroVed API: {response.status_code} | {response.text}")
            synced = 1
            # If the response is valid JSON, parse it.
            # If the Astroved API returns non-JSON, we might get an error here, which goes to except block.
            api_response = response.json()

    except httpx.TimeoutException:
        print("AstroVed API timeout")
        api_response["Message"] = "Saved with timeout fallback"
    except httpx.ConnectError as ce:
        print(f"AstroVed API connection error: {ce}")
        api_response["Message"] = "Saved with connection fallback"
    except Exception as e:
        print(f"register_user unexpected error: {str(e)}")
        api_response["Message"] = "Saved with error fallback"
    finally:
        # 2, 3, 4, 8: Always save to MongoDB regardless of AstroVed API result.
        save_user_registration(req.session_id, req.user_name, req.user_email, req.user_phone, req.country_code, synced)
        create_or_update_session(req.session_id, req.user_name, req.user_email, req.user_phone)

    return api_response


@router.post("/handoff", include_in_schema=False)
@router.post("/api/handoff")
async def handoff(req: HandoffRequest):
    try:
        create_or_update_handoff(req.session_id, req.user_name, req.user_email, req.user_phone, req.issue_type, req.priority)
        save_message(req.session_id, "system", f"Handoff requested: {req.issue_type} (priority: {req.priority})")
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
