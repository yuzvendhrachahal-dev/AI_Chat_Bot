"""
Widget Router
=============
Handles routes for:
  - GET /
  - GET /app
  - GET /widget.js
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

from app.services.kb_service import KB_CHUNKS
from app.config.settings import GROQ_API_KEY
from app.config.topic_map import TOPIC_MAP

router = APIRouter()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/")
def root():
    return {
        "status": "AstroVed.AI is online",
        "model": "llama-3.1-8b-instant",
        "api_key_loaded": bool(GROQ_API_KEY),
        "knowledge_chunks_loaded": len(KB_CHUNKS),
        "topics_loaded": len(TOPIC_MAP),
    }


@router.get("/app")
async def serve_chatbot():
    return FileResponse("templates/index.html")


@router.get("/widget.js")
async def serve_widget():
    return FileResponse("static/widget_content.js", media_type="application/javascript")
