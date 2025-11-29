WhatsApp Python Bridge (Cloud API)
==================================

This bridge uses Meta's official WhatsApp Cloud API (Graph) instead of the unofficial Web/Multi-Device protocol. It provides:

- A thin client wrapper for sending messages and handling media.
- A FastAPI webhook that verifies signatures and normalizes incoming events.
- CLI entrypoints for sending text, downloading media, and running the webhook server.
- Tests for configuration loading, request construction, signature verification, webhook behavior, and CLI help.

Quick start
-----------

1) Export credentials (or pass via CLI flags):

```
export WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
export WHATSAPP_TOKEN=your_long_lived_token
export WHATSAPP_APP_SECRET=your_app_secret          # optional, enables webhook signature verification
export WHATSAPP_VERIFY_TOKEN=your_verify_token      # used by webhook GET challenge
```

2) Install dependencies inside `whatsapp-python-bridge`:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: pip install -e .  # if you prefer editable imports instead of sys.path tweak in tests
```

3) Send a text message (builds idempotency key if you omit one):

```
python -m whatsapp_python_bridge.cli send-text \
  --to 15551234567 \
  --text "Hello from Python"
```

4) Run the webhook server (FastAPI + uvicorn):

```
python -m whatsapp_python_bridge.cli runserver --host 0.0.0.0 --port 8080
```

All entrypoints expose `--help` to see available options.

Webhooks
--------
- Ensure `.env` is present so the server knows your `WHATSAPP_VERIFY_TOKEN`.
- Expose the server via HTTPS (e.g., `ngrok http 8080`) and configure the callback URL + verify token in Meta > WhatsApp > Configuration.
- Incoming webhook payloads are logged to stdout by default for debugging; remove/change once verified.

Environment
-----------

Create a `.env` file (see `.env.example`) so the CLI/server auto-load credentials:

```
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_TOKEN=...
WHATSAPP_APP_SECRET=...
WHATSAPP_VERIFY_TOKEN=...
```
