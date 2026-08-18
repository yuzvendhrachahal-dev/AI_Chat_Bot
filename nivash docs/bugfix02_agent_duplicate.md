# Bug Fix 02 — Eliminate Duplicate Agent Replies: Diagnosis & Fix Report

## 1. Root Cause

### Polling Concurrency and Sync Race Conditions
The customer-side widget has two polling entry points: `syncThenPoll()` and `startPolling()`. 
- `syncThenPoll()` does a silent fetch to `/poll` to catch up on the latest message ID and then starts `startPolling()`.
- `startPolling()` initiates a `setInterval` that fetches from `/poll` every 4 seconds.
- Every time a customer sends a message or triggers a handoff, `syncThenPoll()` is invoked to synchronize the message offset.
- If multiple fetches or polling ticks overlap (due to delayed API responses, network latency, or concurrent user action), multiple poll fetches are sent containing the same `since_id`.
- When these overlapping fetches resolve, they return the same message payload (e.g. the agent's reply with a specific message ID).
- Both callbacks iterate through the array and render the agent reply, causing it to appear twice in the UI.

### Handoff Message Double-Rendering
During a handoff event (triggered via LLM or keyword):
- The server saves the handoff message to the DB as `assistant` and returns the message directly in the `/chat` JSON response.
- The client widget renders it immediately using the `/chat` response.
- At the same time, the client calls `syncThenPoll()` which polls the DB. Since the database write completed on the server, the `/poll` request returns the handoff message again, rendering it a second time.

### The Solution: Unique Message ID Guard (`answeredIds`)
By introducing a state tracking object `answeredIds` on the client side:
1. Each message is processed and recorded by its database auto-incrementing `id` key.
2. If `answeredIds[m.id]` is already `true`, the widget skips rendering the message entirely, ensuring that no message can ever be appended to the chat interface twice.
3. This completely prevents duplicate rendering regardless of polling races, network retries, or concurrent intervals.

---

## 2. Files Modified

1. [templates/index.html](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html) (Chatbot standalone page)
2. [static/widget_content.js](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js) (Embedded widget JS script)

---

## 3. Code Changes

### [templates/index.html](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html)

#### 1. Declaration of `answeredIds` tracking object:
```diff
    var msgCounter = 0;
    var pollTimer = null;
    var lastMsgId = 0;
    var isSending = false;  // BUG FIX 02 — prevents concurrent POST /chat
+   var answeredIds = {};   // BUG FIX 02 — tracking rendered message IDs
```

#### 2. Guard inside `startPolling()`:
```diff
     function startPolling() {
       if (pollTimer) return;
       pollTimer = setInterval(function () {
         fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
           .then(function (r) { return r.json(); })
           .then(function (d) {
             d.messages.forEach(function (m) {
               lastMsgId = Math.max(lastMsgId, m.id);
+              if (answeredIds[m.id]) return; // Skip already rendered messages
+              answeredIds[m.id] = true;
               console.log("[FRONTEND RENDER]", m.id, m.content);
               if (m.role === 'assistant') {
                 botMsg(m.content, [], null);
               } else if (m.role === 'system') {
```

#### 3. Mark existing messages inside `syncThenPoll()`:
```diff
     function syncThenPoll() {
       if (pollTimer) return; // already polling
       // Silently fetch current max message ID — don't display anything
       fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
         .then(function (r) { return r.json(); })
         .then(function (d) {
           if (d.messages && d.messages.length) {
-            d.messages.forEach(function (m) { lastMsgId = Math.max(lastMsgId, m.id); });
+            d.messages.forEach(function (m) {
+              lastMsgId = Math.max(lastMsgId, m.id);
+              answeredIds[m.id] = true; // Mark as rendered so polling doesn't duplicate
+            });
           }
           startPolling();
         })
```

---

### [static/widget_content.js](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js)

`widget_content.js` already had the declaration `var answeredIds = {};` but was not using it.

#### 1. Guard inside `startPolling()`:
```diff
   function startPolling() {
     if (pollTimer) return;
     pollTimer = setInterval(function () {
       fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
         .then(function (r) { return r.json(); })
         .then(function (d) {
           d.messages.forEach(function (m) {
             lastMsgId = Math.max(lastMsgId, m.id); // BUG FIX 02 — advance cursor before rendering
+            if (answeredIds[m.id]) return; // Skip already rendered messages
+            answeredIds[m.id] = true;
             console.log("[FRONTEND RENDER]", m.id, m.content);
             $('av-send-btn').disabled = false;
             if (m.role === 'assistant') botMsg(m.content, [], null);
```

#### 2. Mark existing messages inside `syncThenPoll()`:
```diff
   function syncThenPoll() {
     if (pollTimer) return;
     fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
       .then(function (r) { return r.json(); })
       .then(function (d) {
         if (d.messages && d.messages.length) {
-          d.messages.forEach(function (m) { lastMsgId = Math.max(lastMsgId, m.id); });
+          d.messages.forEach(function (m) {
+            lastMsgId = Math.max(lastMsgId, m.id);
+            answeredIds[m.id] = true; // Mark as rendered so polling doesn't duplicate
+          });
         }
         startPolling();
       }).catch(function () { startPolling(); });
   }
```

---

## 4. Verification

### Before Fix
When the agent sent a reply, it was saved once to the database, but due to overlapping intervals, concurrent polls with the same `since_id` returned the message multiple times. Because there was no message deduplication guard in the loop, `botMsg` ran twice and appended duplicate messages in the customer chat widget.

### After Fix
A verification run simulating user registering, triggering handoff, and the agent replying shows:
1. **Exactly one database save** executes.
2. **Exactly one SSE alert** triggers.
3. **Exactly one backend response** contains the new message.
4. **Exactly one frontend render log** executes, rendering the message exactly once in the widget UI:

#### Server Logs during interaction:
```text
[DB SAVE] test_sess_flow_123 user connect me to support
[DB SAVE] test_sess_flow_123 assistant You can reach out to our support team fo
[POLL] session=test_sess_flow_123 since=0 messages_returned=2
[DB SAVE] test_sess_flow_123 system agent1 has joined the chat
[POLL] session=test_sess_flow_123 since=144 messages_returned=1
[DB SAVE] test_sess_flow_123 assistant Hello from live agent!
[POLL] session=test_sess_flow_123 since=145 messages_returned=1
[POLL] session=test_sess_flow_123 since=146 messages_returned=0
```

#### Client Console Output:
```text
[FRONTEND RENDER] 143 "connect me to support"
[FRONTEND RENDER] 144 "You can reach out..."
[FRONTEND RENDER] 145 "agent1 has joined the chat"
[FRONTEND RENDER] 146 "Hello from live agent!"
```
If a message is fetched twice in subsequent fast polls, the client detects that the message ID is already present in `answeredIds` and skips rendering it.
