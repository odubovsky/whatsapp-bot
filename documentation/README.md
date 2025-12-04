# WhatsApp Bot - AI-Powered Message Responder

An AI-powered WhatsApp bot that monitors specific groups/users and responds using Perplexity AI with configurable prompts per entity.

## Features

- ✅ QR code authentication for WhatsApp
- ✅ Monitor specific groups and individual users
- ✅ Per-entity custom prompts and personas
- ✅ Session memory with configurable expiry (time-based, duration, or same-day)
- ✅ Configurable message rotation (automatic cleanup)
- ✅ Daily vitality health checks
- ✅ Startup validation messages
- ✅ Perplexity API integration
- ✅ Cloud deployment ready

## Quick Start

### 1. Clone and Setup

```bash
cd whatsapp-bot
./setup.sh
```

### 2. Configure

Edit `.env`:
```bash
PERPLEXITY_API_KEY=your_api_key_here
LOG_LEVEL=INFO
```

Edit `app.json`:
```json
{
  "whatsapp": {
    "phone_number": "YOUR_PHONE_NUMBER"
  },
  "monitored_entities": [
    {
      "type": "group",
      "jid": "GROUP_JID@g.us",
      "name": "Family Group",
      "prompt": "You are a helpful family assistant...",
      "persona": "friendly"
    }
  ]
}
```

### 3. Run

```bash
# First time: Scan QR code
python3 bot/main.py --qr-only

# After scanning, start service
./run-bot.sh
```

## Configuration

### Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| PERPLEXITY_API_KEY | Yes | Your Perplexity API key |
| LOG_LEVEL | No | DEBUG, INFO, WARNING, ERROR (default: INFO) |
| DATABASE_PATH | No | Custom database path (default: store/whatsapp_bot.db) |

### Application Config (app.json)

See [.claude/configuration.md](.claude/configuration.md) for complete reference.

#### Key Settings:

- **monitored_entities**: Groups/users to monitor with per-entity prompts
- **polling.interval_seconds**: How often to check for new messages (default: 5)
- **rotation.messages_retention_days**: Days to keep messages (default: 7)
- **session_memory.reset_mode**: "time", "duration", or "same_day"
- **vitality**: Daily health check configuration
- **perplexity**: AI model settings

## Usage

### Basic Commands

```bash
# Normal start
./run-bot.sh

# Show QR code only
python3 bot/main.py --qr-only

# Reset WhatsApp session
python3 bot/main.py --reset-session

# Show database stats
python3 bot/main.py --show-stats

# Validate configuration
python3 bot/main.py --validate-config

# Debug mode
python3 bot/main.py --log-level DEBUG

# Dry run (test without connecting)
python3 bot/main.py --dry-run
```

### Production Deployment

```bash
# Run in background using nohup or screen/tmux
nohup ./run-bot.sh > bot/logs/service.log 2>&1 &

# Or use screen for interactive management
screen -S whatsapp-bot
./run-bot.sh
# Press Ctrl+A then D to detach

# To reattach later
screen -r whatsapp-bot
```

## Project Structure

```
whatsapp-bot/
├── .env                      # API keys (gitignored)
├── app.json                  # Main configuration
├── main.py                   # Entry point
├── config.py                 # Configuration management
├── database.py               # SQLite operations
├── whatsapp_client.py        # WhatsApp integration
├── message_agent.py          # AI integration
├── vitality_checker.py       # Health checks
├── setup.sh                  # Automated setup
├── run-bot.sh                # Bot runner script
└── store/                    # Database storage
```

## Documentation

Comprehensive documentation available in [.claude/](.claude/) directory:

- [project-overview.md](.claude/project-overview.md) - Project goals and architecture
- [requirements.md](.claude/requirements.md) - Detailed requirements
- [architecture.md](.claude/architecture.md) - System architecture
- [configuration.md](.claude/configuration.md) - Configuration reference
- [database-design.md](.claude/database-design.md) - Database schema
- [cli-reference.md](.claude/cli-reference.md) - CLI documentation
- [implementation-checklist.md](.claude/implementation-checklist.md) - Development checklist

## Architecture

