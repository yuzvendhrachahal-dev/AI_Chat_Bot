# Bug Fix 05 — Clear answeredIds on Conversation Restart

## 1. Root Cause
In both the standalone chatbot application ([`templates/index.html`](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html)) and the embedded widget ([`static/widget_content.js`](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js)), when a user clicks the "New Conversation" button:
1. `restart()` is invoked.
2. It resets the session ID (`sessId`), clears input values, resets the rating stars, and clears `lastMsgId` and the active `pollTimer`.
3. However, the `answeredIds` tracking object (used as a deduplication guard to prevent duplicate message rendering on the client side) was **not cleared**.
4. This meant that old message IDs from previous sessions remained stored in the memory cache of `answeredIds`. Although SQLite's global auto-incrementing key prevented immediate conflicts, it created a memory leak and potential rendering blockages if the database IDs were reset, or if keys overlapped.

## 2. Files Changed
- [`templates/index.html`](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html) (Modified `restart()` function)
- [`static/widget_content.js`](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js) (Modified `restart()` function)

## 3. Code Changes

### [templates/index.html](file:///Users/nivash/AV/AI_Chat_Bot/templates/index.html)
```diff
     function restart() {
       sessId = 'sess_' + Math.random().toString(36).slice(2);
       uName = '';
       uEmail = '';
       uPhone = '';
       msgCounter = 0;
       lastMsgId = 0;
+      answeredIds = {};
       if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
```

### [static/widget_content.js](file:///Users/nivash/AV/AI_Chat_Bot/static/widget_content.js)
```diff
   function restart() {
     sessId = 'av_' + Math.random().toString(36).slice(2);
     uName = ''; uEmail = ''; uPhone = '';
     msgCounter = 0; lastMsgId = 0;
+    answeredIds = {};
     if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
```

---

## 4. Verification
1. Start the chatbot application.
2. Complete a conversation and click **New Conversation**.
3. Re-enter name and start a new conversation.
4. Inspect state variables in the console (`answeredIds`, `lastMsgId`, `pollTimer`).
   - `answeredIds` is successfully reset to `{}`.
   - `lastMsgId` is successfully reset to `0`.
   - `pollTimer` is successfully set to `null` (decoupled/deallocated from previous intervals).
   - No memory leak persists across conversational sessions.
