import re

def load_knowledge_base():
    chunks = []
    try:
        with open("knowledge_base.txt", "r", encoding="utf-8") as f:
            content = f.read()
        parts = re.split(r"\n--- PAGE: (.*?) \((https?://[^\)]+)\) ---\n", content)
        for i in range(1, len(parts) - 2, 3):
            title, url, text = parts[i].strip(), parts[i+1].strip(), parts[i+2].strip()
            if text:
                chunks.append({"title": title, "url": url, "text": text[:1500]})
        print(f"Loaded {len(chunks)} page chunks from knowledge base")
    except Exception as e:
        print(f"Could not load knowledge_base.txt: {e}")
    return chunks

KB_CHUNKS = load_knowledge_base()

def reload_knowledge_base():
    global KB_CHUNKS
    KB_CHUNKS = load_knowledge_base()

def search_knowledge(query: str, top_k: int = 3):
    """Same as search_knowledge but also returns the matched chunks (with URL/title)
    so we can build a real topic_url even when there's no TOPIC_MAP entry."""
    if not KB_CHUNKS:
        return "", []
    query_words = set(re.findall(r"[a-zA-Z]{3,}", query.lower()))
    if not query_words:
        return "", []
    scored = []
    for chunk in KB_CHUNKS:
        haystack = (chunk["title"] + " " + chunk["text"]).lower()
        score = sum(1 for w in query_words if w in haystack)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    text = "".join(f"\n[Page: {c['title']}]\nURL: {c['url']}\n{c['text'][:800]}\n" for _, c in top)
    matches = [{"title": c["title"], "url": c["url"], "score": s} for s, c in top]
    return text, matches

def search_knowledge_for_url(url_fragment: str, top_k: int = 2):
    if not KB_CHUNKS: return ""
    matches = [c for c in KB_CHUNKS if url_fragment in c["url"].lower()]
    return "".join(f"\n[Page: {c['title']}]\nURL: {c['url']}\n{c['text'][:800]}\n" for c in matches[:top_k])
