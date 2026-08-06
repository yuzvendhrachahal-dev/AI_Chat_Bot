from groq import Groq
from fastapi import HTTPException

from app.config.settings import GROQ_API_KEY, SITE
from app.database.database import get_and_update_session_status, save_message, get_history
from app.services.handoff_service import create_or_update_handoff, needs_handoff
from app.services.language_service import detect_language
from app.prompts.prompts import BASE_SYSTEM_PROMPT, TOPIC_FORCE_INSTRUCTION, LANGUAGE_INSTRUCTIONS
from app.services.kb_service import search_knowledge, search_knowledge_for_url
from topic_map import TOPIC_MAP, match_topic

client = Groq(api_key=GROQ_API_KEY)

async def process_chat(req):
    try:
        status = get_and_update_session_status(req.session_id)
        if status == "with_agent":
            save_message(req.session_id, "user", req.message)
            return {"reply": None, "mode": "with_agent"}
        history = get_history(req.session_id)
        save_message(req.session_id, "user", req.message)
        if needs_handoff(req.message):
            create_or_update_handoff(req.session_id, req.user_name, req.user_email, req.user_phone, "general", "normal")
            reply = "I understand this needs special attention. Connecting you with our specialist team now — they'll be with you shortly! 🎧"
            save_message(req.session_id, "assistant", reply)
            return {"reply": reply, "mode": "handoff_triggered", "topic_url": None, "topic_label": None}
        
        detected_lang = detect_language(req.message)
        topic_url, topic_label = match_topic(req.message)
        topic_info = None
        if topic_label:
            for _k, _v in TOPIC_MAP.items():
                if _v["label"] == topic_label:
                    topic_info = _v
                    break

        system_content = BASE_SYSTEM_PROMPT + LANGUAGE_INSTRUCTIONS.get(detected_lang, LANGUAGE_INSTRUCTIONS["english"])

        if topic_info:
            url_fragment = topic_info["url"].replace(SITE, "").strip("/").split("/")[0]
            kb_content = search_knowledge_for_url(url_fragment) or search_knowledge(req.message, top_k=2)
            if not kb_content:
                kb_content = f"[Page: {topic_info['label']}]\nURL: {topic_info['url']}\n{topic_info.get('fallback','')}\n"
            system_content += TOPIC_FORCE_INSTRUCTION.format(label=topic_info["label"], content=kb_content)
        else:
            relevant_content, kb_matches = search_knowledge(req.message, top_k=3)
            if relevant_content:
                system_content += f"\n\n=== RELEVANT WEBSITE CONTENT ===\n{relevant_content}\n=== END CONTENT ==="
            if not topic_url and kb_matches:
                topic_url = kb_matches[0]["url"]
                topic_label = kb_matches[0]["title"]

        messages = [{"role": "system", "content": system_content}]
        for h in history:
            if h["role"] in ("user", "assistant"):
                messages.append({"role": h["role"], "content": str(h["content"])})
        messages.append({"role": "user", "content": str(req.message)})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=450,
            temperature=0.45,
            top_p=0.9,
        )
        
        reply = response.choices[0].message.content
        save_message(req.session_id, "assistant", reply)
        return {"reply": reply, "mode": "bot", "topic_url": topic_url, "topic_label": topic_label}
    except Exception as e:
        print(f"ERROR in /chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
