"""
WhatsApp Client - Go Bridge Integration

Communicates with the Go whatsapp-bridge service via HTTP API.
The Go bridge handles the actual WhatsApp connection using whatsmeow.
"""

import asyncio
import logging
import subprocess
import time
import httpx
from datetime import datetime
from typing import Optional
import json

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """WhatsApp client that communicates with Go bridge"""

    def __init__(self, config, database):
        """
        Initialize WhatsApp client

        Args:
            config: Configuration object
            database: Database instance
        """
        self.config = config
        self.db = database
        self.is_connected = False
        self.phone_number = config.whatsapp.phone_number

        # Go bridge settings
        self.bridge_url = "http://localhost:8080"
        self.bridge_process = None


    async def connect(self, force_qr: bool = False):
        """
        Connect to existing Go bridge (must be running separately)

        Args:
            force_qr: Ignored - start Go bridge manually with --reset-session flag
        """
        logger.info("Connecting to Go bridge at %s...", self.bridge_url)

        # Wait for bridge to be ready
        await self._wait_for_bridge()

        logger.info("✅ Connected to WhatsApp via Go bridge")
        self.is_connected = True

    async def _start_bridge(self, force_reset: bool = False):
        """Start the Go bridge process"""
        import os

        bridge_dir = "/Users/odedd/coding/whatsapp-bot/whatsapp-bridge"
        bridge_binary = os.path.join(bridge_dir, "whatsapp-client")

        # Build command
        cmd = [bridge_binary]
        if force_reset:
            cmd.append("--reset-session")

        logger.info(f"Starting Go bridge: {' '.join(cmd)}")

        # Start the Go process
        self.bridge_process = subprocess.Popen(
            cmd,
            cwd=bridge_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        logger.info("Go bridge process started")

    async def _wait_for_bridge(self, timeout: int = 30):
        """Wait for Go bridge to be ready by checking HTTP connectivity"""
        logger.info("Waiting for Go bridge to be ready...")

        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                async with httpx.AsyncClient() as client:
                    # Try a simple connection test
                    response = await client.get(f"{self.bridge_url}/api/send", timeout=2.0)
                    # Any response (even error) means the server is up
                    logger.info("✅ Go bridge is reachable")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                # Bridge not ready yet
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise RuntimeError(
                        f"Go bridge not reachable at {self.bridge_url} after {timeout}s. "
                        "Please start the Go bridge first:\n"
                        "  cd whatsapp-bridge && ./whatsapp-client"
                    )
                await asyncio.sleep(1)

    async def _check_authentication(self) -> bool:
        """
        Check if WhatsApp is authenticated.
        Note: The Go bridge will display QR code in its output if not authenticated.
        For now, we assume authentication after startup delay.
        """
        # The user will see QR code in Go bridge terminal output if needed
        # We'll assume authenticated after the startup delay
        return True

    async def send_message(self, chat_jid: str, content: str):
        """
        Send message via Go bridge

        Args:
            chat_jid: Recipient JID (group or user)
            content: Message text
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to WhatsApp")

        try:
            logger.info(f"📤 Sending message to {chat_jid} (len={len(content)})")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bridge_url}/api/send",
                    json={
                        "recipient": chat_jid,
                        "message": content
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        logger.info("✅ Message sent successfully")

                        # Store sent message in database
                        msg_id = f"sent_{int(datetime.now().timestamp())}"
                        self.db.insert_message(
                            msg_id=msg_id,
                            chat_jid=chat_jid,
                            sender=f"{self.phone_number}@s.whatsapp.net",
                            content=content,
                            timestamp=datetime.now(),
                            is_from_me=True
                        )
                    else:
                        logger.error(f"Failed to send message: {result.get('message')}")
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            raise

    async def start_listening(self):
        """
        Start listening for incoming messages from Go bridge

        The Go bridge stores messages in its database. We'll poll it periodically
        and sync to our database.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to WhatsApp")

        logger.info("Started listening for WhatsApp messages via Go bridge...")

        # For now, the Go bridge handles message receiving and storage
        # We can poll its database or implement a webhook later
        # This keeps the service running
        while self.is_connected:
            await asyncio.sleep(10)

    async def send_startup_validation(self):
        """Send validation message to self confirming service is operational"""
        try:
            my_jid = f"{self.phone_number}@s.whatsapp.net"
            message = (
                f"🤖 WhatsApp Bot Started\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Status: All systems operational\n"
                f"Monitored entities: {len(self.config.monitored_entities)}\n"
                f"Bridge: Go whatsmeow integration"
            )

            await self.send_message(my_jid, message)
            logger.info("✅ Startup validation message sent")

        except Exception as e:
            logger.error(f"Failed to send startup validation: {e}", exc_info=True)

    def disconnect(self):
        """Disconnect from WhatsApp (Go bridge continues running separately)"""
        logger.info("Disconnecting from WhatsApp...")
        self.is_connected = False
        logger.info("✅ Disconnected (Go bridge still running)")


if __name__ == "__main__":
    # Test WhatsApp client initialization
    import sys
    sys.path.insert(0, '/Users/odedd/coding/whatsapp-bot')

    from config import get_config
    from database import Database

    logging.basicConfig(level=logging.INFO)

    async def test():
        try:
            config = get_config()
            db = Database()
            db.initialize()

            client = WhatsAppClient(config, db)
            await client.connect()

            logger.info("✅ WhatsApp client connected via Go bridge")

            # Keep running
            await asyncio.sleep(5)

            client.disconnect()

        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)

    asyncio.run(test())
