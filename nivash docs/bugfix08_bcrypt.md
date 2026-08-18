# Bug Fix 08 — Secure Password Hashing (Bcrypt)

## 1. Root Cause

The agent dashboard authentication stored agent passwords in the database using plain `SHA-256`. This hashing algorithm is extremely fast and designed for message integrity, making it highly vulnerable to brute-force and dictionary attacks (rainbow tables) if the database is ever leaked.

## 2. Files Modified

| File | Change |
|------|--------|
| `requirements.txt` | Added `passlib[bcrypt]` |
| `app/database/database.py` | Migrated `hash_password()` to use `passlib.context.CryptContext` with `bcrypt`. |
| `app/services/agent_service.py` | Migrated `process_agent_login()` to use `pwd_context.verify()` instead of direct hash comparison. |

## 3. Code Changes

### Database hashing update

```python
# app/database/database.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)
```

### Agent Service verification update

```python
# app/services/agent_service.py
from app.database.database import pwd_context

def process_agent_login(username: str, password: str) -> dict:
    row = get_agent_by_username(username)
    # Replaced: if not row or row[1] != hash_password(password):
    if not row or not pwd_context.verify(password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"status": "ok", "display_name": row[0], "username": username}
```

## 4. Verification Steps

1. **Delete the existing database:** Remove `chat.db` to allow the seed function to run again on the next startup.
2. **Restart the server:** Wait for `init_db()` and `seed_default_agents()` to execute.
3. **Inspect the database:** Use a sqlite browser to view the `agents` table. The `password_hash` column should now begin with `$2b$` (the bcrypt identifier) instead of a 64-character hex string.
4. **Login:** Attempt to log into the agent dashboard using `agent1` and `astroved123`. It should succeed, verifying that `pwd_context.verify()` correctly validates the plaintext against the bcrypt hash.
