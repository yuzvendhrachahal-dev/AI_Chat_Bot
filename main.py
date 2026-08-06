from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from app.services.chat_service import process_chat
from app.routes.chat import router as chat_router
from app.routes.agent import router as agent_router
from app.routes.admin import router as admin_router
import os, asyncio, httpx, re, secrets, unicodedata
from contextlib import asynccontextmanager
from datetime import datetime
from topic_map import TOPIC_MAP, match_topic
from fastapi.responses import StreamingResponse, Response
import json as json_lib
from app.config.settings import GROQ_API_KEY, SITE, HANDOFF_KEYWORDS, ASTROVED_API_BASE
from app.database.database import (
    init_db, seed_default_agents, get_history, save_message,
    get_and_update_session_status,
    get_waiting_or_active_sessions,
)
from app.services.kb_service import KB_CHUNKS
from app.services.handoff_service import create_or_update_handoff









# FIX (accuracy): removed the "HANDOFF: say exact phrase" instruction from the
# system prompt. The model was independently deciding to say the handoff
# sentence for things like "connect with crm" / "team", which then collided
# with the frontend's own CRM_KW trigger and produced duplicate "connect you
# with our specialist team" messages back-to-back. Handoff is now controlled
# ONLY by needs_handoff() in code (single source of truth, both code paths
# now use the same narrow keyword list).


async def keep_alive():
    await asyncio.sleep(10)
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get("https://astroved-chatbot.onrender.com/")
                print(f"Keep-alive ping OK status={r.status_code}")
        except Exception as e:
            print(f"Keep-alive failed (ok): {e}")
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(keep_alive())
    yield

app = FastAPI(lifespan=lifespan)


app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

init_db(); seed_default_agents()

app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(admin_router)

class HandoffRequest(BaseModel):
    session_id: str; user_name: str = ""; user_email: str = ""
    user_phone: str = ""; issue_type: str = "general"; priority: str = "normal"

@app.post("/handoff")
async def handoff(req: HandoffRequest):
    try:
        create_or_update_handoff(req.session_id, req.user_name, req.user_email, req.user_phone, req.issue_type, req.priority)
        save_message(req.session_id, "system", f"Handoff requested: {req.issue_type} (priority: {req.priority})")
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/app")
async def serve_chatbot():
    return FileResponse("index.html")

@app.get("/widget.js")
async def serve_widget():
    with open("widget_content.js", "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="application/javascript")

@app.get("/")
def root():
    return {
        "status": "AstroVed.AI is online",
        "model": "llama-3.1-8b-instant",
        "api_key_loaded": bool(GROQ_API_KEY),
        "knowledge_chunks_loaded": len(KB_CHUNKS),
        "topics_loaded": len(TOPIC_MAP),
    }