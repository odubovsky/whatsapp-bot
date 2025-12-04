# WhatsApp Bot - Database Design

## Database Overview

**Type:** SQLite
**Location:** `store/whatsapp_bot.db`
**Mode:** WAL (Write-Ahead Logging) for better concurrency
**Access:** Single connection, thread-safe

## Schema Design

### Table: messages

**Purpose:** Store all messages from monitored entities with configurable retention

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,                    -- WhatsApp message ID (unique)
    chat_jid TEXT NOT NULL,                 -- Chat identifier (group or user)
    sender TEXT NOT NULL,                   -- Sender JID (who sent the message)
    content TEXT,                           -- Message text content
    timestamp TIMESTAMP NOT NULL,           -- Message sent time (from WhatsApp)
    is_from_me BOOLEAN NOT NULL,           -- True if sent by bot, False if received
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- DB insert time
);

CREATE INDEX idx_chat_timestamp ON messages(chat_jid, timestamp DESC);
CREATE INDEX idx_created_at ON messages(created_at);
CREATE INDEX idx_sender ON messages(sender);
```

**Fields Explained:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | TEXT | WhatsApp message ID | `3EB0ABC123DEF456` |
| chat_jid | TEXT | Group JID or user JID | `123456789-1234567890@g.us` |
| sender | TEXT | Sender's JID | `1234567890@s.whatsapp.net` |
| content | TEXT | Message text | `Hello, how are you?` |
| timestamp | TIMESTAMP | When message sent | `2024-01-15 14:30:00` |
| is_from_me | BOOLEAN | Direction flag | `0` (received), `1` (sent) |
| created_at | TIMESTAMP | When stored in DB | `2024-01-15 14:30:01` |

**Indexes:**
- `idx_chat_timestamp`: Fast queries for chat history (most common operation)
- `idx_created_at`: Efficient rotation cleanup
- `idx_sender`: Fast lookup by sender

**Rotation Logic:**
- Delete rows WHERE `created_at < (now - retention_days)`
- Runs every `cleanup_interval_hours`
- Keeps database lightweight

### Table: chat_sessions

**Purpose:** Store conversation memory with configurable expiry

```sql
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,            -- Unique session identifier
    user_jid TEXT NOT NULL,                 -- User who owns this session
    chat_jid TEXT NOT NULL,                 -- Chat context (group or DM)
    context TEXT,                           -- JSON array of conversation history
    created_at TIMESTAMP NOT NULL,          -- Session start time
    expires_at TIMESTAMP NOT NULL,          -- Calculated expiry time
    last_activity TIMESTAMP NOT NULL        -- Last message time
);

CREATE INDEX idx_expires_at ON chat_sessions(expires_at);
CREATE INDEX idx_user_chat ON chat_sessions(user_jid, chat_jid);
CREATE INDEX idx_last_activity ON chat_sessions(last_activity DESC);
```

**Fields Explained:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| session_id | TEXT | Unique ID | `1234567890@s.whatsapp.net_123...@g.us_1705330200` |
| user_jid | TEXT | Session owner | `1234567890@s.whatsapp.net` |
| chat_jid | TEXT | Chat context | `123456789-1234567890@g.us` |
| context | TEXT | JSON conversation | `[{"role": "user", "content": "..."}]` |
| created_at | TIMESTAMP | Session created | `2024-01-15 10:00:00` |
| expires_at | TIMESTAMP | Session expires | `2024-01-16 02:00:00` |
| last_activity | TIMESTAMP | Last interaction | `2024-01-15 14:30:00` |

**Context JSON Format:**
```json
[
  {
    "role": "user",
    "content": "What's the weather like?"
  },
  {
    "role": "assistant",
    "content": "I don't have real-time weather data, but..."
  },
  {
    "role": "user",
    "content": "Thanks!"
  }
]
```

**Session ID Format:**
```
{user_jid}_{chat_jid}_{unix_timestamp}
Example: 1234567890@s.whatsapp.net_123456789-1234567890@g.us_1705330200
```

**Indexes:**
- `idx_expires_at`: Fast cleanup of expired sessions
- `idx_user_chat`: Lookup active session for user in specific chat
- `idx_last_activity`: Find stale sessions

**Expiry enforcement:**
- Timestamps are stored as ISO strings in UTC.
- `get_or_create_session` re-validates expiry in Python (timezone-safe) and deletes stale rows before returning a session, preventing old context from leaking into new conversations.
- For self-debug chats, `reset_stale_session` drops sessions whose `last_activity` exceeds a configurable age (`self.stale_session_seconds`, default 60s) so the first debug message starts with a clean context.

**Expiry Calculation Examples:**

**Mode: time (reset_time = "02:00")**
```python
# Message at 10:00 PM → expires at 2:00 AM (next day)
created_at = datetime(2024, 1, 15, 22, 0, 0)
expires_at = datetime(2024, 1, 16, 2, 0, 0)

