# Docker Setup Guide

This guide explains how to run the WhatsApp Bot using Docker Compose.

## Architecture

The setup consists of two containers:

1. **Bridge Container** (`whatsapp-bridge`): Go-based WhatsApp bridge using whatsmeow
   - Handles WhatsApp connection and authentication
   - Stores messages in shared database
   - Exposes HTTP API on port 8080 (internal network only)

2. **Bot Container** (`whatsapp-bot`): Python-based AI message processing bot
   - Polls shared database for new messages
   - Processes messages using LLM (Perplexity/OpenAI)
   - Sends responses via bridge HTTP API

## Prerequisites

- Docker and Docker Compose installed
- `.env` file with required API keys (see `.env.example`)
- `app.json` configuration file

## Quick Start

1. **Prepare environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Build and start containers:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f bridge
   docker-compose logs -f bot
   ```

4. **Stop containers:**
   ```bash
   docker-compose down
   ```

## First Time Setup (QR Code Authentication)

1. **Start the bridge container:**
   ```bash
   docker-compose up bridge
   ```

2. **Scan QR code** that appears in the logs:
   ```bash
   docker-compose logs -f bridge
   ```

3. **Once connected**, stop the bridge and start both services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Configuration

### Environment Variables

The bot container reads from `.env` file. Key variables:

- `LLM_PROVIDER`: `perplexity` or `openai` (default: `perplexity`)
- `PERPLEXITY_API_KEY`: Your Perplexity API key
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI)
- `LLM_TEMPERATURE`: Temperature for LLM (default: `0.7`)
- `LLM_MAX_TOKENS`: Max tokens for LLM (default: `500`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Bridge Configuration

Bridge environment variables (set in `docker-compose.yml` or `.env`):

- `WHATSAPP_LOG_LEVEL`: Log level (default: `INFO`)
- `WHATSAPP_RESET_SESSION`: Set to `true` to force re-authentication
- `WHATSAPP_RESET_MESSAGES`: Set to `true` to reset message database

## Volumes

The setup uses three Docker volumes:

1. **shared-store**: Shared messages database (`/shared/store/messages.db`)
   - Bridge writes messages here
   - Bot reads messages from here

2. **bot-store**: Bot processing database (`/app/bot/store/whatsapp_bot.db`)
   - Bot's internal state and session management

3. **bridge-store**: Bridge session and media (`/app/store/`)
   - WhatsApp session database (`whatsapp.db`)
   - Media files (`{chat_jid}/`)

## Networking

- Containers communicate via internal Docker network `whatsapp-bot-network`
- Bridge API is accessible at `http://bridge:8080` from bot container
- Port 8080 is **not exposed** to host by default (internal only)
- To expose for debugging, uncomment the `ports` section in `docker-compose.yml`

## Troubleshooting

### Bridge not starting

1. Check logs:
   ```bash
   docker-compose logs bridge
   ```

2. Verify QR code authentication completed (first time only)

3. Check if port 8080 is available (if exposed)

### Bot can't connect to bridge

1. Verify bridge is healthy:
   ```bash
   docker-compose ps
   ```

2. Check bot logs for connection errors:
   ```bash
   docker-compose logs bot
   ```

3. Verify `BRIDGE_URL` environment variable is set correctly

### Database issues

1. **Reset databases** (WARNING: Deletes all data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. **Backup volumes**:
   ```bash
   docker run --rm -v whatsapp-bot_shared-store:/data -v $(pwd):/backup alpine tar czf /backup/shared-store-backup.tar.gz -C /data .
   ```

3. **Restore volumes**:
   ```bash
   docker run --rm -v whatsapp-bot_shared-store:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/shared-store-backup.tar.gz"
   ```

## Development

### Mount config files for easy editing

Uncomment the volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./app.json:/app/app.json:ro
  - ./.env:/app/.env:ro
```

Then restart:
```bash
docker-compose restart bot
```

### Rebuild after code changes

```bash
docker-compose build
docker-compose up -d
```

### Access container shell

```bash
# Bot container
docker-compose exec bot bash

# Bridge container
docker-compose exec bridge sh
```

## Production Considerations

1. **Use secrets management** instead of `.env` file
2. **Set up log rotation** for container logs
3. **Configure resource limits** in `docker-compose.yml`
4. **Use Docker secrets** for API keys
5. **Set up monitoring** and health checks
6. **Backup volumes** regularly

## Health Checks

Both containers have health checks configured:

- **Bridge**: Checks HTTP endpoint `/api/send`
- **Bot**: Checks Python process

View health status:
```bash
docker-compose ps
```

## Stopping and Cleanup

```bash
# Stop containers (keeps volumes)
docker-compose down

# Stop and remove volumes (WARNING: Deletes all data)
docker-compose down -v

# Remove everything including images
docker-compose down -v --rmi all
```

