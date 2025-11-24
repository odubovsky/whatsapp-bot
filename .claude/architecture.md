# WhatsApp Bot - Architecture Design

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     WhatsApp Bot Service                        │
│                     (Single Python Process)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────┐               │
│  │ WhatsApp Client  │◄────►│  Event Handler   │               │
│  │  (QR Auth)       │      │  (Message Recv)  │               │
│  └────────┬─────────┘      └────────┬─────────┘               │
│           │                          │                          │
│           │                          ▼                          │
│           │                  ┌──────────────┐                  │
│           │                  │   Database   │                  │
│           │                  │   (SQLite)   │                  │
│           │                  └──────┬───────┘                  │
│           │                         │                          │
│           │                         │                          │
│  ┌────────▼─────────┐      ┌───────▼────────┐                │
│  │ Message Sender   │◄─────│ Polling Agent  │                │
│  └──────────────────┘      │ + LLM Client   │                │
│                             └───────┬────────┘                │
│                                     │                          │
│                                     ▼                          │
│                           ┌──────────────────┐                │
│                           │ Perplexity API   │                │
│                           └──────────────────┘                │
│                                                                 │
│  ┌──────────────────────────────────────────────┐             │
│  │         Background Tasks                     │             │
│  │  • Vitality Checker (daily)                 │             │
│  │  • Rotation Cleanup (periodic)              │             │
│  │  • Session Expiry (periodic)                │             │
│  └──────────────────────────────────────────────┘             │
│                                                                 │
│  ┌──────────────────────────────────────────────┐             │
│  │         Configuration                        │             │
│  │  • .env (API keys)                          │             │
│  │  • app.json (entities, prompts, settings)  │             │
│  └──────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ WhatsApp Servers │
                    └──────────────────┘
```

## Component Design

### 1. Main Entry Point (main.py)

**Responsibilities:**
- Parse CLI arguments
- Load configuration
- Initialize database
- Start WhatsApp client
- Orchestrate background tasks
- Handle graceful shutdown

**Key Functions:**
```python
def main():
    """Entry point"""
    - Parse CLI args
    - Load config
    - Setup logging
    - Initialize database
    - Connect WhatsApp
    - Send startup validation
    - Start background tasks
    - Run event loop

async def run_service(args):
    """Main service loop"""
    - Create async tasks:
      - WhatsApp event listener
      - Message polling agent
      - Vitality checker
      - Rotation cleanup
      - Session expiry cleanup
    - Wait for tasks
    - Handle shutdown

def handle_shutdown(signum, frame):
    """Graceful shutdown"""
    - Stop all tasks
    - Close database
    - Disconnect WhatsApp
    - Exit cleanly
```

### 2. Configuration Manager (config.py)

**Responsibilities:**
- Load `.env` and `app.json`
- Validate configuration
- Provide typed access to config
- Build entity lookup maps

**Key Classes:**
```python
@dataclass
class MonitoredEntity:
    type: Literal["user", "group"]
    jid: Optional[str]
    phone: Optional[str]
    name: str
    prompt: str
    persona: str

class Config:
    """Singleton configuration"""
    - perplexity_api_key: str
    - whatsapp: WhatsAppConfig
    - monitored_entities: List[MonitoredEntity]
    - polling: PollingConfig
    - rotation: RotationConfig
    - session_memory: SessionMemoryConfig
    - vitality: VitalityConfig
    - perplexity: PerplexityConfig

    - get_entity_by_jid(jid) -> MonitoredEntity
    - is_monitored(jid) -> bool
    - get_prompt_for_entity(jid) -> str
```

### 3. WhatsApp Client (whatsapp_client.py)

**Responsibilities:**
- QR code authentication
- Connection management
- Event handling (message received)
- Message sending
- Session persistence

**Key Classes:**
```python
class WhatsAppClient:
    """WhatsApp connection manager"""

    def __init__(self, config, database):
        self.config = config
        self.db = database
        self.client = None  # WhatsApp library client

    async def connect(self, force_qr=False):
        """Connect with QR auth if needed"""
        - Load session from database
        - If session exists: auto-connect
        - If no session or force_qr: show QR
        - Save session to database

    def on_message(self, message):
        """Handle incoming message"""
        - Extract: msg_id, chat_jid, sender, content, timestamp
        - Check if monitored entity
        - If monitored: store in database
        - If not: ignore

    async def send_message(self, chat_jid, content):
        """Send message to WhatsApp"""
        - Format message
        - Send via client
        - Log result

    def disconnect(self):
        """Clean disconnect"""
```

**Integration with Library:**
```python
# Using yowsup2 or similar
from yowsup import layers, env
from yowsup.stacks import YowStackBuilder

