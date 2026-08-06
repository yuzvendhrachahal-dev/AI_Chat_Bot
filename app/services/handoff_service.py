from app.config.settings import HANDOFF_KEYWORDS
from app.database.database import create_or_update_handoff

def needs_handoff(text: str) -> bool:
    return any(k in text.lower() for k in HANDOFF_KEYWORDS)
