"""
Admin Router
============
Handles routes for:
  - GET /admin/users
  - GET /admin/registrations
  - GET /debug/env
"""

from fastapi import APIRouter

from app.database.mongodb import (
    get_admin_users,
    get_all_registrations,
)
from app.config.settings import (
    GROQ_API_KEY,
    ASTROVED_JWT_TOKEN,
)

router = APIRouter()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/admin/users")
async def admin_users():
    rows = get_admin_users()
    return {"users": [{"session_id":r[0],"user_name":r[1],"user_email":r[2],"user_phone":r[3],"status":r[4],"issue_type":r[5],"created_at":r[6],"updated_at":r[7]} for r in rows]}


@router.get("/debug/env")
async def debug_env():
    return {
        "groq_loaded": bool(GROQ_API_KEY),
        "jwt_loaded": bool(ASTROVED_JWT_TOKEN),
        "jwt_preview": ASTROVED_JWT_TOKEN[:15] + "..." if ASTROVED_JWT_TOKEN else "NOT SET - using local DB only"
    }


@router.get("/admin/registrations")
async def get_registrations():
    rows = get_all_registrations()
    return {"registrations": [{"session_id":r[0],"user_name":r[1],"user_email":r[2],"user_phone":r[3],"country_code":r[4],"synced_to_api":r[5],"created_at":r[6]} for r in rows]}
