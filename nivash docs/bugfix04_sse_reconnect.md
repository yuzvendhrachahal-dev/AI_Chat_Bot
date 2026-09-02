# Bug Fix 04 — Fix Redundant EventSource Reconnection

## 1. Root Cause
In `app/routes/agent.py`, the EventSource queue update listener `connectSSE()` registered an error handler:
```javascript
sseConn.onerror = function() { setTimeout(connectSSE, 5000); };
```
- Browsers have a **native auto-reconnection mechanism** for `EventSource` connections that automatically tries to reconnect in the background when the connection is dropped.
- Because of this, when a disconnect occurred, the browser natively triggered `onerror` and also scheduled its own reconnect attempt.
- Concurrently, our `onerror` callback scheduled `setTimeout(connectSSE, 5000)`.
- Re-invoking `connectSSE()` instantiated a brand-new `EventSource` object, resulting in redundant reconnection attempts.
- During multiple connection drops (e.g. if the server took time to respond), these timeouts stacked up, leading to multiple active or rapidly cycling EventSource attempts and duplicate callback registrations on different instances.

## 2. Files Changed
- [`app/routes/agent.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/agent.py) (Modified `connectSSE()`'s `onerror` callback).

## 3. Code Changes

```diff
- sseConn.onerror=function(){setTimeout(connectSSE,5000);};
+ sseConn.onerror=function(){console.warn('SSE connection interrupted — browser reconnecting natively...');};
```

This delegates all reconnection concerns to the browser's native `EventSource` engine, guaranteeing that exactly one `EventSource` object is created and maintained.

## 4. Verification
1. Open the Agent Dashboard.
2. The initial connection to `/agent/events` is established.
3. Simulate a network disconnect (e.g., stop the uvicorn server or block network requests).
4. Browser console prints the warning: `SSE connection interrupted — browser reconnecting natively...`.
5. Restart the server.
6. The browser auto-reconnects natively.
7. Inspect the **Network Tab** (DevTools):
   - Only **one** active GET `/agent/events` connection is visible.
   - Reconnections reuse the existing callbacks instead of instantiating new `EventSource` objects or duplicating callbacks.
