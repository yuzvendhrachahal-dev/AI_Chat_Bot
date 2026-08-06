# AstroVed.AI Chatbot Refactor Progress

## Objective

Refactor the chatbot project into a modular, maintainable architecture while preserving 100% existing functionality.

Goals:

- No API endpoint changes
- No UI changes
- No database schema changes
- No business logic changes
- Improve maintainability
- Reduce main.py size
- Prepare for future modules such as Abandoned Cart

---

## Current Branch

refactor/chatbot-modularization

---

## Progress

### ✅ Step 1 – Project Structure

Status: Completed

Changes:
- Created app/
- Created app/config/
- Created app/database/
- Created app/prompts/
- Created app/services/
- Created app/routes/
- Created app/utils/
- Created templates/
- Created static/
- Created tests/
- Added required __init__.py files

Business Logic Changed:
No

Application Tested:
Pending

Commit:
Pending

### ✅ Step 2 – Configuration Extraction

Status: Completed

Objective:
Extract all application configuration and constants from `main.py` into a dedicated configuration module.

Changes:
- Created `app/config/settings.py`
- Moved environment variable loading (`load_dotenv()`)
- Moved `GROQ_API_KEY`
- Moved `SITE`
- Moved `HANDOFF_KEYWORDS`
- Updated `main.py` imports to use the centralized configuration module

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Pending

Commit:
Pending

Notes:
This refactor separates configuration from business logic, making environment management and future configuration updates easier while preserving existing functionality.

### ✅ Step 3 – SQLite Database Layer Extraction

Status: Completed

Objective:
Extract the entire SQLite database layer (connections, initialization, seed data, registrations, message history, agent console CRUD operations) from `main.py` into a modular service helper.

Changes:
- Created `app/database/database.py`
- Moved database connection creation and helper functions
- Moved `init_db()`
- Moved `seed_default_agents()`
- Moved `get_history()` and `save_message()`
- Extracted and encapsulated all agent session management queries (`create_or_update_session()`, `get_admin_users()`, `get_and_update_session_status()`, `get_session_poll_data()`, `get_agent_by_username()`, `get_active_agent_sessions()`, `get_session_messages()`, `claim_session()`, `touch_session()`, `close_session()`, `get_all_sessions()`, `get_waiting_or_active_sessions()`)
- Extracted and encapsulated local registration DB operations (`save_user_registration()`, `get_all_registrations()`)
- Imported database service helper functions in `main.py`

Business Logic Changed:
No

API Changes:
No

Database Changes:
No (schema and connection settings preserved 100%)

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

### ✅ Step 4 – Extract Prompt Management

Status: Completed

Objective:
Extract prompt templates and configurations from `main.py` into a dedicated prompts module.

Changes:
- Created `app/prompts/prompts.py`
- Moved `BASE_SYSTEM_PROMPT`
- Moved `TOPIC_FORCE_INSTRUCTION`
- Moved `LANGUAGE_INSTRUCTIONS`
- Updated `main.py` imports to use the centralized prompts module

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

Notes:
This refactor isolates LLM instructions from application control logic and endpoints, making it easier to modify prompt wording in the future without changing python code paths.

---

### ✅ Step 5 – Knowledge Base Service Extraction

Status: Completed

Objective:
Extract the knowledge base loading and semantic search functionality from `main.py` into a dedicated service.

Changes:
- Created `app/services/kb_service.py`
- Moved knowledge base loading
- Moved KB chunk initialization
- Moved semantic search functions
- Moved URL-specific search helpers
- Updated imports in `main.py`

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

Notes:
The knowledge base subsystem is now isolated into a reusable service without modifying search behaviour or chatbot responses.

### ✅ Step 6 – Language Detection Service Extraction

Status: Completed

Objective:
Extract language detection functionality from `main.py` into a dedicated reusable service.

Changes:
- Created `app/services/language_service.py`
- Moved `detect_language()`
- Moved language helper constants (if any)
- Updated imports in `main.py`

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

Notes:
Language detection is now isolated as an independent reusable service while preserving identical chatbot behaviour.

### ✅ Step 7 – Human Handoff Service Extraction

Status: Completed

Objective:
Extract CRM handoff detection and session management into a dedicated service.

Changes:
- Created `app/services/handoff_service.py`
- Moved `needs_handoff()`
- Moved `create_or_update_handoff()`
- Moved CRM helper functions
- Updated imports in `main.py`

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

Notes:
The CRM handoff workflow is now isolated into a dedicated service while preserving identical behaviour for chatbot-to-agent transitions.

### ✅ Step 8 – Chat Service Extraction

Status: Completed

Objective:
Extract the complete chatbot business logic from `main.py` into a dedicated chat service.

Changes:
- Created `app/services/chat_service.py`
- Moved chatbot request processing
- Moved conversation history preparation
- Moved prompt assembly
- Moved LLM request logic
- Moved response processing
- Updated `main.py` to delegate processing through `process_chat()`

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks)

Commit:
Pending

Notes:
The `/chat` endpoint is now a thin controller that delegates business logic to `chat_service.py`, significantly reducing complexity in `main.py` while preserving existing behaviour.

---

### ✅ Step 9 – Agent Service Extraction

Status: Completed

Objective:
Extract all Human Agent business logic from `main.py` into a dedicated service module.

Changes:
- Created `app/services/agent_service.py`
- Moved: agent authentication (`process_agent_login`)
- Moved: session polling helper (`process_poll_session`)
- Moved: SSE event stream builder (`build_agent_events_response`)
- Moved: active session retrieval (`process_agent_sessions`)
- Moved: full session history view (`process_agent_all_sessions`)
- Moved: per-session message history (`process_agent_history`)
- Moved: claim session logic (`process_agent_claim`)
- Moved: agent reply processing (`process_agent_reply`)
- Moved: session close logic (`process_agent_close`)
- Updated `main.py` imports — removed agent-specific DB imports now internal to agent_service
- All route decorators remain in `main.py`; each route body is a single delegation call

Business Logic Changed:
No

API Changes:
No

Database Changes:
No

UI Changes:
No

Application Tested:
Yes (successfully verified via Python import checks — 690 KB chunks loaded)

Commit:
Pending

Notes:
All agent operations are now isolated in `app/services/agent_service.py`.
`main.py` route handlers are thin one-liners that delegate to the service layer.

---

## Upcoming Steps

- Step 10 – Extract API Routes
- Step 11 – Move HTML Templates
- Step 12 – Move Static Assets (JS/CSS)
- Step 13 – Scheduler Cleanup
- Step 14 – Scraper Cleanup
- Step 15 – Testing & Validation
- Step 16 – Final Documentation

---

## Notes

This refactor is intentionally incremental.

Each step must preserve existing functionality.

The chatbot, agent dashboard, Render deployment, and APIs must continue working after every completed step.
