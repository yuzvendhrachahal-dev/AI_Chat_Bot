# Bug Fix 07 — Rate Limiting Integration

## 1. Root Cause

The API lacked rate limiting middleware. An attacker could script thousands of requests against `/chat`, completely draining Groq API limits, causing expensive billing, and potentially locking the SQLite database (Denial of Service). The `/user/register` and session initialization endpoints were equally unprotected.

## 2. Files Modified

| File | Change |
|------|--------|
| `requirements.txt` | Added `slowapi` |
| `app/config/rate_limit.py` | Initialized central `Limiter` instance |
| `main.py` | Integrated `SlowAPIMiddleware` and `429` exception handler |
| `app/routes/chat.py` | Added `@limiter.limit` decorators to endpoints |

## 3. Code Changes

The `slowapi` library was configured to limit requests based on the client's remote IP address.

```python
# app/routes/chat.py
from app.config.rate_limit import limiter
from fastapi import Request

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    ...

@router.get("/session/start")
@limiter.limit("10/minute")
async def session_start(request: Request):
    ...

@router.post("/user/register")
@limiter.limit("5/minute")
async def register_user(request: Request, req: RegisterRequest):
    ...
```

## 4. Verification Steps

1. **Start the server.**
2. **Flood the Endpoint:** Use `curl` or a script to send 25 requests to `/chat` within one minute.
3. **Verify:** The 21st request and onward must be rejected with an `HTTP 429 Too Many Requests` status code.
4. **Different Endpoints:** Test `/user/register` (limit 5) separately and verify it throttles correctly without affecting the `/chat` quota.
