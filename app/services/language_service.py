def detect_language(text: str) -> str:
    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    return "tamil" if tamil_chars > 0 else "english"
