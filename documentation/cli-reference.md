# WhatsApp Bot - CLI Reference

## Main Service (main.py)

### Usage

```bash
python main.py [OPTIONS]
```

### Options

#### Connection Options

**--reset-session**
- Force WhatsApp re-authentication
- Clears stored session credentials
- Displays QR code for scanning
- Use when: Session expired, logged out, or switching accounts

```bash
python main.py --reset-session
```

**--qr-only**
- Display QR code and exit without starting service
- Useful for: Initial setup, remote server authentication
- After scanning, run normally to start service

```bash
python main.py --qr-only
```

#### Database Options

**--reset-db**
- Clear all messages and chat sessions
- Preserves WhatsApp authentication session
- WARNING: Irreversible operation

```bash
python main.py --reset-db
```

**--db-path PATH**
- Use custom database file location
- Default: `store/whatsapp_bot.db`
- Useful for: Testing, multiple instances

```bash
python main.py --db-path /tmp/test.db
```

**--show-stats**
- Display database statistics and exit
- Shows: message count, active sessions, database size
- No service start

```bash
python main.py --show-stats
```

Output example:
```
Database Statistics:
  Total Messages: 1,234
  Active Sessions: 5
  Database Size: 2.5 MB
  Last WhatsApp Connection: 2024-01-15 14:30:00
```

#### Configuration Options

**--config FILE**
- Specify custom configuration file
- Default: `app.json`
- Useful for: Multiple environments, testing

```bash
python main.py --config config-production.json
```

**--env-file FILE**
- Specify custom .env file
- Default: `.env`
- Useful for: Multiple environments

```bash
python main.py --env-file .env.production
```

**--validate-config**
- Validate configuration files and exit
- Checks: syntax, required fields, data types
- No service start

```bash
python main.py --validate-config
```

Output example:
```
✅ Configuration valid
  - .env: PERPLEXITY_API_KEY present
  - app.json: 4 monitored entities
  - Timezones: valid
  - All required fields: present
```

#### Service Options

**--no-vitality**
- Disable daily vitality health check messages
- Useful for: Testing, debugging, quiet operation

```bash
python main.py --no-vitality
```

**--no-polling**
- Disable message polling agent
- Bot receives messages but doesn't respond
- Useful for: Monitoring only, testing

```bash
python main.py --no-polling
```

**--polling-interval SECONDS**
- Override polling interval from config
- Range: 1-300 seconds
- Useful for: Performance tuning, testing

```bash
python main.py --polling-interval 10
```

#### Logging Options

**--log-level LEVEL**
- Set logging verbosity
- Values: DEBUG, INFO, WARNING, ERROR
- Overrides .env LOG_LEVEL

```bash
python main.py --log-level DEBUG
```

**--log-file FILE**
- Write logs to file in addition to stdout
- Creates file if doesn't exist
- Useful for: Production deployment, debugging

```bash
python main.py --log-file /var/log/whatsapp-bot.log
```

**--quiet**
- Suppress all output except errors
- Useful for: Background operation, cron jobs

```bash
python main.py --quiet
```

#### Testing Options

**--dry-run**
- Test configuration without connecting to WhatsApp
- Validates: config files, database, permissions
- No actual WhatsApp connection

```bash
python main.py --dry-run
```

Output example:
```
[DRY RUN] Configuration loaded
[DRY RUN] Database initialized
[DRY RUN] 4 monitored entities configured
[DRY RUN] Would connect to WhatsApp (skipped)
[DRY RUN] All checks passed
```

**--send-test MESSAGE**
- Send test message to yourself and exit
- Requires: WhatsApp already connected
- Useful for: Testing connectivity

```bash
python main.py --send-test "Bot test message"
```

### Examples

**First-time setup:**
```bash
# Show QR code for authentication
python main.py --qr-only

# After scanning, start service
python main.py
```

**Production start:**
```bash
python main.py --log-file /var/log/whatsapp-bot.log --log-level INFO
```

**Debug mode:**
```bash
python main.py --log-level DEBUG --no-vitality
```

**Testing:**
```bash
# Validate config
python main.py --validate-config

# Dry run
python main.py --dry-run

# Send test message
python main.py --send-test "Testing bot"
```

**Reset and restart:**
```bash
# Clear session, re-authenticate
python main.py --reset-session

# Clear all data
python main.py --reset-db --reset-session
```

---

## Database Manager (db_manager.py)

### Usage

```bash
python db_manager.py COMMAND [OPTIONS]
```

### Commands

#### stats

Display database statistics

```bash
python db_manager.py stats
```

Output:
```
Database Statistics:
  Total Messages: 1,234
  Messages by Chat:
    Family Group: 456
    Work Team: 321
    Alice: 123
  Active Sessions: 5
  Expired Sessions: 12
  Database Size: 2.5 MB
  Last WhatsApp Connection: 2024-01-15 14:30:00
```

#### cleanup

Delete old messages

