# Bug Fix 07 — Eliminate AI Hallucinations / Off-Domain Answers

## 1. Root Cause

### Problem A — System Prompt Permitted Off-Domain Answers
`BASE_SYSTEM_PROMPT` in [`app/prompts/prompts.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/prompts/prompts.py) contained:
```
Never refuse a question — if unsure, give general Vedic astrology guidance
```
This instruction explicitly told the LLM to **always answer**, even when a question like _"Who is the Chief Minister of Tamil Nadu?"_ or _"What is IPL?"_ fell completely outside AstroVed's domain. The LLM had no mandate to refuse; it simply drew from its training knowledge and hallucinated a confident response.

### Problem B — No Pre-LLM Domain Gate in chat_service.py
In [`app/services/chat_service.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/services/chat_service.py), the flow was:
1. Check `TOPIC_MAP` for a keyword match.
2. Query the knowledge base for relevant content.
3. **Always** call the Groq LLM regardless of whether step 1 or 2 produced any results.

When no topic matched and no KB content was found, the LLM was sent only the system prompt and the user message with **zero grounding context**, allowing it to freely use world knowledge to craft a response.

---

## 2. Files Changed
- [`app/prompts/prompts.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/prompts/prompts.py)
- [`app/services/chat_service.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/services/chat_service.py)

---

## 3. Code Changes

### [`app/prompts/prompts.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/prompts/prompts.py)

**a) Added STRICT DOMAIN RULES block at the top of BASE_SYSTEM_PROMPT:**
```diff
+STRICT DOMAIN RULES — READ THESE FIRST:
+- You may ONLY answer questions related to AstroVed, Vedic Astrology, Pujas, Horoscope,
+  Numerology, Compatibility, Temples, Spiritual Services, Birth Chart, Gemstones,
+  Muhurta, Predictions, Nakshatra, Dasha, Remedies, Mantras, Yantras, Zodiac Signs,
+  Rashi, and any other topic directly covered by AstroVed's services.
+- If the user asks about ANYTHING outside this domain (politics, sports, news, general knowledge,
+  celebrities, government, science, technology, geography, etc.), you MUST politely
+  decline and state that you only assist with AstroVed astrology services.
+- NEVER use your training knowledge to answer off-domain questions.
+- NEVER make up facts not present in the provided website content.
+- DO NOT answer questions like "Who is the Chief Minister of Tamil Nadu?",
+  "Who is Narendra Modi?", "What is IPL?", or any non-astrology question.
```

**b) Removed permissive rule that caused hallucinations:**
```diff
-Never refuse a question — if unsure, give general Vedic astrology guidance
```

**c) Added `OFF_DOMAIN_REPLY` and `OFF_DOMAIN_REPLY_TAMIL` constants:**
```python
OFF_DOMAIN_REPLY = (
    "I'm AstroVed.AI, and I specialise exclusively in Vedic Astrology, "
    "Pujas, Horoscopes, Birth Charts, Gemstones, Numerology, Compatibility, "
    "Muhurta, Predictions, and AstroVed's spiritual services. "
    "I'm not able to help with that question, but I'd love to guide you "
    "on anything related to astrology or AstroVed. ✨ What would you like to explore?"
)

OFF_DOMAIN_REPLY_TAMIL = (
    "நான் AstroVed.AI — வேத ஜோதிடம், பூஜைகள், ஜாதகம், ரத்தின கற்கள், "
    "எண் கணிதம், பொருத்தம், முகூர்த்தம் மற்றும் AstroVed சேவைகள் மட்டுமே "
    "பதிலளிக்கிறேன். இந்த கேள்விக்கு என்னால் உதவ இயலாது. "
    "ஜோதிடம் சம்பந்தமாக ஏதேனும் கேட்கலாம்! ✨"
)
```

---

### [`app/services/chat_service.py`](file:///Users/nivash/AV/AI_Chat_Bot/app/services/chat_service.py)

**a) Imported new constants:**
```diff
-from app.prompts.prompts import BASE_SYSTEM_PROMPT, TOPIC_FORCE_INSTRUCTION, LANGUAGE_INSTRUCTIONS
+from app.prompts.prompts import BASE_SYSTEM_PROMPT, TOPIC_FORCE_INSTRUCTION, LANGUAGE_INSTRUCTIONS, OFF_DOMAIN_REPLY, OFF_DOMAIN_REPLY_TAMIL
```

**b) Added off-domain guard before the LLM call:**
```python
# ── OFF-DOMAIN GUARD ─────────────────────────────────────────────────
# No topic match AND no knowledge-base content means the question is
# outside AstroVed's domain. Return a polite refusal without calling
# the LLM so it cannot hallucinate from world knowledge.
if not topic_label and not relevant_content:
    off_domain = OFF_DOMAIN_REPLY_TAMIL if detected_lang == "tamil" else OFF_DOMAIN_REPLY
    save_message(req.session_id, "assistant", off_domain)
    return {"reply": off_domain, "mode": "bot", "topic_url": None, "topic_label": None}
# ── END OFF-DOMAIN GUARD ─────────────────────────────────────────────
```

---

## 4. Defence-in-Depth Architecture

Two independent layers now block hallucinations:

| Layer | Where | What it does |
|-------|-------|-------------|
| **Layer 1 — Pre-LLM Guard** | `chat_service.py` | If no topic match AND no KB content: returns `OFF_DOMAIN_REPLY` instantly, never calls Groq LLM |
| **Layer 2 — System Prompt Domain Wall** | `prompts.py` | Even if the LLM is called, it is explicitly instructed to refuse off-domain questions and NEVER use world knowledge |

Layer 1 eliminates LLM cost and latency on off-domain questions. Layer 2 acts as a safety net for edge cases where KB content partially matches but the user question is still mostly off-domain.

---

## 5. Verification

### Off-Domain Questions (should return polite refusal)
| Question | Before | After |
|----------|--------|-------|
| Who is the Chief Minister of Tamil Nadu? | Hallucinated answer | ✅ Polite refusal |
| Who is Narendra Modi? | Hallucinated answer | ✅ Polite refusal |
| What is IPL? | Hallucinated answer | ✅ Polite refusal |
| What is the capital of France? | Hallucinated answer | ✅ Polite refusal |

### In-Domain Questions (should still work normally)
| Question | Expected Behaviour |
|----------|-------------------|
| What is my Moon sign? | ✅ Answered from KB / prompt |
| Tell me about Shukra puja | ✅ Answered from KB |
| What gemstone is good for Scorpio? | ✅ Answered from KB |
| What is Muhurta? | ✅ Answered from KB |
