import pymongo
import hashlib
from datetime import datetime, timezone
from pymongo import MongoClient
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
        rows.append((
            doc.get("session_id"),
            doc.get("user_name"),
            doc.get("user_email"),
            doc.get("user_phone"),
            doc.get("status"),
            doc.get("issue_type"),
            doc.get("created_at"),
            doc.get("updated_at")
        ))
    return rows

def get_and_update_session_status(session_id: str) -> str:
    doc = sessions_col.find_one({"session_id": session_id})
    if doc and doc.get("status") == "closed":
        sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"status": "bot", "updated_at": datetime.now(timezone.utc)}}
        )
        return "bot"
    return doc.get("status", "bot") if doc else "bot"

def get_session_poll_data(session_id: str, since_id: int = 0):
    messages_cursor = messages_col.find(
        {"session_id": session_id, "id": {"$gt": since_id}}
    ).sort("id", pymongo.ASCENDING)
    
    rows = []
    for m in messages_cursor:
        rows.append((m.get("id"), m.get("role"), m.get("content")))
        
    status_doc = sessions_col.find_one({"session_id": session_id})
    status_row = None
    if status_doc:
        status_row = (status_doc.get("status"), status_doc.get("assigned_agent"))
        
    return rows, status_row

def get_agent_by_username(username: str):
    doc = agents_col.find_one({"username": username})
    if doc:
        return (doc.get("display_name"), doc.get("password_hash"))
    return None

def get_active_agent_sessions():
    cursor = sessions_col.find(
        {"status": {"$in": ["waiting", "with_agent"]}}
    ).sort([("priority", pymongo.DESCENDING), ("updated_at", pymongo.ASCENDING)])
    
    docs = list(cursor)
    docs.sort(key=lambda x: (0 if x.get("priority") == "urgent" else 1, x.get("updated_at") or datetime.now(timezone.utc)))
    
    rows = []
    for doc in docs:
        rows.append((
            doc.get("session_id"),
            doc.get("user_name"),
            doc.get("user_email"),
            doc.get("user_phone"),
            doc.get("status"),
            doc.get("assigned_agent"),
            doc.get("issue_type"),
            doc.get("priority"),
            doc.get("updated_at")
        ))
    return rows

def get_session_messages(session_id: str):
    cursor = messages_col.find({"session_id": session_id}).sort("id", pymongo.ASCENDING)
    rows = []
    for m in cursor:
        rows.append((m.get("id"), m.get("role"), m.get("content"), m.get("created_at")))
    return rows

def claim_session(session_id: str, agent_name: str):
    sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": "with_agent",
            "assigned_agent": agent_name,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

def touch_session(session_id: str):
    sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"updated_at": datetime.now(timezone.utc)}}
    )

def close_session(session_id: str):
    sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": "closed",
            "updated_at": datetime.now(timezone.utc)
        }}
    )

def get_all_sessions():
    cursor = sessions_col.find().sort("updated_at", pymongo.DESCENDING).limit(100)
    rows = []
    for doc in cursor:
        rows.append((
            doc.get("session_id"),
            doc.get("user_name"),
            doc.get("user_email"),
            doc.get("user_phone"),
            doc.get("status"),
            doc.get("assigned_agent"),
            doc.get("issue_type"),
            doc.get("priority"),
            doc.get("updated_at")
        ))
    return rows

def get_waiting_or_active_sessions():
    cursor = sessions_col.find(
        {"status": {"$in": ["waiting", "with_agent"]}}
    ).sort("updated_at", pymongo.DESCENDING)
    
    rows = []
    for doc in cursor:
        rows.append((
            doc.get("session_id"),
            doc.get("user_name"),
            doc.get("status"),
            doc.get("updated_at")
        ))
    return rows

def save_user_registration(session_id: str, user_name: str, user_email: str, user_phone: str, country_code: str, synced_to_api: int = 0):
    users_col.insert_one({
        "session_id": session_id,
        "user_name": user_name,
        "user_email": user_email,
        "user_phone": user_phone,
        "country_code": country_code,
        "synced_to_api": synced_to_api,
        "created_at": datetime.now(timezone.utc)
    })
    
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

def get_all_registrations():
    cursor = users_col.find().sort("created_at", pymongo.DESCENDING).limit(100)
    rows = []
    for doc in cursor:
        rows.append((
            str(doc.get("_id")),
            doc.get("session_id"),
            doc.get("user_name"),
            doc.get("user_email"),
            doc.get("user_phone"),
            doc.get("country_code"),
            doc.get("synced_to_api"),
            doc.get("created_at")
        ))
    return rows
