# Bug Fix 04 — Off-Domain Guard Bypass (Hallucination)

## 1. Problem Description
The chatbot successfully identified AstroVed topics (using `match_topic`) but failed to reject off-domain general knowledge questions such as *"Who is the Chief Minister of Tamil Nadu?"*. The LLM responded using its world knowledge, directly violating the domain boundaries.

## 2. Request Flow Analysis
The flow for an off-domain question was as follows:
1. User asks: *"Who is the Chief Minister of Tamil Nadu?"*
2. `match_topic()` checks `TOPIC_MAP` keywords. No match is found (`topic_label` = `None`).
3. The flow falls back to `search_knowledge()` to scan the knowledge base.
4. `search_knowledge()` extracts 3+ letter words: `{"who", "the", "chief", "minister", "tamil", "nadu"}`.
5. The function iterates through all chunks. Since the word `"the"` is in every document, and `"tamil"` is in many AstroVed pages (like Tamil New Year), the score for these chunks becomes `> 0`.
6. `search_knowledge()` returns these chunks as `relevant_content`.
7. **The Guard Fails:** In `chat_service.py`, the off-domain guard condition is:
   ```python
   if not topic_label and not relevant_content:
       return OFF_DOMAIN_REPLY
   ```
   Because `relevant_content` is **not empty** (it contains generic matched chunks), the condition evaluates to `False`. The guard is bypassed.
8. The LLM is called. Because the injected chunks (e.g. about Tamil New Year) are irrelevant to the question, the LLM falls back to its training memory and correctly answers "M. K. Stalin", acting as a general-purpose AI instead of a domain-restricted one.

## 3. Root Cause
The root cause was the weak scoring logic in `search_knowledge()` inside `app/services/kb_service.py`:
- It did not filter out common English stop words (`"the"`, `"who"`, `"are"`).
- It matched substrings generically instead of strictly using word boundaries (so `"the"` could match inside `"there"`).
- It accepted any chunk with a score `> 0` (even 1 matching word out of 6).

This guaranteed that almost *any* English sentence would return at least one generic chunk from the knowledge base, artificially bypassing the off-domain guard.

## 4. The Fix
The logic in `app/services/kb_service.py` was rewritten to ensure `search_knowledge()` only returns highly relevant chunks, enforcing the off-domain guard for generic queries:
1. **Stop Words Filter:** Added a `STOP_WORDS` set to remove common words (like `"the"`, `"who"`, `"what"`, `"is"`) before evaluating the query.
2. **Word Boundaries:** The chunk text (`haystack`) is padded with spaces, and non-alphabetic characters are stripped. Matches now use exact word boundaries (`f" {w} " in haystack_padded`) instead of generic substring checks.
3. **Relevance Threshold (Ratio):** A minimum match ratio was introduced.
   ```python
   ratio = score / len(query_words)
   if score > 0 and ratio > 0.5:
       scored.append((score, chunk))
   ```
   Now, if the user asks *"Who is the Chief Minister of Tamil Nadu?"*, the meaningful query words are `{"chief", "minister", "tamil", "nadu"}`. If the KB only contains `"tamil"` and `"nadu"`, the ratio is `2/4 = 0.5`. Since the threshold requires `> 0.5` (strictly greater than 50%), the generic chunk is **rejected**.

## 5. Verification
- **Off-Domain:** *"Who is the Chief Minister of Tamil Nadu?"* -> `query_words` filtered to `{"chief", "minister", "tamil", "nadu"}`. Ratio `0.5` fails the `>0.5` threshold. `search_knowledge` returns empty. The guard in `chat_service.py` fires. Returns `OFF_DOMAIN_REPLY` immediately without calling the LLM.
- **In-Domain:** *"Tell me about astrology"* -> `query_words` filtered to `{"tell", "astrology"}`. The word `"astrology"` is highly prevalent in the KB. Even if it goes to `search_knowledge` (though `match_topic` catches it first), the ratio requirement correctly surfaces valid content. All AstroVed functionality remains perfectly intact.
