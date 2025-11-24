# WhatsApp Bot - Detailed Requirements

## Functional Requirements

### FR1: WhatsApp Connection
- **FR1.1**: Connect to WhatsApp using phone number and QR code authentication
- **FR1.2**: Persist session credentials for automatic reconnection
- **FR1.3**: Handle disconnection/reconnection gracefully
- **FR1.4**: Support QR code display in terminal
- **FR1.5**: Allow session reset via CLI flag

### FR2: Message Reception
- **FR2.1**: Receive messages from all WhatsApp chats
- **FR2.2**: Filter messages based on monitored entities (groups/users)
- **FR2.3**: Store only messages from monitored entities
- **FR2.4**: Extract message metadata (sender, timestamp, chat JID)
- **FR2.5**: Support text messages (media optional for future)

### FR3: Message Storage
- **FR3.1**: Store messages in SQLite database
- **FR3.2**: Include: message ID, chat JID, sender, content, timestamp, direction
- **FR3.3**: Implement configurable message retention (days)
- **FR3.4**: Automatic cleanup based on retention period
- **FR3.5**: Configurable cleanup interval (hours)

### FR4: Message Processing
- **FR4.1**: Poll database for new unprocessed messages
- **FR4.2**: Configurable polling interval (seconds)
- **FR4.3**: Retrieve session memory for context
- **FR4.4**: Query Perplexity API with message + context
- **FR4.5**: Send response back to WhatsApp chat

### FR5: Session Memory
- **FR5.1**: Maintain conversation context per user/chat
- **FR5.2**: Support three expiry modes:
  - **Time-based**: Reset at specific time (e.g., 2:00 AM)
  - **Duration-based**: Reset after X hours
  - **Same-day**: Reset at midnight
- **FR5.3**: Store session ID, user JID, chat JID, context, timestamps
- **FR5.4**: Automatic cleanup of expired sessions
- **FR5.5**: Timezone-aware expiry calculation

### FR6: AI Integration
- **FR6.1**: Use Perplexity API for generating responses
- **FR6.2**: Per-entity prompts (each group/user has unique prompt)
- **FR6.3**: Per-entity personas (tone/style configuration)
- **FR6.4**: Include session memory in API calls
- **FR6.5**: Configurable model, temperature, max_tokens

### FR7: Configuration Management
- **FR7.1**: Load API keys from `.env` file
- **FR7.2**: Load application config from `app.json` (JSON format)
- **FR7.3**: Validate configuration at startup
- **FR7.4**: Support for:
  - WhatsApp phone number
  - Monitored entities (groups/users) with prompts
  - Polling settings
  - Rotation settings
  - Session memory settings
  - Vitality check settings
  - Perplexity API settings
- **FR7.5**: Provide example configuration templates

### FR8: Health Monitoring
- **FR8.1**: Send startup validation message to self
- **FR8.2**: Confirm WhatsApp connection is operational
- **FR8.3**: Daily vitality check at configurable time
- **FR8.4**: Configurable vitality message content
- **FR8.5**: Timezone-aware scheduling

### FR9: Command-Line Interface
- **FR9.1**: Main service with comprehensive CLI options
- **FR9.2**: Database management utility
- **FR9.3**: Configuration validator
- **FR9.4**: Message sender utility
- **FR9.5**: Help text for all scripts
- **FR9.6**: Support for common operations:
  - Reset session
  - Reset database
  - Show statistics
  - Validate config
  - Send test message
  - Dry-run mode

### FR10: Deployment Support
- **FR10.1**: Automated setup script (virtual environment)
- **FR10.2**: Service runner script
- **FR10.3**: Systemd service file
- **FR10.4**: Cloud deployment documentation
- **FR10.5**: Persistent storage handling
- **FR10.6**: Log file management

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: Message processing latency < 5 seconds
- **NFR1.2**: Support for multiple concurrent chats
- **NFR1.3**: Efficient database queries with indexes
- **NFR1.4**: Minimal memory footprint

### NFR2: Reliability
- **NFR2.1**: Auto-reconnect on WhatsApp disconnection
- **NFR2.2**: Graceful error handling
- **NFR2.3**: No data loss during rotation cleanup
- **NFR2.4**: Session persistence across restarts
- **NFR2.5**: Transaction safety for database operations

### NFR3: Security
- **NFR3.1**: API keys in `.env` (not in code)
- **NFR3.2**: `.env` excluded from git (.gitignore)
- **NFR3.3**: Secure storage of WhatsApp session credentials
- **NFR3.4**: No logging of sensitive data

### NFR4: Maintainability
- **NFR4.1**: Clean code structure with separation of concerns
- **NFR4.2**: Type hints for all functions
- **NFR4.3**: Docstrings for modules and classes
- **NFR4.4**: Modular design (easy to extend)
- **NFR4.5**: No mockups or placeholders

### NFR5: Usability
- **NFR5.1**: Simple setup process (run setup.sh)
- **NFR5.2**: Clear error messages
- **NFR5.3**: Comprehensive help text
- **NFR5.4**: Example configurations provided
- **NFR5.5**: Logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)