# Message at 3:00 AM → expires at 2:00 AM (tomorrow)
created_at = datetime(2024, 1, 15, 3, 0, 0)
expires_at = datetime(2024, 1, 16, 2, 0, 0)
```

**Mode: duration (reset_hours = 24)**
```python
# Message at 10:00 AM → expires at 10:00 AM (next day)
created_at = datetime(2024, 1, 15, 10, 0, 0)
expires_at = datetime(2024, 1, 16, 10, 0, 0)
```

**Mode: same_day**
```python
# Any message today → expires at midnight tonight
created_at = datetime(2024, 1, 15, 14, 30, 0)
expires_at = datetime(2024, 1, 16, 0, 0, 0)
```

### Table: whatsapp_device

**Purpose:** Store WhatsApp session credentials for auto-reconnection

```sql
CREATE TABLE whatsapp_device (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Enforce single row
    session_data TEXT NOT NULL,             -- Encrypted session JSON
    last_connected TIMESTAMP NOT NULL       -- Last successful connection
);
```

**Fields Explained:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Always 1 (single row) | `1` |
| session_data | TEXT | Serialized session | `{"encKey": "...", "macKey": "..."}` |
| last_connected | TIMESTAMP | Last connection | `2024-01-15 14:30:00` |

**Session Data Structure:**
```json
{
  "clientID": "base64_encoded_client_id",
  "serverToken": "base64_encoded_server_token",
  "clientToken": "base64_encoded_client_token",
  "encKey": "base64_encoded_encryption_key",
  "macKey": "base64_encoded_mac_key",
  "wid": "1234567890@s.whatsapp.net"
}
```

**Purpose:**
- Avoid QR code scan on every restart
- Maintain persistent WhatsApp connection
- Automatic reconnection after disconnect

**Lifecycle:**
1. First run: Empty table → QR code required
2. After QR scan: Session saved to table
3. Subsequent runs: Load session → auto-connect
4. Session expires (~20 days): Clear table → QR code required

## Query Patterns

### Common Queries

**1. Get Unprocessed Messages**
```sql
SELECT * FROM messages
WHERE chat_jid IN (?, ?, ?)  -- monitored entities
AND is_from_me = 0           -- received, not sent
ORDER BY timestamp DESC
LIMIT 10;
```

**2. Get Chat History**
```sql
SELECT * FROM messages
WHERE chat_jid = ?
ORDER BY timestamp DESC
LIMIT 50;
```

**3. Get or Create Session**
```sql
-- Check for existing session
SELECT * FROM chat_sessions
WHERE user_jid = ?
AND chat_jid = ?
AND expires_at > ?  -- not expired
ORDER BY created_at DESC
LIMIT 1;

-- If not found, create new
INSERT INTO chat_sessions
(session_id, user_jid, chat_jid, context, created_at, expires_at, last_activity)
VALUES (?, ?, ?, '[]', ?, ?, ?);
```

**4. Update Session Context**
```sql
UPDATE chat_sessions
SET context = ?,
    last_activity = ?
WHERE session_id = ?;
```

**5. Cleanup Old Messages**
```sql
DELETE FROM messages
WHERE created_at < ?;  -- cutoff date
```

**6. Cleanup Expired Sessions**
```sql
DELETE FROM chat_sessions
WHERE expires_at < ?;  -- now
```

**7. Get Database Statistics**
```sql
-- Total messages
SELECT COUNT(*) FROM messages;

