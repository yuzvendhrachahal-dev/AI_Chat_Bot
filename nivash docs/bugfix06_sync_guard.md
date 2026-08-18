# Bug Fix 06 — Prevent Concurrent Execution of syncThenPoll()

## 1. Root Cause
In both the chatbot standalone application ([`templates/index.html`](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html)) and the embedded widget script ([`static/widget_content.js`](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js)), `syncThenPoll()` coordinates setting up the client-side poll cursor (`lastMsgId`) before launching the polling loop.
- It checks `if (pollTimer) return;` to prevent duplicate polling loops.
- However, during the asynchronous `/poll` catch-up fetch request, `pollTimer` is still `null`.
- If the customer triggered handoff, registered, or sent a message in rapid succession while the catch-up request was still in flight, multiple `syncThenPoll()` calls would bypass the `pollTimer` check and fire concurrent `/poll` fetches.
- Although they resolved sequentially without duplicate intervals, it resulted in overlapping fetches and redundant traffic.

## 2. Files Changed
- [`templates/index.html`](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html) (Modified `syncThenPoll()` and `restart()` functions)
- [`static/widget_content.js`](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js) (Modified `syncThenPoll()` and `restart()` functions)

## 3. Code Changes

### [templates/index.html](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html)
```diff
     var lastMsgId = 0;
     var isSending = false;  // BUG FIX 02 — prevents concurrent POST /chat
     var answeredIds = {};   // BUG FIX 02 — tracking rendered message IDs
+    var syncInProgress = false; // BUG FIX 06 — prevents concurrent syncThenPoll fetches
...
     function restart() {
       sessId = 'sess_' + Math.random().toString(36).slice(2);
       uName = '';
       uEmail = '';
       uPhone = '';
       msgCounter = 0;
       lastMsgId = 0;
       answeredIds = {};
+      syncInProgress = false;
       if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
...
     function syncThenPoll() {
       if (pollTimer) return; // already polling
+      if (syncInProgress) return; // fetch in progress
+      syncInProgress = true;
       // Silently fetch current max message ID — don't display anything
       fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
         .then(function (r) { return r.json(); })
         .then(function (d) {
           if (d.messages && d.messages.length) {
             d.messages.forEach(function (m) {
               lastMsgId = Math.max(lastMsgId, m.id);
               answeredIds[m.id] = true; // Mark as rendered so polling doesn't duplicate
             });
           }
           startPolling();
         })
-        .catch(function () { startPolling(); });
+        .catch(function () { startPolling(); })
+        .finally(function () { syncInProgress = false; });
     }
```

### [static/widget_content.js](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js)
```diff
   var isSending = false;
   var answeredIds = {};
+  var syncInProgress = false; // BUG FIX 06 — prevents concurrent syncThenPoll fetches
...
   function restart() {
     sessId = 'av_' + Math.random().toString(36).slice(2);
     uName = ''; uEmail = ''; uPhone = '';
     msgCounter = 0; lastMsgId = 0;
     answeredIds = {};
+    syncInProgress = false;
     if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
...
   function syncThenPoll() {
     if (pollTimer) return;
+    if (syncInProgress) return; // fetch in progress
+    syncInProgress = true;
     fetch(API + '/poll/' + sessId + '?since_id=' + lastMsgId)
       .then(function (r) { return r.json(); })
       .then(function (d) {
         if (d.messages && d.messages.length) {
           d.messages.forEach(function (m) {
             lastMsgId = Math.max(lastMsgId, m.id);
             answeredIds[m.id] = true; // Mark as rendered so polling doesn't duplicate
           });
         }
         startPolling();
       })
-      .catch(function () { startPolling(); });
+      .catch(function () { startPolling(); })
+      .finally(function () { syncInProgress = false; });
   }
```

---

## 4. Verification
1. Open the Chatbot UI and trigger handoff.
2. Fast double-click or submit rapid inputs to trigger `syncThenPoll()`.
3. In the **Network Tab** (DevTools):
   - Only **one** catch-up request to `/poll` is dispatched.
   - Subsequent calls return early and are blocked while `syncInProgress` is true.
   - Once the fetch resolves or rejects, `syncInProgress` resets to `false`, freeing the path for future synchronization.
