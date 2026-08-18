import os
from dotenv import load_dotenv

# Environment variable loading
load_dotenv()

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in .env file!")

APP_URL = os.getenv("APP_URL")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "astroved_chatbot")


print("Mongo URI:", os.getenv("MONGO_URI"))
print("Mongo DB:", os.getenv("MONGO_DB"))


# Website URLs
SITE = "https://www.astroved.com"
ASTROVED_API_BASE = "https://qawebservice.astroved.com/api"

# API Tokens / Authentication
ASTROVED_JWT_TOKEN = os.getenv("ASTROVED_JWT_TOKEN", "")

# CRM keyword lists
# FIX: kept narrow + specific to real billing/escalation issues, mirrors the
# widget's CRM_KW list so backend and frontend agree on what truly needs a human.
HANDOFF_KEYWORDS = [
    'refund', 'billing issue', 'invoice problem', 'payment failed', 'payment issue',
    'cancel my subscription', 'complaint', 'talk to agent', 'talk to a human',
    'speak to agent', 'speak to a human', 'human agent', 'call me back',
    'account issue', 'order tracking', 'not working', 'broken', 'urgent help'
]
