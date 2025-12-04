# WhatsApp Bot - Project Overview

## Project Goal
Build an AI-powered WhatsApp bot that monitors specific groups/users and responds using Perplexity AI with configurable prompts per entity.

## Core Requirements

### 1. WhatsApp Integration
- Hook to telephone number via QR code authentication
- Background agent running constantly
- Event-driven message handling (not polling WhatsApp)

### 2. Message Storage & Rotation
- Lightweight local SQLite database
- **Configurable** message retention (e.g., 7 days)
- **Configurable** cleanup interval
- Only store messages from designated groups/users

### 3. Selective Response
- Only respond to specific people/groups defined in config
- Per-entity prompts (each group/user has unique LLM persona)
- Filter incoming messages - only monitored entities stored

### 4. AI Integration
- Use Perplexity API for responses
- Configurable model, temperature, max_tokens
- Include session memory for context

### 5. Session Memory
- Track conversation context per user/chat
- **Configurable expiry modes**:
  - `time`: Reset at specific time (e.g., 2:00 AM)
  - `duration`: Reset after X hours
  - `same_day`: Reset at midnight
- Session ID maintained until expiry

### 6. Configuration Management
- `.env` file for API keys and secrets
- `app.json` for all other config (JSON format):
  - Monitored groups/users with individual prompts
  - Polling intervals
  - Rotation settings
  - Session memory settings
  - Vitality check settings
  - Perplexity API settings

### 7. Health Monitoring
- **Startup validation**: Send self-message confirming service is up
- **Daily vitality check**: Scheduled message at configurable time
- Both use configured timezone

### 8. Deployment Considerations
- Python-based implementation
- Virtual environment setup via `setup.sh`
- Cloud-ready (VPS/systemd service)
- Persistent storage for database and sessions
- No Docker (cloud VM deployment)

### 9. Development Guidelines
- No mockups or placeholders
- Deal with issues directly
- Clean, production-ready code
- Comprehensive CLI help for all scripts

## Technology Stack

### Core Libraries
- **WhatsApp**: `yowsup2` or similar Python WhatsApp library
- **Database**: SQLite (built-in `sqlite3`)
- **HTTP Client**: `httpx` for Perplexity API
- **Scheduler**: `apscheduler` for vitality checks
- **Config**: `python-dotenv`, `pydantic` for validation
- **Async**: `asyncio` for concurrent operations

### System Requirements
- Python 3.9+
- Linux VPS (systemd for service management)
- Persistent storage for database

## Project Structure

```
whatsapp-bot/
├── .env                      # API keys (gitignored)
├── .env.example             # Template
├── app.json                 # Main configuration
├── app.json.example         # Template
├── requirements.txt         # Python dependencies
├── setup.sh                 # Automated environment setup
├── run.sh                   # Service runner script
├── README.md                # User documentation
├── .claude/                 # Project documentation
│   ├── project-overview.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── configuration.md
│   ├── database-design.md
│   └── cli-reference.md
├── systemd/
│   └── whatsapp-bot.service # Linux service file
├── main.py                  # Entry point + orchestration
├── config.py                # Configuration loader
├── whatsapp_client.py       # WhatsApp connection & events
├── database.py              # SQLite operations
├── message_agent.py         # Polling + Perplexity integration
├── vitality_checker.py      # Health check scheduler
├── db_manager.py            # Database utility script
├── test_config.py           # Config validator script
├── send_message.py          # Message sender utility
└── store/
    └── whatsapp_bot.db      # SQLite database
```

## Implementation Phases

### Phase 1: Core Infrastructure
- Project structure and setup scripts
- Configuration management (`.env` + `app.json`)
- Database schema with rotation logic
- Logging setup

### Phase 2: WhatsApp Integration
- QR authentication flow
- Message receiving with event handlers
- Message filtering (monitored entities only)
- Startup validation message

### Phase 3: AI Agent
- Database polling mechanism
- Session memory management
- Perplexity API integration
- Per-entity prompt handling

### Phase 4: Health & Maintenance
- Daily vitality check scheduler
- Message rotation cleanup task
- Session expiry management
- Database statistics and monitoring

### Phase 5: Deployment & Utilities
- CLI help for all scripts
- Utility scripts (db_manager, test_config, send_message)
- Systemd service configuration
- Cloud deployment documentation

## Key Design Decisions

### Single-Process Architecture
Unlike the Go reference (two-process), this will be a single Python process with:
- Async event loop for concurrency
- Background tasks for polling and cleanup
- Simpler deployment and monitoring

### Configuration-First Design
All behavior configurable without code changes:
- Message retention periods
- Session expiry modes
- Entity-specific prompts
- Polling intervals
- Health check schedules

### Cloud-Ready from Start
- Systemd service integration
- Persistent storage handling
- Timezone-aware scheduling
- Comprehensive logging
- Health monitoring

## Success Criteria

1. ✅ Connects to WhatsApp via QR code
2. ✅ Sends startup validation message
3. ✅ Receives messages from monitored entities only
4. ✅ Stores messages with configurable retention
5. ✅ Maintains session memory with configurable expiry
6. ✅ Responds using Perplexity with per-entity prompts
7. ✅ Sends daily vitality check messages
8. ✅ Runs reliably in cloud environment
9. ✅ All configuration via `.env` and `app.json`
10. ✅ Comprehensive CLI help and utilities

## Reference Implementation

Go implementation analyzed at: `/Users/odedd/coding/whatsapp-mcp`

Key patterns adopted:
- JID (Jabber ID) system for chat identification
- SQLite for message and session storage
- Event-driven message handling
- Session persistence for auto-reconnection
- Media handling (encryption keys + URLs)

Key differences:
- Single process vs. two-process architecture
- Python vs. Go
- Simplified (no MCP server integration)
- Enhanced configuration flexibility
- Built-in health monitoring
