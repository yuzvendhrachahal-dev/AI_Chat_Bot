# PRODUCTION AUDIT — AstroVed.AI Chatbot

**Audit Date**: 2026-08-07  
**Audited By**: Automated Production Readiness Inspection  
**Target Platform**: Render.com (Free / Hobby tier)

---

## 1. Files Inspected

| File | Purpose |
|------|---------|
| [main.py](file:///Users/nivash/AV/AI_Chat_Bot/main.py) | FastAPI app entry point, lifespan, CORS, router registration |
| [app/database/database.py](file:///Users/nivash/AV/AI_Chat_Bot/app/database/database.py) | SQLite connection lifecycle, all DB functions |
| [app/services/chat_service.py](file:///Users/nivash/AV/AI_Chat_Bot/app/services/chat_service.py) | AI response pipeline |
| [app/services/agent_service.py](file:///Users/nivash/AV/AI_Chat_Bot/app/services/agent_service.py) | SSE stream, agent actions |
| [app/routes/chat.py](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/chat.py) | Chat, poll, register, handoff routes |
| [app/routes/agent.py](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/agent.py) | Agent dashboard HTML and backend routes |
| [app/config/settings.py](file:///Users/nivash/AV/AI_Chat_Bot/app/config/settings.py) | Secrets loading and CRM keyword list |
| [requirements.txt](file:///Users/nivash/AV/AI_Chat_Bot/requirements.txt) | Python dependency manifest |
| [.gitignore](file:///Users/nivash/AV/AI_Chat_Bot/.gitignore) | Repository secret exclusions |

---

## 2. Audit Findings

### 2.1 Memory Leaks

| Area | Finding | Severity |
|------|---------|---------|
| SSE `event_stream()` | The `while True` generator in `agent_service.py` runs indefinitely. It has no `try/finally` or `GeneratorExit` handling. If a client disconnects mid-stream, the generator keeps running until the next `asyncio.sleep()` yields, then should be garbage collected naturally by FastAPI's `StreamingResponse`. **In practice this is acceptable** — FastAPI handles generator cleanup on disconnect. | 🟡 LOW |
| `KB_CHUNKS` list | The full `knowledge_base.txt` (1.4 MB) is loaded into memory at startup as `KB_CHUNKS` and is never evicted. For a single-instance Render deployment this is fine, but adds ~10–15 MB base RAM. | 🟡 LOW (Acceptable) |
| Agent dashboard `pollL` | `pollL = setInterval(loadSessions, 4000)` runs as long as the browser tab is open. It is cleared on `doLogout()`. **No leak** if the agent closes the session correctly. If the tab is closed without logging out, the browser cleans up automatically. | ✅ No Leak |

---

### 2.2 Resource Cleanup (Database Connections)

| Finding | Severity | Detail |
|---------|---------|--------|
| **No context manager (`with`) pattern used** | 🔴 HIGH | Every function in `database.py` calls `conn = get_db_connection()` and later `conn.close()`. If an exception occurs between `conn = ...` and `conn.close()`, the connection is **never closed**. This can cause SQLite `"database is locked"` errors under concurrent load. Affects: `create_or_update_handoff`, `create_or_update_session`, `get_admin_users`, `get_all_sessions`, `get_waiting_or_active_sessions`, `save_user_registration` (16 of 19 functions). Only `get_history` and `save_message` have `try/except` but no `finally` with `conn.close()`. |
| `get_history` uses `try/except` but closes inside `try` block | 🟠 MEDIUM | `conn.close()` on line 43 sits inside the `try` block. If `conn.execute(...)` or `.fetchall()` raises, `except` silently returns `[]` but `conn.close()` was never reached. |
| `save_message` closes inside `try` block | 🟠 MEDIUM | Same pattern as above. `conn.close()` on line 59 is inside `try`. A DB exception leaks the connection. |

**Recommended Fix (applies globally to `database.py`)**:
```python
# Pattern to adopt for every DB function:
def get_history(session_id: str):
    conn = get_db_connection()
    try:
        rows = conn.execute(...)
        ...
        return result
    except Exception as e:
        print(f"get_history error: {e}")
        return []
    finally:
        conn.close()  # guaranteed to run whether or not an exception occurs
```

---

### 2.3 SQLite Locking

| Finding | Severity | Detail |
|---------|---------|--------|
| **No WAL mode enabled** | 🟠 MEDIUM | SQLite's default journal mode (`DELETE`) allows only one writer at a time and blocks concurrent readers during writes. In production with multiple concurrent `/poll` calls, `/chat` calls, and SSE reads, this can produce `"database is locked"` errors. Enabling WAL mode allows concurrent reads while a write is in progress. |
| **No `check_same_thread=False`** | 🟡 LOW | `sqlite3.connect()` is called without `check_same_thread=False`. Since FastAPI uses an async event loop with multiple threads under uvicorn, SQLite may raise a threading safety error if not configured. |
| **No `timeout` parameter** | 🟡 LOW | `sqlite3.connect(DATABASE_PATH)` has no `timeout`. The default is 5 seconds. Under write contention, callers will get `OperationalError: database is locked` after 5s instead of a configurable retry period. |

**Recommended Fix**:
```python
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn
```

---

### 2.4 Render Deployment

| Finding | Severity | Detail |
|---------|---------|--------|
| **Keep-alive pings itself every 10 min** | ✅ Correct | `keep_alive()` in `main.py` sends a GET to `https://astroved-chatbot.onrender.com/` every 600 seconds. This is the standard pattern to prevent Render free-tier spin-down. |
| **`chat.db` lives on ephemeral filesystem** | 🔴 HIGH | Render free and hobby instances use an ephemeral disk. Any restart or redeploy **wipes the SQLite database and all conversation history**. For production persistence, use Render's persistent disk add-on (paid) or migrate to PostgreSQL. |
| **`knowledge_base.txt` on ephemeral disk** | 🟠 MEDIUM | Same issue. If the file is not in the git repo, it will disappear on redeploy. The file is 1.4 MB and is **not** in `.gitignore`, so it will be committed to the repo and survive redeployment. |
| **`reload=True` in `__main__` block** | 🟡 LOW | `uvicorn.run("main:app", ..., reload=True)` enables hot reload. This is fine for local dev but should be `reload=False` for production (Render starts via `uvicorn main:app` directly, so this block is not executed in production anyway). |

---

### 2.5 Error Handling

| Area | Finding | Severity |
|------|---------|---------|
| `/chat` route | Raises `HTTPException(500)` on any unhandled error. The `except` block logs the error with `print()`. ✅ Acceptable. | ✅ |
| `/poll` route | Raises `HTTPException(500)` on exceptions. ✅ | ✅ |
| `/user/register` | Catches `TimeoutException`, `ConnectError`, and generic `Exception` separately. Falls back gracefully in all cases. ✅ | ✅ |
| `database.py` functions without `except` | `create_or_update_handoff`, `create_or_update_session`, `claim_session`, `touch_session`, `close_session`, `get_all_sessions`, `get_active_agent_sessions`, `get_session_messages`, `get_session_poll_data` — all have **no error handling at all**. An uncaught DB exception propagates to the route layer and surfaces as a 500. | 🟠 MEDIUM |
| SSE `event_stream` | Has `except Exception as e` that yields an error frame. Does not crash the stream. ✅ | ✅ |
| `save_user_registration` | Uses DDL (`CREATE TABLE IF NOT EXISTS`) inside the function. Running this on every registration call is inefficient and risks locking contention. It should be in `init_db()`. | 🟡 LOW |

---

### 2.6 Logging

| Finding | Severity | Detail |
|---------|---------|--------|
| **All logging via `print()`** | 🟠 MEDIUM | The codebase uses `print()` exclusively for all log output. Render captures `stdout` as logs, so this works functionally. However, `print()` provides no log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`), no structured formatting, no timestamps, and no way to filter or silence debug noise in production. |
| **`[DB SAVE]` diagnostic log still active** | 🟡 LOW | `save_message()` prints `[DB SAVE] {session_id} {role} {content[:40]}` on every message. This was added for BUG FIX 01 debugging and should be removed or gated before production. |
| **`[DIAG]` diagnostic log in `chat_service.py`** | 🟡 LOW | The BUG FIX 01 diagnostic block (lines 18–28 in `chat_service.py`) logs full session IDs and message content to stdout on every `/chat` request. Should be removed or replaced with a proper structured logger before production. |
| **`[POLL]` diagnostic log in `chat.py`** | 🟡 LOW | `print(f"[POLL] session=...")` on every `/poll` request. At 4-second polling intervals per active session, this is very noisy in production. |

---

### 2.7 Security

| Finding | Severity | Detail |
|---------|---------|--------|
| **`allow_origins=["*"]` CORS policy** | 🔴 HIGH | `main.py` configures `CORSMiddleware` with `allow_origins=["*"]`. This permits any domain to call the API. For a production chatbot widget embedded on `astroved.com`, CORS should be restricted to the list of permitted origins (e.g. `["https://www.astroved.com", "https://astroved.com"]`). |
| **Hardcoded default agent passwords** | 🔴 HIGH | `database.py` seeds agents with password `"astroved123"` in plain text. While the password is stored as a SHA-256 hash, the plaintext default is embedded in source code and committed to git. An attacker reading the repo can log in to the agent dashboard. Passwords should be moved to environment variables. |
| **SHA-256 for password hashing** | 🟠 MEDIUM | SHA-256 is a fast hash function, not a key derivation function. It is vulnerable to brute-force and rainbow table attacks. Production password hashing should use `bcrypt`, `argon2`, or `PBKDF2` (all available via `passlib`). |
| **No rate limiting on `/chat` or `/agent/login`** | 🟠 MEDIUM | There are no rate limits on the chat endpoint or the agent login endpoint. An attacker can brute-force credentials or flood the Groq API at no extra rate-limit resistance. Consider adding `slowapi` or Cloudflare-level rate limiting. |
| **Agent dashboard publicly accessible** | 🟠 MEDIUM | `GET /agent/dashboard` returns the full agent console HTML to any requester. There is no session token, HTTP header authentication, or IP allowlist protecting the dashboard route itself. An attacker who finds the URL can view the login page. |
| **No input length validation on `/chat`** | 🟡 LOW | `ChatRequest.message` has no `max_length` constraint. A user can send arbitrarily long messages, causing expensive LLM calls and potential KB search performance degradation. |
| **API keys in `.env` file** | ✅ Correct | `.env` is in `.gitignore`. Keys are loaded via `python-dotenv`. The GROQ key is not hardcoded in source. |
| **JWT token in `.env`** | ✅ Correct | `ASTROVED_JWT_TOKEN` is loaded from environment. Not hardcoded. |

---

## 3. Summary Table

| Category | Critical 🔴 | Medium 🟠 | Low 🟡 | Clean ✅ |
|----------|------------|----------|-------|---------|
| Memory Leaks | 0 | 0 | 2 | 1 |
| Resource Cleanup | 0 | 2 | 1 | 0 |
| SQLite Locking | 0 | 2 | 2 | 0 |
| Render Deployment | 1 | 1 | 1 | 2 |
| Error Handling | 0 | 1 | 1 | 4 |
| Logging | 0 | 1 | 3 | 0 |
| Security | 2 | 3 | 1 | 2 |

---

## 4. Priority Fixes (Recommended Order)

### 🔴 Critical — Must fix before production traffic

1. **Migrate SQLite to a persistent disk or PostgreSQL** — Render ephemeral disk will lose all chat history on every redeploy.
2. **Restrict CORS origins** — Change `allow_origins=["*"]` to `["https://www.astroved.com", "https://astroved.com"]`.
3. **Move agent default passwords to environment variables** — Remove hardcoded `"astroved123"` from `database.py`.

### 🟠 Medium — Fix before significant user load

4. **Enable WAL mode and `check_same_thread=False`** in `get_db_connection()`.
5. **Wrap all DB functions with `try/finally` + `conn.close()`** — prevents connection leaks under errors.
6. **Upgrade password hashing to `bcrypt` or `argon2`** via `passlib`.
7. **Add rate limiting** to `/chat` and `/agent/login` endpoints.
8. **Replace `print()` with Python `logging` module** for structured log levels.

### 🟡 Low — Clean up for maintainability

9. **Remove BUG FIX 01 diagnostic prints** (`[DB SAVE]`, `[DIAG]`, `[POLL]`, `[AGENT SEND]`, `[SSE]`) before production.
10. **Add `max_length` validator to `ChatRequest.message`** (e.g. 1000 chars).
11. **Move `CREATE TABLE IF NOT EXISTS` in `save_user_registration`** to `init_db()`.