**Options:**
- `--days N`: Delete messages older than N days (default: 7)
- `--dry-run`: Show what would be deleted without deleting

```bash
# Delete messages older than 7 days
python db_manager.py cleanup --days 7

# Preview what would be deleted
python db_manager.py cleanup --days 7 --dry-run
```

Output:
```
Cleanup Preview:
  Messages to delete: 456
  Date cutoff: 2024-01-08 14:30:00

Run without --dry-run to execute
```

#### export

Export messages to file

**Options:**
- `--output FILE`: Output file path (required)
- `--format FORMAT`: Export format: json or csv (default: json)
- `--chat JID`: Export specific chat only (optional)

```bash
# Export all messages to JSON
python db_manager.py export --output messages.json

# Export specific chat to CSV
python db_manager.py export --output family.csv --format csv --chat "123456789-1234567890@g.us"
```

Output formats:

**JSON:**
```json
[
  {
    "id": "3EB0ABC123DEF456",
    "chat_jid": "123456789-1234567890@g.us",
    "sender": "1234567890@s.whatsapp.net",
    "content": "Hello world",
    "timestamp": "2024-01-15T14:30:00",
    "is_from_me": false
  }
]
```

**CSV:**
```csv
id,chat_jid,sender,content,timestamp,is_from_me
3EB0ABC123DEF456,123456789-1234567890@g.us,1234567890@s.whatsapp.net,Hello world,2024-01-15T14:30:00,false
```

#### sessions

Manage chat sessions

**Options:**
- `--list`: List all sessions
- `--clear`: Clear expired sessions
- `--user JID`: Filter by user JID

```bash
# List all active sessions
python db_manager.py sessions --list

# Clear expired sessions
python db_manager.py sessions --clear

# List sessions for specific user
python db_manager.py sessions --list --user "1234567890@s.whatsapp.net"
```

Output:
```
Active Sessions:
  Session: user_123...@s.whatsapp.net_456...@g.us_1705330200
    User: 1234567890@s.whatsapp.net
    Chat: Family Group
    Created: 2024-01-15 10:00:00
    Expires: 2024-01-16 02:00:00
    Messages: 5
```

#### vacuum

Optimize database (reclaim space)

```bash
python db_manager.py vacuum
```

Output:
```
Vacuuming database...
Before: 5.2 MB
After: 2.5 MB
Reclaimed: 2.7 MB
```

### Global Options

**--db PATH**
- Specify database path
- Default: `store/whatsapp_bot.db`

```bash
python db_manager.py stats --db /tmp/test.db
```

---

## Configuration Validator (test_config.py)

### Usage

```bash
python test_config.py [OPTIONS]
```

### Options

**--config FILE**
- Path to app.json config file
- Default: `app.json`

```bash
python test_config.py --config config-production.json
```

**--env-file FILE**
- Path to .env file
- Default: `.env`

```bash
python test_config.py --env-file .env.production
```

**--show-entities**
- Display all monitored groups and users

```bash
python test_config.py --show-entities
```

Output:
```
Monitored Entities:
  [1] Group: Family Group (123456789-1234567890@g.us)
      Prompt: You are a helpful family assistant...
      Persona: friendly and casual

  [2] User: Alice (5551234567)
      Prompt: You are Alice's personal assistant...
      Persona: organized and proactive
```

**--test-perplexity**
- Test connection to Perplexity API
- Sends test query to verify API key

```bash
python test_config.py --test-perplexity
```

Output:
```
Testing Perplexity API...
✅ API key valid
✅ Model accessible: llama-3.1-sonar-large-128k-online
✅ Test query successful
```

**--check-timezones**
- Validate timezone settings

```bash
python test_config.py --check-timezones
```

Output:
```
Checking Timezones:
✅ session_memory.timezone: America/New_York (valid)
✅ vitality.timezone: America/New_York (valid)
```

**--verbose**
- Show detailed validation output

```bash
python test_config.py --verbose
```

### Examples

**Basic validation:**
```bash
python test_config.py
```

**Full check:**
```bash
python test_config.py --show-entities --test-perplexity --check-timezones --verbose
```

**Production validation:**
```bash
python test_config.py --config /etc/whatsapp-bot/app.json --env-file /etc/whatsapp-bot/.env
```

---

## Message Sender (send_message.py)

### Usage

```bash
python send_message.py [OPTIONS]
```

### Options

**--to RECIPIENT**
- Recipient: phone number, JID, or group name
- Examples: `1234567890`, `123456789-1234567890@g.us`, `Family Group`

```bash
python send_message.py --to 1234567890 --message "Hello"
```

**--self**
- Send message to yourself
- Uses phone number from config

```bash
python send_message.py --self --message "Test message"
```

**--message TEXT**
- Message text to send
- Required unless --file provided

```bash
python send_message.py --to 1234567890 --message "Hello, how are you?"
```

**--file PATH**
- File to send (image, video, document)
- Supports: jpg, png, pdf, mp4, etc.