**Single-Process Design:**
- Async event loop for concurrency
- WhatsApp message listener (event-driven)
- Message polling agent (queries Perplexity)
- Background cleanup tasks (rotation, session expiry)
- Daily vitality checker (scheduled)

**Data Flow:**
```
WhatsApp → Message Received → Database → Polling Agent
  ↑                                           ↓
  └──────── Response Sent ←──── Perplexity API
```

## Session Memory

Three expiry modes:

### Time-based (reset at specific time)
```json
"session_memory": {
  "reset_mode": "time",
  "reset_time": "02:00",
  "timezone": "UTC"
}
```
All sessions expire at 2:00 AM daily.

### Duration-based (rolling window)
```json
"session_memory": {
  "reset_mode": "duration",
  "reset_hours": 24
}
```
Sessions expire 24 hours after creation.

### Same-day (reset at midnight)
```json
"session_memory": {
  "reset_mode": "same_day",
  "timezone": "UTC"
}
```
Sessions reset at midnight daily.

## Message Rotation

Automatic cleanup of old messages:

```json
"rotation": {
  "messages_retention_days": 7,
  "cleanup_interval_hours": 24
}
```

Keeps database lightweight and protects privacy.

## WhatsApp Integration

**IMPORTANT:** This implementation includes a stub WhatsApp client. For production use, you need to integrate a proper WhatsApp library:

### Options:

1. **baileys-py** (Recommended)
   - Python port of Baileys
   - Supports QR authentication
   - Active development

2. **WhatsApp Business API** (Official)
   - Requires business verification
   - Cloud-based solution
   - Best for enterprise

3. **whatsmeow Bridge** (Like reference)
   - Use Go reference implementation as bridge
   - Communicate via HTTP/WebSocket
   - Most reliable

4. **Custom Implementation**
   - Direct WebSocket to WhatsApp
   - Requires protocol knowledge

See [whatsapp_client.py](whatsapp_client.py) for integration points.

## Troubleshooting

### QR Code Not Displaying
```bash
# Install qrencode
sudo apt install qrencode  # Linux
brew install qrencode      # macOS

# Try QR-only mode
python3 bot/main.py --qr-only
```

### Messages Not Being Processed
```bash
# Check database
python3 bot/main.py --show-stats

# Enable debug logging
python3 bot/main.py --log-level DEBUG

# Verify configuration
python3 bot/main.py --validate-config
```

### Session Expired
```bash
# Reset and re-authenticate
python3 bot/main.py --reset-session
```

### Database Growing Too Large
```bash
# Reduce retention period in app.json
"messages_retention_days": 3

# Or manually cleanup
# (utility scripts coming soon)
```

## Development

### Requirements

- Python 3.9+
- Linux/macOS
- Perplexity API key

### Setup Development Environment

```bash
# Install dependencies
pip3 install --user -r bot/requirements.txt

# Copy config templates
cp .env.example .env
cp bot/app.json.example bot/app.json

# Edit configs
nano .env
nano bot/app.json

# Run tests
python3 bot/config.py
python3 bot/database.py
```

### Testing

```bash
# Validate configuration
python3 bot/main.py --validate-config

# Test without connecting
python3 bot/main.py --dry-run

# Send test message
python3 bot/main.py --send-test "Hello from bot!"
```

## Contributing

This is a personal project, but suggestions are welcome!

## License

MIT License - See LICENSE file for details

## Security

- **Never commit .env or app.json** to version control
- Store backups securely (contains session credentials)
- Rotate API keys periodically
- Review monitored entity lists regularly

## Roadmap

- [ ] Utility scripts (db_manager.py, test_config.py, send_message.py)
- [ ] Media message support (images, videos, documents)
- [ ] Web dashboard for monitoring
- [ ] Multi-language support
- [ ] Custom plugin system
- [ ] Analytics and reporting
- [ ] Scheduled messages
- [ ] Group admin commands

## Support

For issues, questions, or suggestions:
- Check documentation in `.claude/` directory
- Review logs: `tail -f bot/logs/whatsapp-bot.log`
- Enable debug mode: `python3 bot/main.py --log-level DEBUG`

## Acknowledgments

- Reference Go implementation: **`/Users/odedd/coding/whatsapp-mcp`**
- Perplexity AI for language model API
- WhatsApp for messaging platform
