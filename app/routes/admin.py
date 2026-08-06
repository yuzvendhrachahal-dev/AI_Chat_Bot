"""
Admin Router
============
Handles routes for:
  - GET /admin/users
  - GET /admin/registrations
  - GET /debug/env

Routes are not yet moved here. This file is the infrastructure scaffold.
"""

from fastapi import APIRouter, HTTPException

from app.database.database import (
    get_admin_users,
    get_all_registrations,
)
from app.config.settings import (
    GROQ_API_KEY,
    SITE,
    ASTROVED_API_BASE,
)

router = APIRouter()