### NFR6: Scalability
- **NFR6.1**: Support for multiple monitored entities
- **NFR6.2**: Efficient handling of high message volume
- **NFR6.3**: Database optimization (WAL mode, indexes)
- **NFR6.4**: Async operations for concurrency

### NFR7: Portability
- **NFR7.1**: Python 3.9+ compatibility
- **NFR7.2**: Linux environment (systemd)
- **NFR7.3**: Cloud VPS deployment ready
- **NFR7.4**: No Docker dependency

## Configuration Requirements

### app.json Schema

```json
{
  "whatsapp": {
    "phone_number": "string (required)"
  },
  "monitored_entities": [
    {
      "type": "group|user (required)",
      "jid": "string (optional, for groups)",
      "phone": "string (optional, for users)",
      "name": "string (required)",
      "prompt": "string (required)",
      "persona": "string (required)"
    }
  ],
  "polling": {
    "interval_seconds": "integer (default: 5)"
  },
  "rotation": {
    "messages_retention_days": "integer (default: 7)",
    "cleanup_interval_hours": "integer (default: 24)"
  },
  "session_memory": {
    "reset_mode": "time|duration|same_day (required)",
    "reset_time": "string HH:MM (required if mode=time)",
    "reset_hours": "integer (required if mode=duration)",
    "timezone": "string IANA timezone (default: UTC)"
  },
  "vitality": {
    "enabled": "boolean (default: true)",
    "time": "string HH:MM (default: 09:00)",
    "timezone": "string IANA timezone (default: UTC)",
    "message": "string (default: 🤖 Bot operational)"
  },
  "perplexity": {
    "model": "string (default: llama-3.1-sonar-large-128k-online)",
    "temperature": "float 0.0-1.0 (default: 0.7)",
    "max_tokens": "integer (default: 500)"
  }
}
```

### .env Schema

```
PERPLEXITY_API_KEY=string (required)
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR (default: INFO)
DATABASE_PATH=string (default: store/whatsapp_bot.db)
```

## Use Cases

### UC1: First-Time Setup
1. User clones repository
2. Runs `./setup.sh`
3. Edits `.env` with API key
4. Edits `app.json` with groups/users
5. Runs `./run.sh`
6. Scans QR code in terminal
7. Receives startup validation message
8. Bot begins monitoring

### UC2: Daily Operation
1. User sends message in monitored group
2. Bot receives message via WhatsApp event
3. Bot stores message in database
4. Polling agent detects new message
5. Agent retrieves session memory
6. Agent queries Perplexity with entity-specific prompt
7. Bot sends response to group
8. Session memory updated

### UC3: Session Expiry (Time-based)
1. Session created at 10:00 PM
2. User converses with bot
3. Session memory accumulates context
4. At 2:00 AM (configured reset_time)
5. Session expires and is deleted
6. Next message creates new session
7. Bot has no memory of previous conversation

### UC4: Daily Vitality Check
1. Service runs 24/7
2. At configured time (e.g., 9:00 AM)
3. Bot sends vitality message to self
4. Confirms service is operational
5. Repeats next day

### UC5: Message Rotation Cleanup
1. Background task runs every 24 hours (configurable)
2. Calculates cutoff date (7 days ago, configurable)
3. Deletes messages older than cutoff
4. Logs number of deleted messages
5. Database remains lightweight

### UC6: Cloud Deployment
1. User provisions Linux VPS
2. Clones repository
3. Runs `./setup.sh`
4. Configures `.env` and `app.json`
5. Installs systemd service
6. Enables and starts service
7. SSH to VPS, scans QR code (first time only)
8. Service runs automatically on reboot
9. Monitors via logs

### UC7: Configuration Update
1. User modifies `app.json` (add new group)
2. Restarts service
3. New configuration loaded
4. Bot now monitors new group
5. Existing sessions preserved

### UC8: Session Reset
1. User wants to force re-authentication
2. Runs `./main.py --reset-session`
3. WhatsApp session cleared from database
4. New QR code displayed
5. User scans QR code
6. New session established

## Constraints

### C1: Technical Constraints
- Python 3.9+ required
- Linux environment for systemd
- Internet connectivity required
- WhatsApp account required

### C2: Operational Constraints
- WhatsApp session requires periodic re-authentication (~20 days)
- Perplexity API rate limits apply
- Database size grows with message volume

### C3: Design Constraints
- No Docker (cloud VM deployment)
- No mockups or placeholders
- SQLite only (no external database)
- Single-process architecture

## Assumptions

### A1: Environment
- Linux VPS with systemd
- Python 3.9+ available
- Internet connectivity stable
- Sufficient disk space for database

### A2: WhatsApp
- User has valid WhatsApp account
- Phone can receive SMS for verification
- QR code authentication supported
- Multi-device mode enabled

### A3: Configuration
- User can provide valid Perplexity API key
- User knows JIDs of groups to monitor
- Timezone settings are valid IANA timezones

### A4: Usage
- Moderate message volume (not high-traffic)
- Text messages primarily (media optional)
- English language for prompts and responses
