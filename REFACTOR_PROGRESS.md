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

## Upcoming Steps

- Step 5 – Extract Knowledge Base Service
- Step 6 – Extract Language Detection Service
- Step 7 – Extract Human Handoff Service
- Step 8 – Extract Chat Service
- Step 9 – Extract Agent Service
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