-- Messages per chat
SELECT chat_jid, COUNT(*) as count
FROM messages
GROUP BY chat_jid
ORDER BY count DESC;

-- Active sessions
SELECT COUNT(*) FROM chat_sessions
WHERE expires_at > ?;

-- Database size
SELECT page_count * page_size as size
FROM pragma_page_count(), pragma_page_size();
```

## Database Operations

### Initialization

```python
def initialize_database(db_path):
    """Create tables and indexes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")

    # Create tables
    cursor.execute(CREATE_MESSAGES_TABLE)
    cursor.execute(CREATE_INDEXES_MESSAGES)

    cursor.execute(CREATE_SESSIONS_TABLE)
    cursor.execute(CREATE_INDEXES_SESSIONS)

    cursor.execute(CREATE_DEVICE_TABLE)

    conn.commit()
    conn.close()
```

### Message Insertion

```python
def insert_message(conn, msg_id, chat_jid, sender, content, timestamp, is_from_me):
    """Store new message"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO messages
        (id, chat_jid, sender, content, timestamp, is_from_me)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (msg_id, chat_jid, sender, content, timestamp, is_from_me))
    conn.commit()
```

### Session Management

```python
def get_or_create_session(conn, user_jid, chat_jid):
    """Get existing session or create new one"""
    cursor = conn.cursor()

    # Try to find existing session
    cursor.execute("""
        SELECT * FROM chat_sessions
        WHERE user_jid = ? AND chat_jid = ?
        AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_jid, chat_jid, datetime.now()))

    row = cursor.fetchone()
    if row:
        return dict(row)

    # Create new session
    session_id = f"{user_jid}_{chat_jid}_{int(datetime.now().timestamp())}"
    created_at = datetime.now()
    expires_at = calculate_expiry(created_at)

    cursor.execute("""
        INSERT INTO chat_sessions
        (session_id, user_jid, chat_jid, context, created_at, expires_at, last_activity)
        VALUES (?, ?, ?, '[]', ?, ?, ?)
    """, (session_id, user_jid, chat_jid, created_at, expires_at, created_at))

    conn.commit()

    return {
        "session_id": session_id,
        "user_jid": user_jid,
        "chat_jid": chat_jid,
        "context": "[]",
        "created_at": created_at,
        "expires_at": expires_at,
        "last_activity": created_at
    }
```

### Rotation Cleanup

```python
def cleanup_old_messages(conn, retention_days):
    """Delete messages older than retention period"""
    cursor = conn.cursor()
    cutoff = datetime.now() - timedelta(days=retention_days)

    cursor.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
    deleted_count = cursor.rowcount

    conn.commit()
    return deleted_count
```

### Session Cleanup

```python
def cleanup_expired_sessions(conn):
    """Delete expired sessions"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_sessions WHERE expires_at < ?", (datetime.now(),))
    deleted_count = cursor.rowcount

    conn.commit()
    return deleted_count
```

## Performance Optimization

### WAL Mode Benefits

```sql
PRAGMA journal_mode=WAL;
```

**Benefits:**
- Concurrent reads while writing
- Better performance for multiple connections
- Reduced disk I/O
- Atomic commits

**Trade-offs:**
- Slightly more disk space (`.wal` and `.shm` files)
- Need to checkpoint periodically

### Indexes Strategy

**Created Indexes:**
1. `messages(chat_jid, timestamp)` - Chat history queries
2. `messages(created_at)` - Rotation cleanup
3. `messages(sender)` - Sender lookups
4. `chat_sessions(expires_at)` - Session cleanup
5. `chat_sessions(user_jid, chat_jid)` - Session retrieval

**Why These Indexes:**
- Cover most common query patterns
- Minimal overhead (only 5 indexes total)
- Balance between read speed and write speed

### Connection Management

**Single Connection Pattern:**
```python
class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
```

**Benefits:**
- No connection pool overhead
- Simplified error handling
- WAL mode allows concurrent access
- Thread-safe with `check_same_thread=False`

### Query Optimization

**Use Parameterized Queries:**
```python
# Good
cursor.execute("SELECT * FROM messages WHERE chat_jid = ?", (jid,))

