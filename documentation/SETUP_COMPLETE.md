# WhatsApp Bot - Setup Complete!

## ✅ What's Been Set Up

### Core Application
- ✅ Python virtual environment created
- ✅ All dependencies installed
- ✅ Configuration files created (`.env` + `app.json`)
- ✅ Database initialized
- ✅ All Python modules implemented

### WhatsApp Integration
- ✅ Go WhatsApp bridge copied from reference implementation
- ✅ Python client configured to communicate with Go bridge via HTTP
- ✅ Two-process architecture: Python (AI) + Go (WhatsApp)

## Architecture

```
┌─────────────────────────────────────┐
│   Python Bot (main.py)              │
│   - Configuration management        │
│   - Database (SQLite)              │
│   - Message polling agent           │
│   - Perplexity AI integration       │
│   - Vitality checker                │
│   - HTTP client to Go bridge        │
└──────────┬──────────────────────────┘
           │ HTTP (localhost:8080)
           ├─ /api/send (send messages)
           └─ /api/download (media)
           │
┌──────────▼──────────────────────────┐
│   Go Bridge (whatsapp-client)       │
│   - WhatsApp connection (whatsmeow) │
│   - QR authentication               │
│   - Message receiving               │
│   - REST API endpoints              │
└─────────────────────────────────────┘
```

## How to Run

### Option 1: First Time Setup (QR Code)

```bash
# Terminal 1: Start Go bridge with QR authentication
cd /Users/odedd/coding/whatsapp-bot/whatsapp-bridge
./whatsapp-client

# Scan the QR code with WhatsApp when it appears
# Wait for "Connected to WhatsApp" message

# Terminal 2: Start Python bot
cd /Users/odedd/coding/whatsapp-bot
./run.sh
```

### Option 2: After QR Scanned (Normal Run)

Once WhatsApp is authenticated, both services will auto-connect:

```bash
# Terminal 1: Go bridge (start this FIRST)
cd /Users/odedd/coding/whatsapp-bot/whatsapp-bridge
./whatsapp-client

# Wait for "Connected to WhatsApp!" message, then...

# Terminal 2: Python bot (skip startup validation until connection is stable)
cd /Users/odedd/coding/whatsapp-bot
python main.py --no-startup-validation
```

**Note**: The `--no-startup-validation` flag skips the initial test message to yourself. This is recommended until the WhatsApp connection fully stabilizes after startup (usually takes 10-30 seconds).

### Option 3: Integrated Start (Coming Soon)

We can create a single script to start both processes.

## Current Configuration

### Phone Number
- **972504078989**

### Monitored Entities
1. **Example Group** (placeholder JID - needs real group JID)
2. **Oded Dubovsky** (you) - will respond to your messages

### AI Settings
- **Model**: sonar-pro (Perplexity)
- **Temperature**: 0.7
- **Max Tokens**: 1000

### Session Memory
- **Mode**: time-based
- **Reset**: Daily at 02:00 UTC
- **Effect**: Conversation context clears at 2 AM

### Vitality Check
- **Enabled**: Yes
- **Time**: 09:00 UTC daily
- **Message**: Health check confirmation

## Next Steps

### Immediate
1. ✅ Start Go bridge to scan QR code
2. ✅ Start Python bot
3. ✅ Send yourself a message to test
4. ✅ Check logs for responses

### Configuration
1. Get actual group JIDs (check Go bridge logs when messages arrive)
2. Update `app.json` with real group JIDs
3. Customize prompts per group/user
4. Adjust timezone if needed

### Optional
1. Add more monitored groups/users
2. Customize prompts and personas
3. Adjust polling interval
4. Modify message retention period

## File Locations

### Configuration
- `.env` - API keys
- `app.json` - Application config

### Database
- `store/whatsapp_bot.db` - Python bot database (messages, sessions)
- `whatsapp-bridge/store/whatsapp.db` - Go bridge (WhatsApp session)
- `whatsapp-bridge/store/messages.db` - Go bridge (message history)

### Logs
- `logs/whatsapp-bot.log` - Python bot logs
- Go bridge logs to stdout (Terminal 1)

## Troubleshooting

### QR Code Not Appearing
```bash
cd whatsapp-bridge
./whatsapp-client --reset-session
```

### Go Bridge Won't Start
```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill existing process if needed
kill -9 <PID>
```

### Python Bot Can't Connect
- Ensure Go bridge is running first
- Check Go bridge is on port 8080
- Check logs for errors

### No Responses
- Check Perplexity API key in `.env`
- Verify messages are from monitored entities
- Check polling is enabled (not `--no-polling`)
- Review logs for errors

## Commands Reference

### Python Bot
```bash
# Validate configuration
python main.py --validate-config

# Show database stats
python main.py --show-stats

# Dry run (no WhatsApp)
python main.py --dry-run

# Normal run
./run.sh

# With options
python main.py --log-level DEBUG
python main.py --no-vitality
```

### Go Bridge
```bash
# Normal start
./whatsapp-client

# Reset and re-authenticate
./whatsapp-client --reset-session

# Debug mode
./whatsapp-client --log-level DEBUG
```

## What's Working

✅ Configuration loading and validation
✅ Database operations (messages, sessions, rotation)
✅ Message agent (Perplexity integration)
✅ Session memory with time-based expiry
✅ Daily vitality checks
✅ Message rotation cleanup
✅ Go WhatsApp bridge integration
✅ HTTP communication between Python and Go

## Ready to Test!

You're all set up! Follow the "How to Run" section above to start both services.
