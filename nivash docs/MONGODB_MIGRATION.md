# Overview

The application was migrated from SQLite to MongoDB to transition the database architecture to a production-ready, cloud-compatible database system. SQLite is file-based and not suitable for distributed, stateless cloud deployments (such as Render) where disk persistence is not guaranteed across restarts or scaling events. MongoDB provides a scalable, document-oriented database that supports concurrent client operations and integrates seamlessly with cloud environments.

# Previous Architecture

In the previous architecture, SQLite was used as the primary database storage. It stored:
- **users**: Customer profile information and identification data.
- **sessions**: Chat session details, current status (bot, waiting, active, closed), and metadata.
- **messages**: The raw messages exchanged between users, bot, and support agents.
- **agents**: Support agent profiles, login credentials, and display names.

# New Architecture

Under the new architecture, MongoDB hosts the chat-specific operational data, while registration data integrates with external services.

MongoDB stores:
- **users**
- **sessions**
- **messages**
- **agents**

The system coordinates database writes as follows:

AstroVed Registration API
↓
Microsoft SQL Server (External synchronization for customer registrations)

Chat History
↓
MongoDB (Operational store for real-time messaging data)

# Collections

The MongoDB database contains the following collections:

### users
Stores user details registered via the widget. Each document maps a session to a user's name, email, phone, and registration status.

### sessions
Tracks the state of conversations, including the assigned agent, issue type, priority levels, session state (e.g., `bot`, `waiting`, `active`, `closed`), and timestamps for updates.

### messages
Contains all individual chat logs. Each message document records the corresponding `session_id`, the sender's `role` (e.g., `user`, `assistant`, `system`), message content, and sequential message IDs.

### agents
Stores credentials and identifiers for support agents, including usernames, hashed passwords, and display names used to claim chat queues.

# Benefits

- **Scalability**: MongoDB easily handles high concurrent reads and writes, preventing database locking issues associated with file-based databases under load.
- **Cloud deployment**: Highly optimized for stateless container architectures.
- **Performance**: High-throughput indexing on operational keys like `session_id`.
- **Atlas compatibility**: Seamlessly integrates with managed services like MongoDB Atlas for clustering, backups, and security monitoring.
- **Render compatibility**: Eliminates the need for persistent disk mounts on hosting providers like Render.
- **No local database dependency**: Decoupled database host allows server instances to scale up or down without local storage sync issues.

# Files Modified

The following files were involved in the migration process:
- `app/database/mongodb.py` (New database connection and query handler module)
- `app/database/database_sqlite_backup.py` (Legacy SQLite connector retained as backup)
- `main.py` (Startup lifespan updated to initialize MongoDB and seed default agents)
- `app/routes/chat.py` (Updated queries to import and utilize the MongoDB connector)
- `app/routes/admin.py` (Admin metrics queries ported to MongoDB collection aggregations)
- `app/services/chat_service.py` (LLM chat interactions and session tracking migrated to MongoDB)
- `app/services/agent_service.py` (Agent-claim events and session updates refactored for MongoDB operations)

Migration Status

✅ Completed
