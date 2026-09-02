# Bug Fix 04 — Agent Dashboard Flicker/Blink

## 1. Root Cause

The dashboard blinked continuously because **two polling loops unconditionally rebuilt the DOM on every tick** — even when nothing had changed.

### Cause A — `renderCards()` (session list, every 4 s)

```
enterApp()
  └── pollL = setInterval(loadSessions, 4000)
        └── loadSessions() → fetch('/agent/all-sessions')
              └── renderCards()
                    └── sl.innerHTML = ''   ← ⚠️ DOM wiped unconditionally
                          └── list.forEach → appendChild   ← ⚠️ Rebuilt from scratch
```

Every 4 seconds `sl.innerHTML = ''` destroyed every session card in the sidebar and immediately rebuilt them. The browser repaint on destruction → recreation causes a visible flicker on each cycle regardless of whether any session data changed.

### Cause B — `loadHistory()` (chat body, every 3 s)

```
openSess()
  └── pollH = setInterval(loadHistory, 3000)
        └── loadHistory() → fetch('/agent/history/{sid}')
              └── body.innerHTML = ...  ← ⚠️ Chat body wiped and rebuilt unconditionally
```

Every 3 seconds the active conversation chat log was destroyed and rebuilt entirely, causing the chat window to flash on every poll even when no new messages had arrived.

### Cause C — NOT the EventSource / SSE

The SSE stream was audited and found clean. `connectSSE()` does **not** trigger any DOM mutation. Ping frames (`{"type":"ping"}`) are silently ignored. There is no duplicate `EventSource` instance. The flicker was entirely caused by the unconditional `innerHTML` replacements in the two polling paths above.

---

## 2. Files Modified

| File | Change |
|------|--------|
| [`app/routes/agent.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/routes/agent.py) | Added snapshot diffing guard to `renderCards()` and `loadHistory()` |

---

## 3. Code Changes

### 3.1 State additions (line ~520)

```diff
+ let _lastCardsKey='',_lastHistoryKey='';
```

Two module-level cache variables track the last-rendered state.

---

### 3.2 `renderCards()` — snapshot key guard

```diff
  const sl=document.getElementById('sl');
+ if(!list.length){sl.innerHTML='...';_lastCardsKey='__empty__';return;}
+
+ // BLINK FIX: build a snapshot key; only repaint if sessions changed or active selection changed
+ const key=list.map(s=>
+   s.session_id+'|'+s.status+'|'+(s.assigned_agent||'')+'|'+(s.updated_at||'')
+   +(s.session_id===activeSid?'*':'')
+ ).join(',');
+ if(key===_lastCardsKey)return;   // ← nothing changed, skip the repaint
+ _lastCardsKey=key;
  sl.innerHTML='';
  list.forEach(s=>{ ... });
```

The key encodes: session IDs, statuses, assigned agents, timestamps, and the active-selection flag. If the key hasn't changed since the last render, `renderCards()` returns immediately without touching the DOM.

---

### 3.3 `loadHistory()` — message count+ID guard

```diff
  const body=document.getElementById('cb');if(!body)return;
+
+ // BLINK FIX: only repaint if message count or last message id changed
+ const histKey=(d.messages&&d.messages.length
+   ? d.messages.length+'|'+d.messages[d.messages.length-1].id
+   : '0');
+ if(histKey===_lastHistoryKey){return;}  // ← nothing new, skip the repaint
+ _lastHistoryKey=histKey;
+
  const atBot=body.scrollTop+body.clientHeight>=body.scrollHeight-40;
  body.innerHTML=d.messages.map(...).join('');
```

The key encodes message count + last message DB id. This is guaranteed stable for unchanged conversations and changes immediately when a new message arrives.

---

## 4. Verification Steps

1. **Open the agent dashboard and log in.**
2. **Watch the session sidebar** — it must remain visually stable (no card flash) for at least 30 seconds with no new chats.
3. **Open a user chat in the chat panel** — the conversation body must remain visually stable even while poll timer runs.
4. **Send a new message via the widget** — the chat body must update within ≤3 s and render the new message correctly.
5. **Claim a waiting session or change session status** — the session card in the sidebar must update to reflect the new status on the next poll.
6. **Tab-switch and search filter** — cards must re-render correctly (the key guard is bypassed by direct `renderCards()` calls from `setTab()` and `filterCards()` which do not use the cache).

> **Note on tab-switch / search:** `setTab()` and `filterCards()` call `renderCards()` directly. Because `curTab` or the search query changed, the computed `key` will differ from `_lastCardsKey` and the repaint will execute correctly.
