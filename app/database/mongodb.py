import pymongo
import hashlib
from datetime import datetime, timezone
from pymongo import MongoClient


def fmt_dt(dt) -> str:
    """
    Serialize a datetime to a UTC ISO-8601 string with a 'Z' suffix.

    Always returns UTC regardless of whether the stored datetime is
    timezone-aware or naive (naïve values are assumed to be UTC, which
    matches the datetime.now(timezone.utc) storage convention used
    throughout this application).

    Example output: '2026-08-18T11:40:15.275Z'
    """
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return str(dt)
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC (matches our storage convention)
        dt = dt.replace(tzinfo=timezone.utc)
    # Express in UTC, format with millisecond precision and Z suffix
    dt_utc = dt.astimezone(timezone.utc)
    ms = dt_utc.microsecond // 1000
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


from app.config.settings import MONGO_URI, MONGO_DB

# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Collections
users_col = db["users"]
agents_col = db["agents"]
sessions_col = db["sessions"]
messages_col = db["messages"]

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    agents_col.create_index("username", unique=True)
    sessions_col.create_index("session_id", unique=True)
    messages_col.create_index([("session_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)])

def seed_default_agents():
    if agents_col.count_documents({}) == 0:
        default_agents = [
            {
                "username": "agent1",
                "password_hash": hash_password("astroved123"),
                "display_name": "Support Agent 1",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "username": "agent2",
                "password_hash": hash_password("astroved123"),
                "display_name": "Support Agent 2",
                "created_at": datetime.now(timezone.utc)
            }
        ]
        agents_col.insert_many(default_agents)
        print("Seeded default agent accounts in MongoDB")

def get_history(session_id: str):
    try:
        cursor = messages_col.find(
            {"session_id": session_id, "role": {"$in": ["user", "assistant"]}}
        ).sort("timestamp", pymongo.DESCENDING).limit(20)
        
        rows = list(cursor)
        history = []
        for r in reversed(rows):
            if r["role"] in ("user", "assistant") and r.get("content") and str(r["content"]).strip():
                history.append({"role": r["role"], "content": str(r["content"]).strip()})
        return history
    except Exception as e:
        print(f"get_history error: {e}")
        return []

def save_message(session_id: str, role: str, content: str, agent_id: str = None):
    try:
        current_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        msg_doc = {
            "id": current_time_ms,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }
        if agent_id:
            msg_doc["agent_id"] = agent_id
            
        messages_col.insert_one(msg_doc)
    except Exception as e:
        print(f"save_message error: {e}")

def create_or_update_handoff(session_id, name, email, phone, issue_type, priority):
    existing = sessions_col.find_one({"session_id": session_id})
    if existing:
        sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "waiting",
                "issue_type": issue_type,
                "priority": priority,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    else:
        sessions_col.insert_one({
            "session_id": session_id,
            "user_name": name,
            "user_email": email,
            "user_phone": phone,
            "status": "waiting",
            "issue_type": issue_type,
            "priority": priority,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

def create_or_update_session(session_id: str, user_name: str, user_email: str, user_phone: str):
    existing = sessions_col.find_one({"session_id": session_id})
    if existing:
        sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {
                "user_name": user_name,
                "user_email": user_email,
                "user_phone": user_phone,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    else:
        sessions_col.insert_one({
            "session_id": session_id,
            "user_name": user_name,
            "user_email": user_email,
            "user_phone": user_phone,
            "status": "bot",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

def get_admin_users():
    cursor = sessions_col.find().sort("updated_at", pymongo.DESCENDING)
    rows = []
    for doc in cursor:
        rows.append({
            "session_id":  doc.get("session_id"),
            "user_name":   doc.get("user_name"),
            "user_email":  doc.get("user_email"),
            "user_phone":  doc.get("user_phone"),
            "status":      doc.get("status"),
            "issue_type":  doc.get("issue_type"),
            "created_at":  fmt_dt(doc.get("created_at")),
            "updated_at":  fmt_dt(doc.get("updated_at")),
        })
    return rows

def get_and_update_session_status(session_id: str) -> str:
    doc = sessions_col.find_one({"session_id": session_id})
    if doc and doc.get("status") == "closed":
        return "bot"
    return doc.get("status", "bot") if doc else "bot"

def get_session_poll_data(session_id: str, since_id: int = 0):
    messages_cursor = messages_col.find(
        {"session_id": session_id, "id": {"$gt": since_id}}
    ).sort("id", pymongo.ASCENDING)

    rows = []
    for m in messages_cursor:
        rows.append({"id": m.get("id"), "role": m.get("role"), "content": m.get("content")})

    status_doc = sessions_col.find_one({"session_id": session_id})
    status_row = None
    if status_doc:
        status_row = {
            "status":     status_doc.get("status"),
            "agent_name": status_doc.get("assigned_agent"),
        }

    return rows, status_row

def get_agent_by_username(username: str):
    doc = agents_col.find_one({"username": username})
    if doc:
        return {"display_name": doc.get("display_name"), "password_hash": doc.get("password_hash")}
    return None

def get_active_agent_sessions():
    cursor = sessions_col.find(
        {"status": {"$in": ["waiting", "with_agent"]}}
    ).sort([("priority", pymongo.DESCENDING), ("updated_at", pymongo.ASCENDING)])

    docs = list(cursor)
    docs.sort(key=lambda x: (0 if x.get("priority") == "urgent" else 1, x.get("updated_at") or datetime.now(timezone.utc)))

    rows = []
    for doc in docs:
        rows.append({
            "session_id":     doc.get("session_id"),
            "user_name":      doc.get("user_name"),
            "user_email":     doc.get("user_email"),
            "user_phone":     doc.get("user_phone"),
            "status":         doc.get("status"),
            "assigned_agent": doc.get("assigned_agent"),
            "issue_type":     doc.get("issue_type"),
            "priority":       doc.get("priority"),
            "updated_at":     fmt_dt(doc.get("updated_at")),
        })
    return rows

def get_session_messages(session_id: str):
    cursor = messages_col.find({"session_id": session_id}).sort("id", pymongo.ASCENDING)
    rows = []
    for m in cursor:
        rows.append({
            "id":      m.get("id"),
            "role":    m.get("role"),
            "content": m.get("content"),
            "time":    fmt_dt(m.get("created_at") or m.get("timestamp")),
        })
    return rows

def claim_session(session_id: str, agent_name: str) -> bool:
    result = sessions_col.update_one(
        {"session_id": session_id, "status": "waiting"},
        {"$set": {
            "status": "with_agent",
            "assigned_agent": agent_name,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    return result.modified_count > 0

def touch_session(session_id: str):
    sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"updated_at": datetime.now(timezone.utc)}}
    )

def close_session(session_id: str) -> bool:
    result = sessions_col.update_one(
        {"session_id": session_id, "status": "with_agent"},
        {"$set": {
            "status": "closed",
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    return result.modified_count > 0

def get_all_sessions():
    cursor = sessions_col.find().sort("updated_at", pymongo.DESCENDING).limit(100)
    rows = []
    for doc in cursor:
        rows.append({
            "session_id":     doc.get("session_id"),
            "user_name":      doc.get("user_name"),
            "user_email":     doc.get("user_email"),
            "user_phone":     doc.get("user_phone"),
            "status":         doc.get("status"),
            "assigned_agent": doc.get("assigned_agent"),
            "issue_type":     doc.get("issue_type"),
            "priority":       doc.get("priority"),
            "updated_at":     fmt_dt(doc.get("updated_at")),
        })
    return rows

def get_session_analytics():
    db_name = db.name
    col_name = sessions_col.name
    
    total = sessions_col.count_documents({})
    
    # Status breakdown
    status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_results = list(sessions_col.aggregate(status_pipeline))
    counts = {"waiting": 0, "with_agent": 0, "closed": 0, "bot": 0}
    for r in status_results:
        if r["_id"] in counts:
            counts[r["_id"]] = r["count"]
            
    # Issue types breakdown
    issue_pipeline = [{"$group": {"_id": "$issue_type", "count": {"$sum": 1}}}]
    issue_results = list(sessions_col.aggregate(issue_pipeline))
    issues = { (r["_id"] if r["_id"] else "general"): r["count"] for r in issue_results }
    
    # Recent users (limit 12)
    recent_cursor = sessions_col.find().sort("created_at", pymongo.DESCENDING).limit(12)
    recent = []
    for doc in recent_cursor:
        recent.append({
            "session_id":  doc.get("session_id"),
            "user_name":   doc.get("user_name"),
            "user_email":  doc.get("user_email"),
            "user_phone":  doc.get("user_phone"),
            "status":      doc.get("status"),
            "issue_type":  doc.get("issue_type"),
            "created_at":  fmt_dt(doc.get("created_at") or doc.get("updated_at")),
            "updated_at":  fmt_dt(doc.get("updated_at")),
        })

    print(f"[DIAGNOSTICS] DB: {db_name} | Collection: {col_name} | Total sessions found: {total}")
    
    return {
        "total": total,
        "waiting": counts["waiting"],
        "claimed": counts["with_agent"],
        "completed": counts["closed"],
        "bot": counts["bot"],
        "issues": issues,
        "recent_users": recent
    }

def get_waiting_or_active_sessions():
    cursor = sessions_col.find(
        {"status": {"$in": ["waiting", "with_agent"]}}
    ).sort("updated_at", pymongo.DESCENDING)

    rows = []
    for doc in cursor:
        rows.append({
            "session_id": doc.get("session_id"),
            "user_name":  doc.get("user_name"),
            "status":     doc.get("status"),
            "updated_at": fmt_dt(doc.get("updated_at")),
        })
    return rows

def save_user_registration(session_id: str, user_name: str, user_email: str, user_phone: str, country_code: str, synced_to_api: int = 0):
    try:
        now = datetime.now(timezone.utc)
        result = users_col.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "user_name": user_name,
                    "user_email": user_email,
                    "user_phone": user_phone,
                    "country_code": country_code,
                    "synced_to_api": synced_to_api,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )
        
        obj_id = result.upserted_id if result.upserted_id else "Updated existing"
        print(f"MongoDB Upsert Success | Collection: users | Session: {session_id} | Result: {obj_id}")
        
        # Synchronize session document with registered user info
        sessions_col.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "user_name": user_name,
                    "user_email": user_email,
                    "user_phone": user_phone
                }
            }
        )
    except Exception as e:
        print(f"MongoDB Upsert Failed | Collection: users | Error: {str(e)}")

def get_all_registrations():
    cursor = users_col.find().sort("created_at", pymongo.DESCENDING).limit(100)
    rows = []
    for doc in cursor:
        rows.append({
            "id":           str(doc.get("_id")),
            "session_id":   doc.get("session_id"),
            "user_name":    doc.get("user_name"),
            "user_email":   doc.get("user_email"),
            "user_phone":   doc.get("user_phone"),
            "country_code": doc.get("country_code"),
            "synced_to_api":doc.get("synced_to_api"),
            "created_at":   fmt_dt(doc.get("created_at")),
        })
    return rows