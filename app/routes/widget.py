"""
Widget Router
=============
Handles routes for:
  - GET /
  - GET /app
  - GET /widget.js
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.kb_service import KB_CHUNKS
from app.config.settings import GROQ_API_KEY, GROQ_MODEL
from app.config.topic_map import TOPIC_MAP

router = APIRouter()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/")
def root():
    return {
        "service": "AstroVed AI Chatbot",
        "status": "running"
    }

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "model": GROQ_MODEL,
        "version": "1.0.0"
    }


@router.get("/app", include_in_schema=False)
async def serve_chatbot():
    return FileResponse("templates/index.html")


@router.get("/widget.js")
async def serve_widget():
    return FileResponse("static/widget_content.js", media_type="application/javascript")

