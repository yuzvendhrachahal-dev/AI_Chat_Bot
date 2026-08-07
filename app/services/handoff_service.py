from app.config.settings import HANDOFF_KEYWORDS

def needs_handoff(text: str) -> bool:
    return any(k in text.lower() for k in HANDOFF_KEYWORDS)