# Bad (SQL injection risk + no prepared statement caching)
cursor.execute(f"SELECT * FROM messages WHERE chat_jid = '{jid}'")
```

**Limit Result Sets:**
```python
# Good
cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 50")

# Bad (fetches all rows)
cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC")
```

## Maintenance Operations

### VACUUM (Database Compaction)

**Purpose:** Reclaim space after deletions

```sql
VACUUM;
```

**When to Run:**
- After large deletions (rotation cleanup)
- Database file size growing
- Periodic maintenance (monthly)

**Note:** VACUUM can take time on large databases

### Database Statistics

```python
def get_database_stats(conn):
    """Get database statistics"""
    cursor = conn.cursor()

    # Total messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]

    # Active sessions
    cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE expires_at > ?", (datetime.now(),))
    active_sessions = cursor.fetchone()[0]

    # Database size
    cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0]

    return {
        "total_messages": total_messages,
        "active_sessions": active_sessions,
        "database_size_bytes": db_size,
        "database_size_mb": round(db_size / 1024 / 1024, 2)
    }
```

### Backup Strategy

**Recommended Backup:**
```bash
# Daily backup
sqlite3 store/whatsapp_bot.db ".backup store/backups/whatsapp_bot_$(date +%Y%m%d).db"

# Keep last 7 days
find store/backups/ -name "whatsapp_bot_*.db" -mtime +7 -delete
```

**What to Backup:**
1. `whatsapp_bot.db` - Main database
2. `.env` - Configuration (secure!)
3. `app.json` - Application config

**Restore:**
```bash
cp store/backups/whatsapp_bot_20240115.db store/whatsapp_bot.db
systemctl restart whatsapp-bot
```

## Database Growth Estimates

### Messages Table

**Assumptions:**
- Average message: 200 bytes
- 100 messages/day
- 7-day retention

**Storage:**
```
200 bytes × 100 msgs/day × 7 days = 140 KB
```

**With 1000 messages/day:**
```
200 bytes × 1000 msgs/day × 7 days = 1.4 MB
```

### Sessions Table

**Assumptions:**
- Average session: 5 KB (10 messages context)
- 10 active sessions concurrently

**Storage:**
```
5 KB × 10 sessions = 50 KB
```

### Total Database Size Estimates

| Message Volume | Retention | Estimated Size |
|----------------|-----------|----------------|
| 100 msgs/day | 7 days | ~1 MB |
| 1000 msgs/day | 7 days | ~10 MB |
| 1000 msgs/day | 30 days | ~40 MB |
| 10000 msgs/day | 7 days | ~100 MB |

**Note:** WAL files add ~10-20% overhead

## Troubleshooting

### Database Locked Errors

**Cause:** Multiple processes accessing database

**Solution:**
```python
# Increase timeout
conn = sqlite3.connect(db_path, timeout=30.0)

# Ensure WAL mode
cursor.execute("PRAGMA journal_mode=WAL")
```

### Slow Queries

**Diagnosis:**
```sql
EXPLAIN QUERY PLAN SELECT * FROM messages WHERE chat_jid = ?;
```

**Look for:** `USING INDEX` (good) vs `SCAN TABLE` (bad)

**Solution:** Add missing indexes

### Database Corruption

**Check Integrity:**
```sql
PRAGMA integrity_check;
```

**If Corrupted:**
```bash
# Restore from backup
cp store/backups/whatsapp_bot_latest.db store/whatsapp_bot.db

# Or export/import
sqlite3 store/whatsapp_bot.db .dump > dump.sql
rm store/whatsapp_bot.db
sqlite3 store/whatsapp_bot.db < dump.sql
```

### Large Database Size

**Solutions:**
1. Reduce retention period
2. Run VACUUM
3. Archive old messages
4. Increase cleanup frequency

```python
# Archive before cleanup
cursor.execute("SELECT * FROM messages WHERE created_at < ?", (cutoff,))
archive_messages(cursor.fetchall())

# Then delete
cursor.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
```
