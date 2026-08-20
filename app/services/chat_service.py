import json
from groq import Groq
from fastapi import HTTPException

from app.config.settings import GROQ_API_KEY, SITE, GROQ_MODEL
from app.database.mongodb import (
    get_and_update_session_status,
    save_message,
    get_history,
    create_or_update_handoff
)
from app.services.handoff_service import needs_handoff
from app.services.language_service import detect_language
from app.prompts.prompts import BASE_SYSTEM_PROMPT, TOPIC_FORCE_INSTRUCTION, LANGUAGE_INSTRUCTIONS, OFF_DOMAIN_REPLY, OFF_DOMAIN_REPLY_TAMIL
from app.services.kb_service import search_knowledge, search_knowledge_for_url
from app.config.topic_map import TOPIC_MAP, match_topic

client = Groq(api_key=GROQ_API_KEY)

# ── Generic High-Quality AstroVed Responses ───────────────────────────────────

GENERIC_TOPIC_RESPONSES = {
    "compatibility": (
        "Discover the harmony in your relationship with AstroVed's Horoscope Compatibility Match. "
        "Our Vedic experts analyze planetary alignments to evaluate the compatibility between you and your partner across various life aspects. "
        "Understanding these cosmic dynamics can help you navigate challenges and strengthen your bond.\n\n"
        "**Benefits:**\n"
        "• Gain deep insights into relationship dynamics.\n"
        "• Identify areas of harmony and potential conflict.\n"
        "• Receive Vedic remedies to enhance mutual understanding.\n\n"
        "Ready to explore your cosmic connection? Click the link below to get started!"
    ),
    "horoscope": (
        "Stay ahead of the planetary influences with AstroVed's Today's Horoscope. "
        "Our daily readings provide you with essential guidance based on your Moon Sign, helping you navigate your day with confidence. "
        "Whether it's career, love, or health, the stars have a message for you.\n\n"
        "**Benefits:**\n"
        "• Plan your day with cosmic foresight.\n"
        "• Avoid potential pitfalls and embrace opportunities.\n"
        "• Align your actions with favorable planetary hours.\n\n"
        "Check your daily horoscope below to see what the stars have in store!"
    ),
    "birth_chart": (
        "Unlock the secrets of your destiny with a Free Birth Chart from AstroVed. "
        "Your birth chart is a unique cosmic blueprint detailing the positions of the planets at the exact moment of your birth. "
        "It holds the key to understanding your personality, strengths, and life's purpose.\n\n"
        "**Benefits:**\n"
        "• Discover your true potential and hidden talents.\n"
        "• Understand your life's major transits and periods.\n"
        "• Empower yourself with self-knowledge for better decision-making.\n\n"
        "Generate your free birth chart today and embark on a journey of self-discovery!"
    ),
    "gemstone": (
        "Enhance your cosmic luck with AstroVed's Gemstone Recommendation. "
        "In Vedic astrology, gemstones act as powerful conduits for planetary energies, capable of bringing balance and prosperity to your life. "
        "Wearing the right gemstone can mitigate negative influences and amplify positive planetary vibrations.\n\n"
        "**Benefits:**\n"
        "• Attract success, health, and prosperity.\n"
        "• Harmonize planetary afflictions in your chart.\n"
        "• Experience emotional and spiritual well-being.\n\n"
        "Find your lucky gemstone and invite positive energy into your life today!"
    ),
    "numerology": (
        "Decode the hidden vibrations of your life with AstroVed's Numerology Reading. "
        "Numbers govern the universe, and your birth date and name carry specific numerical frequencies that shape your destiny. "
        "Our numerology service helps you understand these vibrations to align with your true path.\n\n"
        "**Benefits:**\n"
        "• Uncover your Life Path and Destiny numbers.\n"
        "• Find the most auspicious names for yourself or your business.\n"
        "• Optimize your timing for major life events.\n\n"
        "Explore the power of your numbers and align with your destiny!"
    ),
    "muhurta": (
        "Ensure success in your endeavors with AstroVed's Electional Astrology (Muhurta). "
        "Starting a significant event—like a wedding, business launch, or housewarming—at an auspicious time aligns your actions with favorable cosmic energies. "
        "A good Muhurta can be the foundation for long-term prosperity and happiness.\n\n"
        "**Benefits:**\n"
        "• Maximize the chances of success for important events.\n"
        "• Minimize obstacles and negative influences.\n"
        "• Harness the best planetary alignments for your specific purpose.\n\n"
        "Find the perfect time for your next big step with our Muhurta service!"
    )
}

