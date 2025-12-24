# Workshop Quick Start Guide

This guide helps you set up and run the WhatsApp bot locally

## 1) Install System Dependencies

You need system packages for Python, SQLite, QR display, and building the Go bridge.

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip \
  build-essential pkg-config sqlite3 libsqlite3-dev qrencode
```

### Go (required for the bridge)
The bridge targets Go 1.24.1 (see `whatsapp-bridge/go.mod`). If your OS package
manager does not provide a recent Go, install it from:

https://go.dev/dl/

## 2) Clone the Repository

Get the code onto your machine and enter the project directory.

```bash
git clone https://github.com/odubovsky/whatsapp-bot/tree/remaster
cd whatsapp-bot
```

## 3) Run the Setup Script

This script installs Python dependencies and creates config templates.

```bash
./setup.sh --install-system-deps
```

It will:
- Install Python packages from `bot/requirements.txt` using `pip`
- Create `.env` from `.env.example`
- Create `app.json` from `app.json.example`

## 4) Configure API Keys and Monitored Entities

Edit `.env` and provide your API key(s).

```bash
nano .env
```

At minimum:
```
PERPLEXITY_API_KEY=your_api_key_here
```

Edit `app.json` and set your phone and monitored entities.

```bash
nano app.json
```

## 5) Build the WhatsApp Bridge (Linux/Ubuntu)

On Linux, you must build the Go bridge locally.

```bash
cd whatsapp-bridge
go build -o whatsapp-client
cd ..
```

On macOS (arm64), `whatsapp-bridge/whatsapp-client` is already built.

## 6) Start the Bridge (Terminal 1)

The bridge connects to WhatsApp and exposes a local API.

```bash
./run-bridge.sh
```

On the first run, scan the QR code shown in the terminal.

If you need a fresh QR code:
```bash
./run-bridge.sh --reset-session
```

## 7) Start the Bot (Terminal 2)

The bot reads messages and sends responses.

```bash
./run-bot.sh
```

Optional: skip startup validation if needed.
```bash
./run-bot.sh --no-startup-validation
```

## 8) Verify the End-to-End Flow

- Send a message from a monitored number or group.
- Watch both terminals for logs.
- For group JIDs: send a message in the group and look for `123456789@g.us`
  in the bridge logs, then update `app.json`.
