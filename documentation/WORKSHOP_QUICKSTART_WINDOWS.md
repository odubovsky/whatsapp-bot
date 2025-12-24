# Workshop Quick Start Guide (Windows)

This guide helps you set up and run the WhatsApp bot locally on Windows.

## 1) Install System Dependencies

You need Git, Python 3.9+, and Go for the WhatsApp bridge.

- Git: https://git-scm.com/downloads
- Python 3.9+: https://www.python.org/downloads/
  - During install, check "Add Python to PATH"
- Go (bridge build): https://go.dev/dl/

Optional (QR display helper):
- Chocolatey: https://chocolatey.org/install
- Then run:
  ```powershell
  choco install qrencode
  ```

## 2) Clone the Repository

Get the code onto your machine and enter the project directory.

```powershell
git clone https://github.com/odubovsky/whatsapp-bot
cd whatsapp-bot
```

## 3) Run the Setup Script

This script installs Python dependencies and creates config templates.

```powershell
.\setup.sh --install-system-deps
```

If the shell script does not run on your Windows setup, do the equivalent
steps manually:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r bot\requirements.txt
copy .env.example .env
copy app.json.example app.json
```

## 4) Configure API Keys and Monitored Entities

Edit `.env` and provide your API key(s).

```powershell
notepad .env
```

At minimum:
```
PERPLEXITY_API_KEY=your_api_key_here
```

Edit `app.json` and set your phone and monitored entities.

```powershell
notepad app.json
```

## 5) Build the WhatsApp Bridge

You must build the Go bridge locally on Windows.

```powershell
cd whatsapp-bridge
go build -o whatsapp-client.exe
cd ..
```

## 6) Start the Bridge (Terminal 1)

The bridge connects to WhatsApp and exposes a local API.

```powershell
.\run-bridge.sh
```

On the first run, scan the QR code shown in the terminal.

If you need a fresh QR code:
```powershell
.\run-bridge.sh --reset-session
```

## 7) Start the Bot (Terminal 2)

The bot reads messages and sends responses.

```powershell
.\run-bot.sh
```

Optional: skip startup validation if needed.
```powershell
.\run-bot.sh --no-startup-validation
```

## 8) Verify the End-to-End Flow

- Send a message from a monitored number or group.
- Watch both terminals for logs.
- For group JIDs: send a message in the group and look for `123456789@g.us`
  in the bridge logs, then update `app.json`.
