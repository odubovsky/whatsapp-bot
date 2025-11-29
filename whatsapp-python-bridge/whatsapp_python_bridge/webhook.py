import json
import logging
from datetime import datetime
from typing import Callable, Optional

from fastapi import FastAPI, Header, HTTPException, Request

from .client import verify_signature, WhatsAppCloudClient
from .config import WhatsAppConfig

logger = logging.getLogger(__name__)
WebhookHandler = Callable[[dict], None]


def create_app(
    config: WhatsAppConfig,
    client: WhatsAppCloudClient,
    on_message: Optional[WebhookHandler] = None,
) -> FastAPI:
    """Create FastAPI app with verification + webhook handlers."""
    app = FastAPI(title="WhatsApp Cloud API Bridge", version="0.1.0")

    @app.get("/webhook")
    async def verify(mode: str, challenge: str, token: str):
        if mode == "subscribe" and config.verify_token and token == config.verify_token:
            return int(challenge)
        raise HTTPException(status_code=403, detail="Verification failed")

    @app.post("/webhook")
    async def handle(
        request: Request,
        x_hub_signature_256: str | None = Header(default=None),
    ):
        body = await request.body()

        if config.app_secret:
            if not verify_signature(config.app_secret, body, x_hub_signature_256 or ""):
                raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Parse and print incoming messages to STDOUT
        _parse_and_print_messages(payload)

        if on_message:
            on_message(payload)

        return {"status": "received"}

    return app


def _parse_and_print_messages(payload: dict) -> None:
    """Parse webhook payload and print messages to STDOUT."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                msg_id = msg.get("id", "")
                from_phone = msg.get("from", "")
                timestamp = msg.get("timestamp", "")
                msg_type = msg.get("type", "unknown")

                # Convert phone to JID format
                chat_jid = f"{from_phone}@s.whatsapp.net"

                # Extract content based on type
                content = ""
                media_type = None

                if msg_type == "text":
                    content = msg.get("text", {}).get("body", "")
                elif msg_type in ["image", "video", "audio", "document"]:
                    media_type = msg_type
                    media_id = msg.get(msg_type, {}).get("id", "")
                    content = msg.get(msg_type, {}).get("caption", f"[{msg_type} media: {media_id}]")

                # Get contact name if available
                contacts = value.get("contacts", [])
                display_name = contacts[0].get("profile", {}).get("name", from_phone) if contacts else from_phone

                # Convert timestamp to readable format
                dt = datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.now()
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                # Print to STDOUT
                print(f"\n{'='*60}")
                print(f"📨 Incoming Message")
                print(f"{'='*60}")
                print(f"Message ID:  {msg_id}")
                print(f"From:        {display_name}")
                print(f"Phone:       {from_phone}")
                print(f"JID:         {chat_jid}")
                print(f"Type:        {msg_type}")
                print(f"Timestamp:   {timestamp_str}")
                if media_type:
                    print(f"Media Type:  {media_type}")
                print(f"Content:     {content}")
                print(f"{'='*60}\n")

                logger.info(f"Received message from {chat_jid}: {content[:50]}...")
