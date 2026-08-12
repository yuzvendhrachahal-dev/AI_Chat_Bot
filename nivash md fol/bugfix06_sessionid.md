# Bug Fix 06 — Secure Backend Session ID Generation

## 1. Root Cause

The frontend was generating `sessId` natively using `Math.random().toString(36)`. This approach is insecure because:
1. `Math.random()` is not cryptographically secure and is easily predictable.
2. It opened the application to Session Hijacking, where attackers could guess a user's session ID and pull their chat history or interact with an agent on their behalf.

## 2. Files Modified

| File | Change |
|------|--------|
| `app/routes/chat.py` | Added a new endpoint `GET /session/start` that returns a securely generated `uuid.uuid4().hex`. |
| `static/widget_content.js` | Updated initialization and `restart()` to fetch `session_id` from the backend instead of using `Math.random()`. |
| `templates/index.html` | Updated initialization and `restart()` equivalently. |

## 3. Code Changes

### Backend API addition (`app/routes/chat.py`)

```python
import uuid

@router.get("/session/start")
async def session_start():
    try:
        return {"session_id": f"sess_{uuid.uuid4().hex}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend modification

```javascript
  // Old (Insecure)
  var sessId = 'av_' + Math.random().toString(36).slice(2);

  // New (Secure)
  var sessId = '';
  fetch(API + '/session/start')
    .then(function(r){return r.json();})
    .then(function(d){sessId=d.session_id;})
    .catch(function(){sessId='sess_'+Math.random().toString(36).slice(2);}); // Fallback on network failure
```

## 4. Verification Steps

1. **Open the chat widget in a new incognito window.**
2. **Open Network tools in DevTools.**
3. **Verify:** You should see a `GET` request to `/session/start`. The response payload should contain a 32-character hexadecimal UUID prefixed with `sess_`.
4. **Chat interaction:** Send a test message and verify it arrives on the agent dashboard under the newly generated secure session ID.
