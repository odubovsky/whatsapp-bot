"""
Vitality Checker Module

Schedules and sends daily health check messages to confirm the service is operational.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class VitalityChecker:
    """Daily health check scheduler"""

    def __init__(self, config, whatsapp_client):
        """
        Initialize vitality checker

        Args:
            config: Configuration object
            whatsapp_client: WhatsApp client instance
        """
        self.config = config
        self.whatsapp = whatsapp_client
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the vitality check scheduler"""
        if not self.config.vitality.enabled:
            logger.info("Vitality checks disabled in config")
            return

        try:
            # Parse time (HH:MM format)
            hour, minute = map(int, self.config.vitality.time.split(":"))

            # Create cron trigger
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.config.vitality.get_timezone()
            )

            # Schedule the job
            self.scheduler.add_job(
                self.send_vitality_message,
                trigger=trigger,
                id="vitality_check",
                name="Daily Vitality Check",
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            logger.info(f"✅ Vitality checker started")
            logger.info(f"  Schedule: Daily at {self.config.vitality.time}")
            logger.info(f"  Timezone: {self.config.vitality.timezone}")

        except Exception as e:
            logger.error(f"Error starting vitality checker: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop the vitality check scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Vitality checker stopped")

    async def send_vitality_message(self):
        """Send daily health check message to self"""
        try:
            logger.info("Sending daily vitality check message...")

            # Get own JID
            my_jid = f"{self.config.whatsapp.phone_number}@s.whatsapp.net"

            # Prepare message
            message = f"{self.config.vitality.message}\n"
            message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Send via WhatsApp
            await self.whatsapp.send_message(my_jid, message)

            logger.info("✅ Vitality check message sent")

        except Exception as e:
            logger.error(f"Error sending vitality message: {e}", exc_info=True)


if __name__ == "__main__":
    # Test vitality checker
    import asyncio
    from config import get_config
    from database import Database
    from whatsapp_client import WhatsAppClient

    logging.basicConfig(level=logging.INFO)

    async def test():
        try:
            config = get_config()
            db = Database()
            db.initialize()

            whatsapp = WhatsAppClient(config, db)
            checker = VitalityChecker(config, whatsapp)

            logger.info("✅ Vitality checker initialized")

            if config.vitality.enabled:
                logger.info(f"  Enabled: Yes")
                logger.info(f"  Schedule: Daily at {config.vitality.time}")
                logger.info(f"  Timezone: {config.vitality.timezone}")
                logger.info(f"  Message: {config.vitality.message}")
            else:
                logger.info(f"  Enabled: No")

        except Exception as e:
            logger.error(f"❌ Error: {e}")

    asyncio.run(test())
