import sqlite3
import hashlib

DATABASE_PATH = "chat.db"

def get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect(DATABASE_PATH)

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT,
        content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_sessions (
        session_id TEXT PRIMARY KEY, user_name TEXT, user_email TEXT, user_phone TEXT,
        status TEXT DEFAULT 'bot', assigned_agent TEXT, issue_type TEXT,
        priority TEXT DEFAULT 'normal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
        password_hash TEXT, display_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

def seed_default_agents():
    conn = get_db_connection()
    if conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0:
        for u, p, n in [("agent1", "astroved123", "Support Agent 1"), ("agent2", "astroved123", "Support Agent 2")]:
            conn.execute("INSERT INTO agents (username, password_hash, display_name) VALUES (?, ?, ?)", (u, hash_password(p), n))
        conn.commit()
        print("Seeded default agent accounts")
    conn.close()

def get_history(session_id: str):
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? AND role IN ('user','assistant') ORDER BY created_at DESC LIMIT 20",
            (session_id,)).fetchall()
        conn.close()
        history = []
        for r, c in reversed(rows):
            if r in ("user", "assistant") and c and str(c).strip():
                history.append({"role": r, "content": str(c).strip()})
        return history
    except Exception as e:
        print(f"get_history error: {e}")
        return []

def save_message(session_id: str, role: str, content: str):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO messages (session_id, role, content) VALUES (?,?,?)", (session_id, role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"save_message error: {e}")

def create_or_update_handoff(session_id, name, email, phone, issue_type, priority):
    conn = get_db_connection()
    if conn.execute("SELECT session_id FROM agent_sessions WHERE session_id=?", (session_id,)).fetchone():
        conn.execute("UPDATE agent_sessions SET status='waiting', issue_type=?, priority=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?",
            (issue_type, priority, session_id))
    else:
        conn.execute("INSERT INTO agent_sessions (session_id, user_name, user_email, user_phone, status, issue_type, priority) VALUES (?,?,?,?,'waiting',?,?)",
            (session_id, name, email, phone, issue_type, priority))
    conn.commit()
    conn.close()

def create_or_update_session(session_id: str, user_name: str, user_email: str, user_phone: str):
    conn = get_db_connection()
    if conn.execute("SELECT session_id FROM agent_sessions WHERE session_id=?", (session_id,)).fetchone():
        conn.execute("UPDATE agent_sessions SET user_name=?, user_email=?, user_phone=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?",
            (user_name, user_email, user_phone, session_id))
    else:
        conn.execute("INSERT INTO agent_sessions (session_id, user_name, user_email, user_phone, status) VALUES (?,?,?,?,'bot')",
            (session_id, user_name, user_email, user_phone))
    conn.commit()
    conn.close()

def get_admin_users():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT session_id, user_name, user_email, user_phone, status, issue_type, created_at, updated_at FROM agent_sessions ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return rows

def get_and_update_session_status(session_id: str) -> str:
    conn = get_db_connection()
    row = conn.execute("SELECT status FROM agent_sessions WHERE session_id=?", (session_id,)).fetchone()
    if row and row[0] == "closed":
        conn.execute("UPDATE agent_sessions SET status='bot', updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
        conn.commit()
        row = ("bot",)
    conn.close()
    return row[0] if row else "bot"

def get_session_poll_data(session_id: str, since_id: int = 0):
    conn = get_db_connection()
    rows = conn.execute("SELECT id, role, content FROM messages WHERE session_id=? AND id > ? ORDER BY id ASC", (session_id, since_id)).fetchall()
    status_row = conn.execute("SELECT status, assigned_agent FROM agent_sessions WHERE session_id=?", (session_id,)).fetchone()
    conn.close()
    return rows, status_row

def get_agent_by_username(username: str):
    conn = get_db_connection()
    row = conn.execute("SELECT display_name, password_hash FROM agents WHERE username=?", (username,)).fetchone()
    conn.close()
    return row

def get_active_agent_sessions():
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT session_id, user_name, user_email, user_phone, status, assigned_agent, issue_type, priority, updated_at
           FROM agent_sessions WHERE status IN ('waiting','with_agent')
           ORDER BY CASE priority WHEN 'urgent' THEN 0 ELSE 1 END, updated_at ASC""").fetchall()
    conn.close()
    return rows

def get_session_messages(session_id: str):
    conn = get_db_connection()
    rows = conn.execute("SELECT id, role, content, created_at FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,)).fetchall()
    conn.close()
    return rows

def claim_session(session_id: str, agent_name: str):
    conn = get_db_connection()
    conn.execute("UPDATE agent_sessions SET status='with_agent', assigned_agent=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (agent_name, session_id))
    conn.commit()
    conn.close()

def touch_session(session_id: str):
    conn = get_db_connection()
    conn.execute("UPDATE agent_sessions SET updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

def close_session(session_id: str):
    conn = get_db_connection()
    conn.execute("UPDATE agent_sessions SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT session_id, user_name, user_email, user_phone, status, 
           assigned_agent, issue_type, priority, updated_at
           FROM agent_sessions 
           ORDER BY updated_at DESC LIMIT 100"""
    ).fetchall()
    conn.close()
    return rows

def get_waiting_or_active_sessions():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT session_id, user_name, status, updated_at FROM agent_sessions WHERE status IN ('waiting','with_agent') ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return rows

def save_user_registration(session_id: str, user_name: str, user_email: str, user_phone: str, country_code: str, synced_to_api: int = 0):
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_name TEXT,
            user_email TEXT,
            user_phone TEXT,
            country_code TEXT,
            synced_to_api INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    conn.execute(
        "INSERT INTO user_registrations (session_id, user_name, user_email, user_phone, country_code, synced_to_api) VALUES (?,?,?,?,?,?)",
        (session_id, user_name, user_email, user_phone, country_code, synced_to_api)
    )
    conn.commit()
    conn.close()

def get_all_registrations():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, session_id, user_name, user_email, user_phone, country_code, synced_to_api, created_at FROM user_registrations ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return rows
