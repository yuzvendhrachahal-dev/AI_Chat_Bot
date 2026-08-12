# Bug Fix 05 — Server-Sent Events (SSE) Audit & Cleanup Report

## 1. Audit Objective

Audit the Server-Sent Events (SSE) implementation in the Agent Dashboard (`/agent/events`) focusing on:
- `connectSSE()` execution flow
- `EventSource` instance lifecycle & cleanup
- Reconnect handling (preventing duplicate reconnect loops)
- Keep-alive `ping` frame handling
- Memory leak and duplicate event listener prevention

---

## 2. Audit Findings

### 2.1 `EventSource` Instantiation & Reconnect Logic
- **Location**: [`app/routes/agent.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/agent.py) (`connectSSE()`)
- **Inspection**:
  ```javascript
  function connectSSE(){
    if(sseConn) sseConn.close();
    sseConn = new EventSource(API + '/agent/events');
    ...
    sseConn.onerror = function(){
      console.warn('SSE connection interrupted — browser reconnecting natively...');
    };
  }
  ```
- **Finding**:
  1. **No manual reconnect loops**: Previously, custom `onerror` handlers used `setTimeout(connectSSE, 3000)` which spawned duplicate `EventSource` instances whenever temporary network glitches occurred. The manual retry loop has been completely removed.
  2. **Native Reconnection**: Browser-native `EventSource` reconnection handles transient network interruptions automatically without triggering multiple client instances.

---

### 2.2 Instance Cleanup & Memory Leak Prevention
- **Singleton Guard**: Before initializing a new `EventSource`, `connectSSE()` checks `if (sseConn) sseConn.close()`. This guarantees that calling `connectSSE()` multiple times (e.g. during page/state transitions) will close the active connection first.
- **Session Logout**: In `doLogout()`, `if (sseConn) sseConn.close()` explicitly closes the connection and releases browser resources.
- **Listener Overwrites**: Event handlers are assigned via direct property assignment (`sseConn.onmessage = ...`) rather than `addEventListener`. Re-running `connectSSE()` replaces the handler function reference without accumulating duplicate listener callbacks.

---

### 2.3 Ping Frame Handling
- **Backend Generator** ([`app/services/agent_service.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/services/agent_service.py)):
  ```python
  if count != last_count:
      yield f"data: {data}\n\n"
  else:
      yield 'data: {"type":"ping"}\n\n'
  ```
- **Client Handler** ([`app/routes/agent.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/agent.py)):
  ```javascript
  sseConn.onmessage = function(e){
    try {
      const d = JSON.parse(e.data);
      if (d.type === 'queue_update') {
        // Update badge and trigger notifications
      }
    } catch(err) {};
  };
  ```
- **Finding**: Ping frames (`{"type":"ping"}`) keep the HTTP streaming connection alive every 3 seconds to prevent timeout, and are safely ignored by the frontend `if (d.type === 'queue_update')` filter. No UI side-effects or errors occur.

---

## 3. Summary Table

| Category | Finding | Status |
|----------|---------|--------|
| **Manual Reconnect Loops** | Manual `setTimeout` retry loop removed | ✅ Clean (uses browser native retry) |
| **Instance Cleanup** | `if(sseConn) sseConn.close()` on re-init & logout | ✅ Clean |
| **Listener Accumulation** | Direct `.onmessage` assignment prevents duplicate callbacks | ✅ Clean |
| **Keep-Alive Ping** | `{"type":"ping"}` frames handled silently | ✅ Clean |
| **Backend Stream** | `StreamingResponse` properly formatted with `text/event-stream` headers | ✅ Clean |