# Event handler registration
client.on('message', self.on_message)
client.on('connected', self.on_connected)
client.on('disconnected', self.on_disconnected)
```

### 4. Database Manager (database.py)

**Responsibilities:**
- SQLite operations
- Message CRUD
- Session memory management
- Rotation cleanup
- WhatsApp session storage

**Key Classes:**
```python
class Database:
    """SQLite database manager"""

    def initialize(self):
        """Create tables and indexes"""

    # Message operations
    def insert_message(self, msg_id, chat_jid, sender, content, timestamp, is_from_me)
    def get_unprocessed_messages(self, limit) -> List[Dict]
    def get_messages_for_chat(self, chat_jid, limit) -> List[Dict]
    def cleanup_old_messages(self) -> int

    # Session memory operations
    def get_or_create_session(self, user_jid, chat_jid) -> Dict
    def update_session_context(self, session_id, context)
    def get_session_context(self, session_id) -> List[Dict]
    def cleanup_expired_sessions(self) -> int

    # WhatsApp session operations
    def save_whatsapp_session(self, session_data)
    def load_whatsapp_session(self) -> Optional[str]
    def clear_whatsapp_session(self)

    # Utility
    def get_stats(self) -> Dict
```

**Database Schema:**
```sql
-- Messages with rotation
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    chat_jid TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT,
    timestamp TIMESTAMP NOT NULL,
    is_from_me BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_timestamp (chat_jid, timestamp DESC),
    INDEX idx_created_at (created_at)
);

-- Session memory with expiry
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_jid TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    context TEXT,  -- JSON array
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    INDEX idx_expires_at (expires_at),
    INDEX idx_user_chat (user_jid, chat_jid)
);

-- WhatsApp device session
CREATE TABLE whatsapp_device (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    session_data TEXT NOT NULL,
    last_connected TIMESTAMP NOT NULL
);
```

### 5. Message Agent (message_agent.py)

**Responsibilities:**
- Poll database for new messages
- Load session memory
- Query Perplexity API
- Send responses
- Update session memory
- Avoid feedback loops by tracking the last bot response per chat and skipping echoes of that response coming back from the bridge
- Normalize/alias sender IDs (raw and @s.whatsapp.net) when fetching sessions to preserve context even if the bridge changes sender format
- Optional debug mode per entity (and self) sends a pre-LLM debug message with the user entry, augmented prompt, and persona
- Config auto-reload: hash of app.json stored in DB; message processing checks for changes and reloads config on the fly

**Key Classes:**
```python
class MessageAgent:
    """AI response agent"""

    def __init__(self, config, database, whatsapp_client):
        self.config = config
        self.db = database
        self.whatsapp = whatsapp_client
        self.perplexity = PerplexityClient(config.perplexity_api_key)

    async def run(self):
        """Main polling loop"""
        while True:
            await asyncio.sleep(self.config.polling.interval_seconds)
            await self.process_new_messages()

    async def process_new_messages(self):
        """Process unprocessed messages"""
        - Get unprocessed messages from DB
        - For each message:
            - Get entity config (prompt, persona)
            - Load session memory
            - Build prompt with context
            - Query Perplexity
            - Send response
            - Update session memory

    async def query_llm(self, message, context, entity) -> str:
        """Query Perplexity API"""
        - Build messages array:
            [
                {"role": "system", "content": entity.prompt},
                ...context...,
                {"role": "user", "content": message}
            ]
        - Call Perplexity API
        - Return response

class PerplexityClient:
    """Perplexity API client"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"

    async def chat_completion(self, messages, model, temperature, max_tokens) -> str:
        """Call chat completion API"""
```

### 6. Vitality Checker (vitality_checker.py)

**Responsibilities:**
- Schedule daily health check
- Send vitality message to self
- Handle timezone-aware scheduling

**Key Classes:**
```python
class VitalityChecker:
    """Daily health check scheduler"""

    def __init__(self, config, whatsapp_client):
        self.config = config
        self.whatsapp = whatsapp_client
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start scheduler"""
        if not self.config.vitality.enabled:
            return

        # Schedule daily at configured time
        self.scheduler.add_job(
            self.send_vitality_message,
            trigger='cron',
            hour=self.config.vitality.time.split(':')[0],
            minute=self.config.vitality.time.split(':')[1],
            timezone=self.config.vitality.get_timezone()
        )
        self.scheduler.start()

    async def send_vitality_message(self):
        """Send health check message"""
        my_jid = f"{self.config.whatsapp.phone_number}@s.whatsapp.net"
        await self.whatsapp.send_message(
            my_jid,
            self.config.vitality.message
        )
```

## Data Flow

### Message Receiving Flow

```
1. WhatsApp Server
   ↓ (WebSocket event)
2. WhatsApp Client (on_message handler)
   ↓ (check if monitored)
