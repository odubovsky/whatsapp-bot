# WhatsApp Bot - Quick Start Guide

## ✅ Bot is Ready to Use!

Your WhatsApp bot is fully set up and ready to run.

## How to Start the Bot

### Terminal 1: Start Go Bridge
```bash
cd /Users/odedd/coding/whatsapp-bot/whatsapp-bridge
./whatsapp-client
```

Wait for: `✓ Connected to WhatsApp!`

### Terminal 2: Start Python Bot
```bash
cd /Users/odedd/coding/whatsapp-bot
python main.py --no-startup-validation
```

Look for:
```
🚀 WhatsApp Bot is now running
  Phone: 972504078989
  Monitored entities: 2
  Polling: Enabled
  Vitality checks: Enabled
```

## Testing

**Send a message to yourself** (+972504078989) from another phone.

The bot should:
1. Receive your message
2. Query Perplexity AI with your configured prompt
3. Send a response back

## Monitoring

### Check Python Bot Logs
The terminal running `python main.py` will show:
- Incoming messages
- Perplexity API calls
- Outgoing responses

### Check Go Bridge Logs
The terminal running `./whatsapp-client` will show:
- WhatsApp connection status
- Message send/receive events

## Configuration

### Monitored Entities
Edit [app.json](app.json) to configure:
- Which groups/users to monitor
- Custom prompts per entity
- Persona for each entity

### Current Configuration
- **Your number**: +972504078989 (monitored)
- **Example group**: Needs real JID (placeholder currently)

To get a real group JID:
1. Send a message in the group you want to monitor
2. Look at the Go bridge logs for the group's JID (format: `123456789@g.us`)
3. Update `app.json` with that JID

### API Configuration
Edit [.env](.env) to change:
- Perplexity API key
- Log level
- Database path

## Useful Commands

### Validate Configuration
```bash
python main.py --validate-config
```

### Check Database Stats
```bash
python main.py --show-stats
```

### View All Options
```bash
python main.py --help
```

### Enable Debug Logging
```bash
python main.py --log-level DEBUG --no-startup-validation
```

## Stopping the Bot

Press `Ctrl+C` in both terminals to stop:
1. Python bot (Terminal 2)
2. Go bridge (Terminal 1)

## Next Steps

1. **Test the bot** by sending yourself a message
2. **Get real group JIDs** from Go bridge logs
3. **Update app.json** with actual group JIDs and custom prompts
4. **Customize prompts** for different groups/users
5. **Adjust polling interval** if needed (default: 5 seconds)
6. **Configure timezone** for vitality checks (default: UTC)

## Troubleshooting

### "Go bridge not reachable" error
- Make sure you started the Go bridge first
- Check port 8080 is not in use: `lsof -i :8080`

### No responses to messages
- Verify Perplexity API key in `.env`
- Check you're sending from a monitored entity (your number or configured group)
- Enable debug logging: `python main.py --log-level DEBUG --no-startup-validation`

### WhatsApp disconnected
- Restart Go bridge: `./whatsapp-client`
- If needed, re-authenticate: `./whatsapp-client --reset-session`

## Documentation

- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Full setup details and architecture
- [STATUS.md](STATUS.md) - Current status and troubleshooting details
- [app.json.example](app.json.example) - Configuration template

## Support

For issues or questions:
- Check logs in both terminals
- Use `--log-level DEBUG` for detailed output
- Review [STATUS.md](STATUS.md) for known issues
