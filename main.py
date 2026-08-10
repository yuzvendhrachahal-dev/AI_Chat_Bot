from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.chat import router as chat_router
from app.routes.agent import router as agent_router
from app.routes.admin import router as admin_router
from app.routes.widget import router as widget_router

import asyncio
import httpx
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config.rate_limit import limiter
from app.config.settings import APP_URL
from app.database.database import init_db, seed_default_agents

async def keep_alive():
    """Background task to keep the Render deployment awake."""
    await asyncio.sleep(10)
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(APP_URL)
                print(f"Keep-alive ping OK status={r.status_code}")
        except Exception as e:
            print(f"Keep-alive failed (ok): {e}")
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the keep-alive task on startup
    asyncio.create_task(keep_alive())
    yield

# Initialize FastAPI Application
app = FastAPI(
    title="AstroVed Chatbot API",
    description="Backend services for AstroVed AI Chatbot and Agent Dashboard",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Configure Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Initialize Database and Seed Default Agents
init_db()
seed_default_agents()

# Mount Static Files Directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register All Route Modules
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(admin_router)
app.include_router(widget_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
