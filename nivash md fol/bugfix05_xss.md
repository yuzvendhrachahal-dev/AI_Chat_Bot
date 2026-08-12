# Bug Fix 05 — Reflected & Stored XSS Prevention

## 1. Root Cause

The frontend rendered markdown into HTML using `cleanMd()`, which directly inserted user and bot text into the DOM via `.innerHTML`. However, the input was not sanitized for HTML entities. This allowed any user to input malicious HTML tags (e.g., `<script>`, `<img src=x onerror=...>`, etc.), which would be executed in the browser. Since these messages are also saved in the database, it created a stored XSS vulnerability in the Agent Dashboard.

## 2. Files Modified

| File | Change |
|------|--------|
| `static/widget_content.js` | Added entity escaping to `cleanMd()` |
| `templates/index.html` | Added entity escaping to `cleanMd()` |

## 3. Code Changes

### `cleanMd()` Sanitization

```javascript
  function cleanMd(t) {
    return (t || '')
      .replace(/</g, '&lt;').replace(/>/g, '&gt;') // ← HTML entity escaping
      .replace(/https?:\/\/[^\s)]+/g, '')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // ... existing formatting ...
```

By placing the `.replace(/</g, '&lt;')` logic at the absolute beginning of the formatting chain, all potential HTML tags are converted to safe string literals before any markdown features (bolding, lists, links) are processed.

## 4. Verification Steps

1. **Open the Chat Widget.**
2. **Send XSS Payload:** Type `<script>alert(1)</script>` into the input box and send.
3. **Verify:** The message should render visually as plain text (`<script>alert(1)</script>`) without triggering an alert box.
4. **Markdown Preservation:** Send a message with `**bold**` text. Verify it renders correctly in bold to confirm the escaping logic did not break the markdown parsing.
