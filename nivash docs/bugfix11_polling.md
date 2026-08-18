# Bug Fix 11 — Polling & Network Request Audit Report

## 1. Audit Summary

This audit evaluated all background polling timers, ping endpoints, SSE keep-alive generators, and pre-warming fetches across the system to identify unnecessary polling and reduce duplicate HTTP requests.

---

## 2. Inventory of Polling & Ping Endpoints

| Component | Endpoint | Trigger / Frequency | Behavior / Audit Finding | Status / Optimization |
|-----------|----------|---------------------|--------------------------|----------------------|
| **Agent Dashboard** | `GET /agent/sessions` | Every 4000ms via `pollL` | Chained sequentially before fetching `/agent/all-sessions`. | ⚡ **Eliminated** (merged into single `/all-sessions` call) |
| **Agent Dashboard** | `GET /agent/all-sessions` | Every 4000ms via `pollL` | Fetches all session cards for dashboard display. | ✅ **Optimized** (single request per interval) |
| **Agent Dashboard** | `GET /agent/history/{id}` | Every 3000ms via `pollH` | Active only when an agent has a chat open. Cleared on tab switch/close/logout. | ✅ **Necessary & Properly Cleared** |
| **Agent Dashboard** | `GET /agent/events` | Permanent SSE connection | Server sends SSE `queue_update` and 15s keep-alive `ping`. | ✅ **Efficient (SSE Streaming)** |
| **Customer Widget** | `GET /poll/{session_id}` | Every 4000ms when status is `waiting`/`with_agent` | Polls for new messages. Cleared on status `closed`/`bot` or `restart()`. | ✅ **Necessary & Properly Cleared** |
| **Customer Widget** | `GET /` | 1000ms after load | Pre-warms server connection on load. | ✅ **One-time startup fetch** |

---

## 3. Key Optimizations Applied

### Optimization 1: Consolidated Chained Dashboard Session Polling
- **Before**: `loadSessions()` executed `fetch('/agent/sessions')`, and inside its `.then()` block executed a second request `fetch('/agent/all-sessions')`. This resulted in **2 sequential HTTP GET requests every 4 seconds** (30 requests/minute).
- **After**: `loadSessions()` now performs a single fetch to `GET /agent/all-sessions`. It calculates `active`, `waiting`, and `with_agent` metrics directly from the full sessions array in memory.
- **Result**: Reduced dashboard list polling traffic by **50%** (15 requests/minute instead of 30 requests/minute).

### Optimization 2: Fixed Repeated Handoff Trigger (Bug 07)
- **Before**: When a customer typed a payment/CRM keyword a second time (e.g. `payment issue`), `send()` re-triggered `showCRM()` and appended duplicate Support Cards to the UI.
- **After**: Introduced `handoffTriggered` state flag in `templates/index.html` and `static/widget_content.js`. Additionally, `chat_service.py` updated status check to `if status in ("with_agent", "waiting"):`.
- **Result**: Subsequent CRM keyword messages route through `/chat`, save as user messages for the agent, and do not trigger duplicate support cards or AI bot replies.

---

## 4. Verification

1. **Dashboard Sessions Polling**:
   - Open Agent Dashboard.
   - Inspect Network tab: exactly 1 request to `GET /agent/all-sessions` is fired every 4 seconds. No extra call to `/agent/sessions`.
2. **SSE Events & Ping**:
   - EventSource receives `ping` frame every 15 seconds to prevent browser connection timeout without spawning new HTTP requests.
3. **Repeated Handoff Check**:
   - Send `payment issue` in widget. Support card appears.
   - Send `payment issue` again. Message is saved to DB for agent; no duplicate support card appears.