def detect_astrology_intent(message: str, matched_label: str) -> str:
    msg = message.lower()
    label = (matched_label or "").lower()
    
    if "compatibility" in msg or "matching" in msg or "milan" in msg or "partner match" in msg or "horoscope matching" in label or "compatibility" in label:
        return "compatibility"
    if "horoscope" in msg or "rashi" in msg or "moon sign" in msg or "daily horoscope" in label:
        if "compatibility" not in msg and "matching" not in msg and "match" not in msg:
            return "horoscope"
    if "birth chart" in msg or "natal chart" in msg or "kundli" in msg or "kundali" in msg or "free birth chart" in label:
        return "birth_chart"
    if "gemstone" in msg or "lucky stone" in msg or "gem recommendation" in label:
        return "gemstone"
    if "numerology" in msg or "lucky number" in msg or "life path" in msg or "numerology" in label:
        return "numerology"
    if "muhurta" in msg or "muhurat" in msg or "auspicious time" in msg or "electional" in label:
        return "muhurta"
        
    return None

# ── Main Chat Processing ───────────────────────────────────────────────────────

async def process_chat(req):
    try:
        status = get_and_update_session_status(req.session_id)
        if status in ("with_agent", "waiting"):
            save_message(req.session_id, "user", req.message)
            return {"reply": None, "mode": "with_agent"}
            
        history = get_history(req.session_id)
        save_message(req.session_id, "user", req.message)
        
        if needs_handoff(req.message):
            reply = "I don't have access to customer account or order information.\n\nOur customer support team can assist you."
            save_message(req.session_id, "assistant", reply)
            return {"reply": reply, "mode": "support_card", "topic_url": None, "topic_label": None}
            
        detected_lang = detect_language(req.message)
        topic_url, topic_label = match_topic(req.message)
        
        intent = detect_astrology_intent(req.message, topic_label)
        if intent and intent in GENERIC_TOPIC_RESPONSES:
            reply = GENERIC_TOPIC_RESPONSES[intent]
            save_message(req.session_id, "assistant", reply)
            return {"reply": reply, "mode": "bot", "topic_url": topic_url, "topic_label": topic_label}

        # Fallback to general LLM logic
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

            if not topic_label and not relevant_content:
                off_domain = OFF_DOMAIN_REPLY_TAMIL if detected_lang == "tamil" else OFF_DOMAIN_REPLY
                save_message(req.session_id, "assistant", off_domain)
                return {"reply": off_domain, "mode": "bot", "topic_url": None, "topic_label": None}

        # NEVER HALLUCINATE ASTROLOGY DATA (Constraint enforcement via system prompt)
        astrology_guard = (
            "\n\nCRITICAL SAFETY RULES:\n"
            "1. You are forbidden to invent or assume any zodiac signs, moon signs, ascendants, birth charts, gemstone recommendations, numerology numbers, dashas, nakshatras, or horoscope predictions for the user.\n"
            "2. Do not fabricate personalized astrology readings.\n"
            "3. If asked about a personal astrology profile, provide a general, high-quality, friendly introduction to the AstroVed service that handles it, without generating a reading.\n"
            "4. Speak as a helpful guide representing AstroVed."
        )
        system_content += astrology_guard

        messages = [{"role": "system", "content": system_content}]
        for h in history:
            if h["role"] in ("user", "assistant"):
                messages.append({"role": h["role"], "content": str(h["content"])})
        messages.append({"role": "user", "content": str(req.message)})

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=450,
                temperature=0.45,
                top_p=0.9,
            )
        except Exception as model_err:
            print(f"ERROR calling Groq model {GROQ_MODEL}: {str(model_err)}")
            reply = "I'm sorry, but my AI model is currently unavailable or returning an error. Please try again later."
            save_message(req.session_id, "assistant", reply)
            return {"reply": reply, "mode": "bot", "topic_url": topic_url, "topic_label": topic_label}
        
        reply = response.choices[0].message.content
        save_message(req.session_id, "assistant", reply)
        return {"reply": reply, "mode": "bot", "topic_url": topic_url, "topic_label": topic_label}
    except Exception as e:
        print(f"ERROR in /chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
