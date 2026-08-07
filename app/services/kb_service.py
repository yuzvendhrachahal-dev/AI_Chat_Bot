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

STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "has", 
    "him", "his", "how", "who", "what", "why", "out", "our", "she", "too", "was", 
    "with", "this", "that", "there", "their", "have", "they", "will", "would", 
    "could", "should", "your", "when", "where", "which", "then", "than", "them", 
    "these", "those", "been", "much", "many", "some", "such", "into", "upon", 
    "about", "above", "below", "before", "after", "under", "over", "does", "from",
    "is", "am", "doing", "did", "were", "it", "its"
}

def search_knowledge(query: str, top_k: int = 3):
    """Same as search_knowledge but also returns the matched chunks (with URL/title)
    so we can build a real topic_url even when there's no TOPIC_MAP entry."""
    if not KB_CHUNKS:
        return "", []
        
    # Extract words >= 3 chars, convert to lowercase, and remove stop words
    words = re.findall(r"[a-zA-Z]{3,}", query.lower())
    query_words = set(w for w in words if w not in STOP_WORDS)
    
    if not query_words:
        return "", []
        
    scored = []
    for chunk in KB_CHUNKS:
        haystack = (chunk["title"] + " " + chunk["text"]).lower()
        # Pad haystack with spaces and replace non-alpha with spaces for fast word-boundary matching
        haystack_padded = " " + re.sub(r'[^a-z]', ' ', haystack) + " "
        
        score = sum(1 for w in query_words if f" {w} " in haystack_padded)
        
        # Root Cause Fix: Only consider it a match if a significant portion of the query matched.
        # Otherwise, queries like "Who is the Chief Minister of Tamil Nadu?" match just "tamil" and "nadu"
        # and bypass the off-domain guard. Require at least >50% of the meaningful query words to match.
        ratio = score / len(query_words)
        if score > 0 and ratio > 0.5:
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
