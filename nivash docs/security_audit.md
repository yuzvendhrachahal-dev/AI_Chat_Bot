# Security Audit Report

**Date:** 2026-08-07  
**Scope:** Production Deployment Architecture, APIs, Database, and Frontend Clients.

---

## 1. Executive Summary
The application has strong defenses against SQL Injection (parameterized queries) and file exposure. However, critical vulnerabilities exist in cross-site scripting (XSS), session generation (predictable IDs leading to hijacking), permissive CORS, and a lack of rate limiting.

---

## 2. Vulnerability Assessment

### 2.1 Cross-Site Scripting (XSS) & HTML Injection — 🔴 HIGH
- **Finding:** The customer-facing widget (`static/widget_content.js`) renders messages via `cleanMd()` using `.innerHTML` without escaping HTML entities. A user sending `<script>alert(1)</script>` or `<img src=x onerror=...>` will have the payload executed in the browser. 
- **Agent Dashboard:** `agent.py` uses `.replace(/</g, '&lt;')` for message rendering, which prevents basic script tags but is not a comprehensive XSS sanitizer.

### 2.2 Session Hijacking — 🔴 HIGH
- **Finding:** `session_id` is generated on the client side using `Math.random().toString(36).slice(2)`. This uses a weak, predictable pseudo-random number generator.
- **Impact:** An attacker can guess active `session_id` values and call `GET /poll/{session_id}` to steal chat history (which may contain phone numbers and emails) or hijack the session by sending messages via `POST /chat`.

### 2.3 Cross-Origin Resource Sharing (CORS) — 🔴 HIGH
- **Finding:** `main.py` configures `CORSMiddleware` with `allow_origins=["*"]`.
- **Impact:** Any domain can send requests to the API. This enables Cross-Site Request Forgery (CSRF)-like attacks where malicious sites can abuse the chatbot API from a user's browser.

### 2.4 API Abuse & Rate Limiting — 🔴 HIGH
- **Finding:** There is zero rate limiting on the application.
- **Impact:** An attacker can script thousands of requests to `POST /chat`, completely draining the Groq API limits, causing expensive billing, and potentially locking the SQLite database (Denial of Service).

### 2.5 Secrets & Authentication — 🟠 MEDIUM
- **Finding 1:** Default agent passwords (`"astroved123"`) are hardcoded in plaintext inside `app/database/database.py` during seeding.
- **Finding 2:** Passwords are hashed using basic `SHA-256`, which is fast and vulnerable to brute-force/rainbow table attacks. A key derivation function like `bcrypt` or `argon2` is required.

### 2.6 Prompt Injection — 🟡 LOW
- **Finding:** The LLM receives user input directly in the `user` role message. While the API strictly formats it via the Groq SDK, a malicious user could still attempt to jailbreak the bot using commands like "Ignore all previous instructions...". 
- **Mitigation:** The pre-LLM domain guard (`match_topic` / `search_knowledge`) heavily limits what queries even reach the LLM, but injection is still theoretically possible for queries containing AstroVed keywords.

### 2.7 SQL Injection (SQLi) — ✅ SAFE
- **Finding:** Inspected `app/database/database.py`. All dynamic queries exclusively use SQLite parameterized queries (`?`). No string formatting or concatenation is used in queries.

### 2.8 File Exposure — ✅ SAFE
- **Finding:** Only the `/static` directory is mounted for static file serving. Sensitive files in the root like `chat.db` and `.env` are secure and cannot be accessed via HTTP GET requests. Environment variables are loaded securely via `python-dotenv`.

---

## 3. Recommended Remediation Plan

1. **Fix XSS:** Update `cleanMd()` in the frontend to properly escape `<` and `>` before parsing markdown.
2. **Secure Sessions:** Generate `session_id` securely on the backend using `uuid.uuid4()` instead of relying on the client's `Math.random()`.
3. **Restrict CORS:** Change `allow_origins=["*"]` to `["https://www.astroved.com"]` in `main.py`.
4. **Implement Rate Limiting:** Add `slowapi` to limit `/chat` to a reasonable quota (e.g., 20 requests/minute per IP).
5. **Secure Passwords:** Move default agent credentials to `.env` variables and upgrade hashing to `passlib` (bcrypt).
