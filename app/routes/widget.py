"""
Widget Router
=============
Handles routes for:
  - GET /
  - GET /app
  - GET /widget.js

Routes are not yet moved here. This file is the infrastructure scaffold.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter()