3. Database (insert_message)
   ↓ (stored)
4. [Message waiting for processing]
```

### Message Processing Flow

```
1. Message Agent (polling loop)
   ↓ (get unprocessed messages)
2. Database (get_unprocessed_messages)
   ↓ (load session)
3. Database (get_or_create_session)
   ↓ (load context)
4. Database (get_session_context)
   ↓ (build prompt)
5. Perplexity API (chat completion)
   ↓ (get response)
6. WhatsApp Client (send_message)
   ↓ (update session)
7. Database (update_session_context)
   ↓ (mark processed)
8. [Complete]
```

### Session Memory Lifecycle

```
1. New message arrives
   ↓
2. Check for existing session (user_jid + chat_jid)
   ↓
3. If exists and not expired:
   │  → Load session
   │  → Add to context
   │  → Return session_id
   ↓
4. If not exists or expired:
   │  → Create new session
   │  → Calculate expiry based on mode
   │  → Empty context
   │  → Return new session_id
   ↓
5. Process message with context
   ↓
6. Update session with response
   ↓
7. Continue until expiry
```

### Rotation Cleanup Flow

```
1. Background task (periodic)
   ↓
2. Calculate cutoff date (now - retention_days)
   ↓
3. Delete messages WHERE created_at < cutoff
   ↓
4. Delete sessions WHERE expires_at < now
   ↓
5. Log counts
   ↓
6. Sleep until next interval
```

## Concurrency Model

### Async Event Loop

```python
async def main():
    # Create concurrent tasks
    tasks = [
        asyncio.create_task(whatsapp_client.listen()),
        asyncio.create_task(message_agent.run()),
        asyncio.create_task(rotation_cleanup_task()),
        asyncio.create_task(session_cleanup_task()),
    ]

    # Start vitality checker (APScheduler)
    vitality_checker.start()

    # Wait for all tasks
    await asyncio.gather(*tasks)
```

### Task Responsibilities

| Task | Type | Interval | Purpose |
|------|------|----------|---------|
| WhatsApp Listener | Event-driven | Continuous | Receive messages |
| Message Agent | Poll | 5s (configurable) | Process messages |
| Rotation Cleanup | Timer | 24h (configurable) | Delete old messages |
| Session Cleanup | Timer | 1h (fixed) | Delete expired sessions |
| Vitality Checker | Cron | Daily at time | Send health check |

## Error Handling Strategy

### Connection Errors
- WhatsApp disconnect → Auto-reconnect with exponential backoff
- Perplexity API error → Log, skip message, continue
- Database lock → Retry with timeout

### Data Errors
- Invalid message format → Log, skip, continue
- Missing entity config → Log, skip, continue
- Session expiry calculation error → Use default (24h)

### Configuration Errors
- Missing API key → Exit with error
- Invalid JSON → Exit with error
- Invalid timezone → Exit with error

### Runtime Errors
- Unhandled exception → Log, attempt recovery
- Memory issues → Log warning
- Disk full → Log error, pause rotation

## Security Considerations

### Secrets Management
- API keys in `.env` (not committed)
- WhatsApp session encrypted in database
- No logging of sensitive data

### Input Validation
- Validate all config values at startup
- Sanitize message content before storage
- Validate JIDs before database operations

### Database Security
- Use parameterized queries (prevent SQL injection)
- WAL mode for consistency
- Regular backups recommended

## Performance Optimization

### Database
- Indexes on common queries (chat_jid, timestamp)
- WAL mode for concurrent access
- Connection pooling (single connection, thread-safe)
- Periodic VACUUM for optimization

### API Calls
- Async HTTP client (httpx)
- Retry logic with backoff
- Timeout configuration
- Rate limit handling

### Memory Management
- Limit session context size (e.g., last 10 messages)
- Cleanup old data regularly
- Stream large queries
- Efficient JSON serialization

## Deployment Architecture

### Cloud VPS Deployment

```
┌─────────────────────────────────────┐
│         Linux VPS (Cloud)           │
├─────────────────────────────────────┤
│                                     │
│  systemd                            │
│    ↓                                │
│  whatsapp-bot.service               │
│    ↓                                │
│  /opt/whatsapp-bot/run.sh          │
│    ↓                                │
│  venv/bin/python main.py            │
│                                     │
│  Persistent Storage:                │
│  • store/whatsapp_bot.db           │
│  • logs/whatsapp-bot.log           │
│  • .env (secrets)                  │
│  • app.json (config)               │
│                                     │
└─────────────────────────────────────┘
```

### Process Management
- Systemd for service management
- Auto-restart on failure
- Logs to systemd journal + file
- Graceful shutdown on stop

### Monitoring
- Log file rotation
- Database statistics endpoint
- Health check via vitality messages
- Process status via systemd
