"""
Agent Service
=============
Business logic for all human-agent operations.

Extracted from main.py as part of the modularization refactor (Step 9).
FastAPI route decorators remain in main.py; this module contains only
the processing logic called by those routes.
"""

import asyncio
import json as json_lib

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.database.database import (
    get_agent_by_username,
    get_active_agent_sessions,
    get_session_messages,
    get_session_poll_data,
    get_waiting_or_active_sessions,
    get_all_sessions,
    claim_session,
    touch_session,
    close_session,
    save_message,
    hash_password,
)


# ---------------------------------------------------------------------------
# Session Polling
# ---------------------------------------------------------------------------

def process_poll_session(session_id: str, since_id: int = 0) -> dict:
    """Return new messages and current session status for the chat widget."""
    rows, status_row = get_session_poll_data(session_id, since_id)
    return {
        "messages": [{"id": r[0], "role": r[1], "content": r[2]} for r in rows],
        "status": status_row[0] if status_row else "bot",
        "agent_name": status_row[1] if status_row else None,
    }


# ---------------------------------------------------------------------------
# SSE Event Stream (dashboard live queue)
# ---------------------------------------------------------------------------

def build_agent_events_response() -> StreamingResponse:
    """
    Server-Sent Events stream that pushes queue-update notifications to the
    agent dashboard whenever the number of waiting / active sessions changes.
    """
    async def event_stream():
        last_count = 0
        while True:
            try:
                rows = get_waiting_or_active_sessions()
                count = len(rows)
                if count != last_count:
                    last_count = count
                    data = json_lib.dumps({
                        "type": "queue_update",
                        "count": count,
                        "sessions": [
                            {
                                "session_id": r[0],
                                "user_name": r[1],
                                "status": r[2],
                                "updated_at": r[3],
                            }
                            for r in rows
                        ],
                    })
                    print(f"[SSE] Queue update sent: count={count}")
                    yield f"data: {data}\n\n"
                else:
                    yield "data: {\"type\":\"ping\"}\n\n"
            except Exception as e:
                print(f"[SSE ERROR] {e}")
                yield f"data: {{\"type\":\"error\",\"msg\":\"{str(e)}\"}}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Agent Authentication
# ---------------------------------------------------------------------------

def process_agent_login(username: str, password: str) -> dict:
    """Verify agent credentials and return identity on success."""
    row = get_agent_by_username(username)
    if not row or row[1] != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"status": "ok", "display_name": row[0], "username": username}


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

def process_agent_sessions() -> dict:
    """Return all waiting/active sessions for the agent queue."""
    rows = get_active_agent_sessions()
    return {
        "sessions": [
            {
                "session_id": r[0],
                "user_name": r[1],
                "user_email": r[2],
                "user_phone": r[3],
                "status": r[4],
                "assigned_agent": r[5],
                "issue_type": r[6],
                "priority": r[7],
                "updated_at": r[8],
            }
            for r in rows
        ]
    }


def process_agent_all_sessions() -> dict:
    """Return ALL sessions including closed ones for the history view."""
    rows = get_all_sessions()
    return {
        "sessions": [
            {
                "session_id": r[0],
                "user_name": r[1],
                "user_email": r[2],
                "user_phone": r[3],
                "status": r[4],
                "assigned_agent": r[5],
                "issue_type": r[6],
                "priority": r[7],
                "updated_at": r[8],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Chat History
# ---------------------------------------------------------------------------

def process_agent_history(session_id: str) -> dict:
    """Return full message history for a given session."""
    rows = get_session_messages(session_id)
    return {
        "messages": [
            {"id": r[0], "role": r[1], "content": r[2], "time": r[3]}
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Agent Actions
# ---------------------------------------------------------------------------

def process_agent_claim(session_id: str, agent_name: str) -> dict:
    """Claim a waiting session and notify the user."""
    claim_session(session_id, agent_name)
    save_message(session_id, "system", f"{agent_name} has joined the chat")
    return {"status": "claimed"}


def process_agent_reply(session_id: str, message: str) -> dict:
    """Persist an agent reply and keep the session alive."""
    save_message(session_id, "assistant", message)
    touch_session(session_id)
    return {"status": "sent"}


def process_agent_close(session_id: str) -> dict:
    """Close a session and append a closure notice to the transcript."""
    close_session(session_id)
    save_message(
        session_id,
        "system",
        "Agent has ended this conversation. Chat history preserved.",
    )
    return {"status": "closed"}