```bash
python send_message.py --to 1234567890 --file /path/to/image.jpg
```

**--config FILE**
- Path to config file
- Default: `app.json`

```bash
python send_message.py --config config-production.json --self --message "Test"
```

### Examples

**Send text message:**
```bash
python send_message.py --to 1234567890 --message "Hello from bot!"
```

**Send to yourself:**
```bash
python send_message.py --self --message "Testing bot functionality"
```

**Send to group by name:**
```bash
python send_message.py --to "Family Group" --message "Hello everyone!"
```

**Send image:**
```bash
python send_message.py --to 1234567890 --file /path/to/photo.jpg
```

**Send document:**
```bash
python send_message.py --to 1234567890 --file /path/to/document.pdf --message "Here's the file"
```

---

## Setup Script (setup.sh)

### Usage

```bash
./setup.sh [OPTIONS]
```

### Options

**-h, --help**
- Show help message

```bash
./setup.sh --help
```

**--python PATH**
- Use specific Python binary
- Default: `python3`

```bash
./setup.sh --python python3.11
```

**--skip-venv**
- Skip virtual environment creation
- Install to system Python (not recommended)

```bash
./setup.sh --skip-venv
```

**--no-templates**
- Don't create config templates
- Use when configs already exist

```bash
./setup.sh --no-templates
```

**--install-system-deps**
- Install system dependencies (requires sudo)
- Installs: qrencode, etc.

```bash
./setup.sh --install-system-deps
```

### Examples

**Standard setup:**
```bash
./setup.sh
```

**With system dependencies:**
```bash
./setup.sh --install-system-deps
```

**Specific Python version:**
```bash
./setup.sh --python /usr/bin/python3.11
```

---

## Run Script (run.sh)

### Usage

```bash
./run.sh [ARGS]
```

**Description:**
- Activates virtual environment
- Runs main.py with provided arguments
- Logs to stdout and file

### Examples

**Normal start:**
```bash
./run.sh
```

**With arguments:**
```bash
./run.sh --log-level DEBUG --no-vitality
```

**Background mode:**
```bash
nohup ./run.sh > /dev/null 2>&1 &
```

---

## Common Workflows

### Initial Setup

```bash
# 1. Run setup
./setup.sh

# 2. Edit configs
nano .env          # Add PERPLEXITY_API_KEY
nano app.json      # Add groups, users, prompts

# 3. Validate
python test_config.py --verbose

# 4. Show QR code
python main.py --qr-only

# 5. Scan QR with phone

# 6. Start service
./run.sh
```

### Daily Operation

```bash
# Check status
python main.py --show-stats

# View logs
tail -f logs/whatsapp-bot.log

# Send test message
python send_message.py --self --message "Bot check"
```

### Maintenance

```bash
# Clean old messages
python db_manager.py cleanup --days 7

# View statistics
python db_manager.py stats

# Optimize database
python db_manager.py vacuum

# Export messages
python db_manager.py export --output backup.json
```

### Troubleshooting

```bash
# Validate config
python test_config.py --verbose

# Test Perplexity API
python test_config.py --test-perplexity

# Reset session
python main.py --reset-session

# Debug mode
python main.py --log-level DEBUG

# Dry run
python main.py --dry-run
```

### Production Deployment

```bash
# Install as systemd service
sudo cp systemd/whatsapp-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-bot
sudo systemctl start whatsapp-bot

# Check status
sudo systemctl status whatsapp-bot

# View logs
sudo journalctl -u whatsapp-bot -f

# Restart
sudo systemctl restart whatsapp-bot
```

---

## Environment Variables

Can be set in `.env` or passed directly:

```bash
# Override log level
LOG_LEVEL=DEBUG python main.py

# Custom database
DATABASE_PATH=/tmp/test.db python main.py

# Multiple variables
LOG_LEVEL=DEBUG DATABASE_PATH=/tmp/test.db python main.py
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Configuration error |
| 2 | Database error |
| 3 | WhatsApp connection error |
| 4 | API error (Perplexity) |
| 5 | Permission error |
| 130 | Interrupted (Ctrl+C) |

---

## Tips

### Quick Testing

```bash
# Test everything
python test_config.py --verbose && \
python main.py --dry-run && \
python main.py --send-test "Test" && \
echo "All tests passed!"
```

### Log Monitoring

```bash
# Live logs with filtering
tail -f logs/whatsapp-bot.log | grep ERROR

# Last 100 lines
tail -n 100 logs/whatsapp-bot.log

# Search logs
grep "Family Group" logs/whatsapp-bot.log
```

### Database Maintenance

```bash
# Weekly cleanup script
python db_manager.py cleanup --days 7
python db_manager.py sessions --clear
python db_manager.py vacuum
python db_manager.py stats
```

### Multiple Instances

```bash
# Instance 1 (production)
python main.py --config app-prod.json --env-file .env.prod --db-path store/prod.db

# Instance 2 (testing)
python main.py --config app-test.json --env-file .env.test --db-path store/test.db
```
