# WhatsApp Bot - Configuration Reference

## Configuration Files

### .env - Environment Variables

Location: `/.env` (root directory, gitignored)

```bash
# Required: Perplexity API Key
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Optional: Logging level
# Values: DEBUG, INFO, WARNING, ERROR
# Default: INFO
LOG_LEVEL=INFO

# Optional: Custom database path
# Default: store/whatsapp_bot.db
DATABASE_PATH=store/whatsapp_bot.db
```

### app.json - Application Configuration

Location: `/app.json` (root directory)

#### Full Example

```json
{
  "whatsapp": {
    "phone_number": "1234567890"
  },
  "self": {
    "active": true,
    "prompt": "/path/to/self.prompt",
    "prompt_is_file": true,
    "persona": "friendly and concise",
    "stale_session_seconds": 60,
    "debug": true
  },
  "monitored_entities": [
    {
      "type": "group",
      "jid": "123456789-1234567890@g.us",
      "name": "Family Group",
      "active": true,
      "debug": true,
      "prompt": "You are a helpful family assistant. Be warm, supportive, and provide practical advice. Keep responses concise and friendly.",
      "prompt_is_file": false,
      "persona": "friendly and casual"
    },
    {
      "type": "group",
      "jid": "987654321-0987654321@g.us",
      "name": "Work Team",
      "prompt": "You are a professional project manager. Provide concise, actionable responses. Focus on productivity and clarity.",
      "persona": "formal and efficient"
    },
    {
      "type": "user",
      "phone": "5551234567",
      "name": "Alice",
      "prompt": "You are Alice's personal assistant. Help with scheduling, reminders, and organization. Be proactive and detail-oriented.",
      "persona": "organized and proactive"
    },
    {
      "type": "user",
      "phone": "5559876543",
      "name": "Bob",
      "prompt": "You are Bob's technical advisor. Provide detailed technical explanations with code examples when appropriate.",
      "persona": "technical and thorough"
    }
  ],
  "polling": {
    "interval_seconds": 5
  },
  "response_delay": 5,
  "rotation": {
    "messages_retention_days": 7,
    "cleanup_interval_hours": 24
  },
  "session_memory": {
    "reset_mode": "time",
    "reset_time": "02:00",
    "timezone": "America/New_York"
  },
  "vitality": {
    "enabled": true,
    "time": "09:00",
    "timezone": "America/New_York",
    "message": "🤖 WhatsApp Bot vitality check - All systems operational"
  },
  "perplexity": {
    "model": "llama-3.1-sonar-large-128k-online",
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

## Configuration Schema

### whatsapp

**Description:** WhatsApp connection settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone_number | string | Yes | Your WhatsApp phone number (no spaces, no +) |

**Example:**
```json
"whatsapp": {
  "phone_number": "1234567890"
}
```

### monitored_entities

**Description:** List of groups and users to monitor and respond to

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | "group" or "user" |
| jid | string | Conditional | Required for groups (format: `ID@g.us`) |
| phone | string | Conditional | Required for users (phone number) |
| name | string | Yes | Display name for logging |
| prompt | string | Yes | System prompt for this entity; can be inline text or a filesystem path (see prompt_is_file) |
| prompt_is_file | boolean | No | If true, load prompt from the file path in `prompt` |
|  |  |  | Auto-detection: if `prompt` contains a `/` and the file exists, it will be loaded even if `prompt_is_file` is false |
| persona | string | Yes | Description of response style |
| debug | boolean | No | Send a pre-LLM debug message with user entry, prompt, persona |
| session_memory | object | No | Optional per-entity override of session memory settings |
| response_delay | integer | No | Seconds to wait before responding (overrides global response_delay; 0 = immediate) |

**Group Example:**
```json
{
  "type": "group",
  "jid": "123456789-1234567890@g.us",
  "name": "Family Group",
  "active": true,
  "debug": true,
  "prompt": "You are a helpful family assistant...",
  "persona": "friendly and casual"
}
```

**User Example:**
```json
{
  "type": "user",
  "phone": "1234567890",
  "name": "John Doe",
  "prompt": "You are John's personal assistant...",
  "persona": "professional",
  "session_memory": {
    "reset_mode": "duration",
    "reset_minutes": 10,
    "timezone": "UTC"
  }
}
```

**How to find Group JID:**
1. Add the bot to the group
2. Check logs when message received
3. Or use utility: `python send_message.py --list-chats`

### self

**Description:** Settings for messages you send to yourself (debug/testing)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| active | boolean | No | false | Enable responses to self messages |
| prompt | string | Conditional | - | Required if active |
| prompt_is_file | boolean | No | false | If true, load prompt from the file path in `prompt` |
|  |  |  | Auto-detection: if `prompt` contains a `/` and the file exists, it will be loaded even if `prompt_is_file` is false |
| persona | string | No | helpful and concise | Persona description |
| stale_session_seconds | integer | No | 60 | If last self-session activity is older than this, discard it so the next first message starts with fresh context |
| debug | boolean | No | true | If true, send a pre-LLM debug message with user entry, prompt, and persona |

### polling

**Description:** Message polling configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| interval_seconds | integer | No | 5 | Seconds between DB polls |

**Example:**
```json
"polling": {
  "interval_seconds": 5
}
```

**Recommendations:**
- Low traffic: 10-30 seconds
- Medium traffic: 5-10 seconds
- High traffic: 2-5 seconds

### response_delay

**Description:** Default seconds to wait before the bot replies (gives you time to answer manually).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| response_delay | integer | No | 5 | Seconds to wait before sending the LLM reply; 0 = immediate |

**Per-entity override:** Set `response_delay` on a monitored entity to override the global default.

### rotation

**Description:** Message cleanup configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| messages_retention_days | integer | No | 7 | Days to keep messages |
| cleanup_interval_hours | integer | No | 24 | Hours between cleanups |

**Example:**
```json
"rotation": {
  "messages_retention_days": 7,
  "cleanup_interval_hours": 24
}
```

**Recommendations:**
- Short-term memory: 1-3 days
- Medium-term: 7 days (default)
- Long-term archive: 30+ days

### session_memory

**Description:** Conversation memory configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| reset_mode | string | Yes | - | "time", "duration", or "same_day" |
| reset_time | string | Conditional | - | Required if mode=time (HH:MM format) |
| reset_hours | integer | Conditional | - | Required if mode=duration (alternative to minutes) |
| reset_minutes | integer | Conditional | - | Alternative to reset_hours for short windows (mode=duration) |
| timezone | string | No | UTC | IANA timezone string |

**Mode: time** (Reset at specific time daily)
```json
"session_memory": {
  "reset_mode": "time",
  "reset_time": "02:00",
  "timezone": "America/New_York"
}
```
All sessions expire at 2:00 AM Eastern Time daily.

**Mode: duration** (Reset after X hours)
```json
"session_memory": {
  "reset_mode": "duration",
  "reset_hours": 24,
  "timezone": "UTC"
}
```
Each session expires 24 hours after creation.

**Mode: same_day** (Reset at midnight)
```json
"session_memory": {
  "reset_mode": "same_day",
  "timezone": "America/Los_Angeles"
}
```
Sessions expire at midnight Pacific Time.

**Per-entity override**
- Each monitored entity can include its own `session_memory` block. If provided, that override is used for that entity; otherwise the global `session_memory` applies.
- `reset_minutes` is helpful for short-lived context (e.g., `reset_minutes: 2` means no history is kept after 2 minutes of inactivity).
- For `reset_mode=time`, `reset_time` defines when the day’s first context begins; messages after that cutoff start a fresh session.

**Valid Timezones:** See [IANA Time Zone Database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

Common examples:
- `UTC`
- `America/New_York` (Eastern)
- `America/Chicago` (Central)
- `America/Los_Angeles` (Pacific)
- `Europe/London`
- `Asia/Tokyo`

### vitality

**Description:** Daily health check configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| enabled | boolean | No | true | Enable daily health checks |
| time | string | No | 09:00 | Daily check time (HH:MM) |
| timezone | string | No | UTC | IANA timezone string |
| message | string | No | 🤖 Bot operational | Message content |

**Example:**
```json
"vitality": {
  "enabled": true,
  "time": "09:00",
  "timezone": "America/New_York",
  "message": "🤖 WhatsApp Bot is alive and monitoring"
}
```

**To disable:**
```json
"vitality": {
  "enabled": false
}
```

### perplexity

**Description:** Perplexity API configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| model | string | No | llama-3.1-sonar-large-128k-online | Model name |
| temperature | float | No | 0.7 | Randomness (0.0-1.0) |
| max_tokens | integer | No | 500 | Max response length |

**Example:**
```json
"perplexity": {
  "model": "llama-3.1-sonar-large-128k-online",
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Available Models:**
- `llama-3.1-sonar-small-128k-online` (faster, cheaper)
- `llama-3.1-sonar-large-128k-online` (default, balanced)
- `llama-3.1-sonar-huge-128k-online` (best quality)

**Temperature Guidelines:**
- `0.0-0.3`: Factual, deterministic responses
- `0.4-0.7`: Balanced (default)
- `0.8-1.0`: Creative, varied responses

## Configuration Validation

### Validation Rules

1. **Required Fields:**
   - `whatsapp.phone_number`
   - `monitored_entities` (at least one)
   - Each entity must have: `type`, `name`, `prompt`, `persona`
   - Groups must have `jid`
   - Users must have `phone`
   - `session_memory.reset_mode`

2. **Conditional Requirements:**
   - If `reset_mode=time`: `reset_time` required
   - If `reset_mode=duration`: `reset_hours` required

3. **Value Constraints:**
   - `polling.interval_seconds`: 1-300
   - `rotation.messages_retention_days`: 1-365
   - `rotation.cleanup_interval_hours`: 1-168
   - `session_memory.reset_hours`: 1-168
   - `perplexity.temperature`: 0.0-1.0
   - `perplexity.max_tokens`: 100-4000

4. **Format Validation:**
   - Phone numbers: digits only
   - JIDs: `*@g.us` or `*@s.whatsapp.net`
   - Time format: `HH:MM` (24-hour)
   - Timezone: valid IANA timezone

### Validation Tool

Run configuration validator:
```bash
python test_config.py
```

Expected output:
```
✅ Configuration valid
✅ .env file loaded
✅ PERPLEXITY_API_KEY found
✅ app.json parsed successfully
✅ 4 monitored entities configured
✅ Timezones valid
✅ All required fields present
```

With `--verbose`:
```bash
python test_config.py --verbose
```

Shows detailed breakdown of all settings.

## Configuration Best Practices

### 1. Prompt Engineering

**Good Prompt:**
```json
"prompt": "You are a helpful assistant for the Smith family. Respond to questions about schedules, reminders, and general advice. Keep responses under 3 sentences. Be warm and supportive."
```

**Bad Prompt:**
```json
"prompt": "Help the family"
```

**Tips:**
- Be specific about role and context
- Define response length/style
- Include personality traits
- Mention any constraints

### 2. Security

**DO:**
- Keep `.env` out of version control
- Use `.env.example` for templates
- Rotate API keys periodically
- Backup `whatsapp_bot.db` session

**DON'T:**
- Commit `.env` to git
- Share API keys in config files
- Use same config across environments

### 3. Resource Management

**Message Retention:**
```json
// High traffic group (1000s msgs/day)
"messages_retention_days": 1

// Medium traffic (100s msgs/day)
"messages_retention_days": 7

// Low traffic (10s msgs/day)
"messages_retention_days": 30
```

**Polling Interval:**
```json
// Real-time responses needed
"interval_seconds": 2

// Casual monitoring
"interval_seconds": 10

// Low-priority background
"interval_seconds": 30
```

### 4. Session Memory Strategy

**Use Case: Work Chat**
```json
// Reset daily at 2am
"session_memory": {
  "reset_mode": "time",
  "reset_time": "02:00",
  "timezone": "America/New_York"
}
```
Context clears overnight, fresh start each day.

**Use Case: Support Bot**
```json
// Rolling 24-hour window
"session_memory": {
  "reset_mode": "duration",
  "reset_hours": 24
}
```
Maintains context for 24h from first interaction.

**Use Case: Daily Assistant**
```json
// Same-day reset
"session_memory": {
  "reset_mode": "same_day",
  "timezone": "America/Los_Angeles"
}
```
Memory resets at midnight daily.

### 5. Multiple Entities

**Organize by purpose:**
```json
"monitored_entities": [
  // Personal chats
  {"type": "user", "phone": "...", "persona": "casual"},

  // Family groups
  {"type": "group", "jid": "...", "persona": "warm"},

  // Work groups
  {"type": "group", "jid": "...", "persona": "professional"},

  // Support channels
  {"type": "group", "jid": "...", "persona": "helpful"}
]
```

## Environment-Specific Configurations

### Development
```json
{
  "polling": {"interval_seconds": 10},
  "rotation": {"messages_retention_days": 1},
  "vitality": {"enabled": false},
  "perplexity": {"temperature": 0.5, "max_tokens": 200}
}
```

### Production
```json
{
  "polling": {"interval_seconds": 5},
  "rotation": {"messages_retention_days": 7},
  "vitality": {"enabled": true, "time": "09:00"},
  "perplexity": {"temperature": 0.7, "max_tokens": 500}
}
```

### Testing
```json
{
  "monitored_entities": [
    {"type": "user", "phone": "YOUR_NUMBER", "name": "Test", ...}
  ],
  "polling": {"interval_seconds": 2},
  "vitality": {"enabled": false}
}
```

## Troubleshooting

### Common Issues

**Issue:** Bot doesn't respond to group
```
Solution: Check group JID in logs, update app.json
Tool: python send_message.py --list-chats
```

**Issue:** Session expires too soon
```
Solution: Check session_memory.reset_mode and times
Tool: python db_manager.py sessions --list
```

**Issue:** Database growing too large
```
Solution: Reduce messages_retention_days
Tool: python db_manager.py stats
```

**Issue:** API rate limit errors
```
Solution: Increase polling.interval_seconds
Check: Perplexity API dashboard
```

**Issue:** Invalid timezone
```
Solution: Use valid IANA timezone
Tool: python test_config.py --check-timezones
```

## Configuration Updates

### Hot Reload (Future Enhancement)
Currently requires service restart:
```bash
sudo systemctl restart whatsapp-bot
```

### Safe Update Process
1. Backup current config: `cp app.json app.json.backup`
2. Edit `app.json`
3. Validate: `python test_config.py`
4. If valid: restart service
5. If invalid: restore backup
6. Monitor logs: `tail -f logs/whatsapp-bot.log`
