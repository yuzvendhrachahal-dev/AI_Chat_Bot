import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config.rate_limit import limiter
from app.config.settings import GROQ_MODEL
from app.database.mongodb import init_db, seed_default_agents

from app.routes.chat import router as chat_router
from app.routes.agent import router as agent_router
from app.routes.admin import router as admin_router
from app.routes.widget import router as widget_router


# ─────────────────────────────────────────────────────────────────────────────
# Application lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup
    yield

    # Application shutdown
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

kwargs = {
    "title": "AstroVed Chatbot API",
    "description": "Backend services for AstroVed AI Chatbot and Agent Dashboard",
    "lifespan": lifespan,
}


# Disable public API documentation in production
if os.getenv("ENV") == "production":
    kwargs["docs_url"] = None
    kwargs["redoc_url"] = None
    kwargs["openapi_url"] = None


app = FastAPI(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        #"https://www.astrovedchat.com",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────────────────────

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.add_middleware(SlowAPIMiddleware)


# ─────────────────────────────────────────────────────────────────────────────
# Database Initialization
# ─────────────────────────────────────────────────────────────────────────────

init_db()
seed_default_agents()


# ─────────────────────────────────────────────────────────────────────────────
# Static Files
# ─────────────────────────────────────────────────────────────────────────────

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal Admin Protection
# ─────────────────────────────────────────────────────────────────────────────

async def verify_internal(request: Request):
    if request.client.host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

# Public chatbot routes
app.include_router(chat_router)

# Agent dashboard and agent APIs
app.include_router(
    agent_router,
    include_in_schema=False
)

# Internal admin routes
app.include_router(
    admin_router,
    include_in_schema=False,
    dependencies=[Depends(verify_internal)]
)

# Chatbot widget
app.include_router(widget_router)


# ─────────────────────────────────────────────────────────────────────────────
# Application Info
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "AstroVed.AI is online",
        "model": GROQ_MODEL,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Local Development
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )