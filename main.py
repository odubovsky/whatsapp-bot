#!/usr/bin/env python3
"""
WhatsApp Bot - Main Entry Point

AI-powered WhatsApp message responder that monitors configured groups/users
and responds using Perplexity AI with configurable prompts per entity.
"""

import asyncio
import argparse
import signal
import logging
import sys
from datetime import timedelta
import hashlib
from pathlib import Path
from colorlog import ColoredFormatter

from config import get_config, reload_config
from database import Database
from whatsapp_client import WhatsAppClient
from message_agent import MessageAgent
from vitality_checker import VitalityChecker

# Global state for graceful shutdown
shutdown_event = asyncio.Event()


def setup_logging(log_level: str, log_file: str = None, quiet: bool = False):
    """
    Setup logging configuration

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        quiet: Suppress all output except errors
    """
    if quiet:
        log_level = "ERROR"

    # Create formatter
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(file_handler)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser with all options"""
    parser = argparse.ArgumentParser(
        description="WhatsApp Bot - AI-powered message responder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Run normally with configs
  %(prog)s --reset-session              Force QR code re-authentication
  %(prog)s --reset-db                   Clear all messages and sessions
  %(prog)s --qr-only                    Show QR code and exit
  %(prog)s --config custom.json         Use custom config file
  %(prog)s --log-level DEBUG            Enable debug logging
  %(prog)s --no-vitality                Disable daily health checks
  %(prog)s --dry-run                    Test config without connecting

Configuration:
  Edit .env for API keys (PERPLEXITY_API_KEY)
  Edit app.json for groups, users, prompts, schedules

For more info: https://github.com/yourusername/whatsapp-bot
        """
    )

    # Connection options
    conn_group = parser.add_argument_group('Connection Options')
    conn_group.add_argument(
        '--reset-session',
        action='store_true',
        help='Force WhatsApp re-authentication (clear stored session)'
    )
    conn_group.add_argument(
        '--qr-only',
        action='store_true',
        help='Display QR code for authentication and exit (no service start)'
    )

    # Database options
    db_group = parser.add_argument_group('Database Options')
    db_group.add_argument(
        '--reset-db',
        action='store_true',
        help='Clear all messages and sessions (keep WhatsApp session)'
    )
    db_group.add_argument(
        '--db-path',
        type=str,
        metavar='PATH',
        help='Custom database path (default: store/whatsapp_bot.db)'
    )
    db_group.add_argument(
        '--show-stats',
        action='store_true',
        help='Display database statistics and exit'
    )

    # Configuration options
    config_group = parser.add_argument_group('Configuration Options')
    config_group.add_argument(
        '--config',
        type=str,
        metavar='FILE',
        default='app.json',
        help='Path to config file (default: app.json)'
    )
    config_group.add_argument(
        '--env-file',
        type=str,
        metavar='FILE',
        default='.env',
        help='Path to .env file (default: .env)'
    )
    config_group.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate configuration and exit'
    )

    # Service options
    service_group = parser.add_argument_group('Service Options')
    service_group.add_argument(
        '--no-vitality',
        action='store_true',
        help='Disable daily vitality health check messages'
    )
    service_group.add_argument(
        '--no-polling',
        action='store_true',
        help='Disable message polling agent (receive only mode)'
    )
    service_group.add_argument(
        '--no-startup-validation',
        action='store_true',
        help='Skip sending startup validation message to yourself'
    )
    service_group.add_argument(
        '--polling-interval',
        type=int,
        metavar='SECONDS',
        help='Override polling interval from config (in seconds)'
    )

    # Logging options
    log_group = parser.add_argument_group('Logging Options')
    log_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level (overrides .env LOG_LEVEL)'
    )
    log_group.add_argument(
        '--log-file',
        type=str,
        metavar='FILE',
        help='Write logs to file (default: stdout only)'
    )
    log_group.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )

    # Testing/debugging options
    test_group = parser.add_argument_group('Testing Options')
    test_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Test configuration without connecting to WhatsApp'
    )
    test_group.add_argument(
        '--send-test',
        type=str,
        metavar='MESSAGE',
        help='Send test message to yourself and exit'
    )

    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    return parser


def validate_and_exit(args):
    """Validate configuration and exit"""
    logger = logging.getLogger(__name__)
    try:
        config = get_config(args.config, args.env_file)
        logger.info("✅ Configuration valid")
        logger.info(f"  Phone: {config.whatsapp.phone_number}")
        logger.info(f"  Monitored entities: {len(config.monitored_entities)}")
        logger.info(f"  Polling interval: {config.polling.interval_seconds}s")
        logger.info(f"  Session memory mode: {config.session_memory.reset_mode}")
        logger.info(f"  Vitality enabled: {config.vitality.enabled}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)


def show_stats_and_exit(args):
    """Display database statistics and exit"""
    logger = logging.getLogger(__name__)
    try:
        db_path = args.db_path or "store/whatsapp_bot.db"
        db = Database(db_path)
        stats = db.get_stats()

        logger.info("Database Statistics:")
        logger.info(f"  Total Messages: {stats['total_messages']:,}")
        logger.info(f"  Active Sessions: {stats['active_sessions']}")
        logger.info(f"  Database Size: {stats['database_size_mb']} MB")
        logger.info(f"  Last WhatsApp Connection: {stats['last_whatsapp_connection']}")

        db.close()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


async def send_test_message_and_exit(args, config, whatsapp):
    """Send test message and exit"""
    logger = logging.getLogger(__name__)
    try:
        await whatsapp.connect()
        my_jid = f"{config.whatsapp.phone_number}@s.whatsapp.net"
        await whatsapp.send_message(my_jid, args.send_test)
        logger.info("✅ Test message sent")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error sending test message: {e}")
        sys.exit(1)


async def rotation_cleanup_task(db, config):
    """Background task for message rotation cleanup"""
    logger = logging.getLogger(__name__)

    while not shutdown_event.is_set():
        try:
            # Wait for cleanup interval
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=config.rotation.cleanup_interval_hours * 3600
            )
        except asyncio.TimeoutError:
            # Timeout means it's time to cleanup
            pass

        if shutdown_event.is_set():
            break

        try:
            logger.info("Running message rotation cleanup...")
            deleted_messages = db.cleanup_old_messages(
                config.rotation.messages_retention_days
            )
            deleted_sessions = db.cleanup_expired_sessions()

            logger.info(f"✅ Cleanup complete: {deleted_messages} messages, "
                       f"{deleted_sessions} sessions deleted")

        except Exception as e:
            logger.error(f"Error in rotation cleanup: {e}", exc_info=True)


async def run_service(args):
    """Main service loop"""
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = get_config(args.config, args.env_file)

        # Override polling interval if specified
        if args.polling_interval:
            config.polling.interval_seconds = args.polling_interval

        # Override vitality if specified
        if args.no_vitality:
            config.vitality.enabled = False

        # Initialize database
        db_path = args.db_path or config.database_path
        db = Database(db_path)
        db.initialize()
        logger.info("✅ Database initialized")

        # Store initial config hash
        try:
            cfg_path = Path(config.config_file)
            cfg_hash = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
            db.set_config_hash(cfg_hash)
            logger.info(f"Config hash recorded: {cfg_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Could not record config hash: {e}")

        # Reset database if requested
        if args.reset_db:
            logger.warning("Resetting database...")
            db.cleanup_old_messages(0)  # Delete all messages
            db.cleanup_expired_sessions()  # Delete all sessions
            logger.info("✅ Database reset complete")

        # Initialize WhatsApp client
        whatsapp = WhatsAppClient(config, db)

        # QR-only mode
        if args.qr_only:
            await whatsapp.connect(force_qr=True)
            logger.info("✅ QR code displayed. Scan and restart service normally.")
            sys.exit(0)

        # Dry-run mode
        if args.dry_run:
            logger.info("[DRY RUN] Configuration loaded")
            logger.info("[DRY RUN] Database initialized")
            logger.info(f"[DRY RUN] {len(config.monitored_entities)} monitored entities")
            logger.info("[DRY RUN] Would connect to WhatsApp (skipped)")
            logger.info("[DRY RUN] All checks passed")
            sys.exit(0)

        # Send test message if requested
        if args.send_test:
            await send_test_message_and_exit(args, config, whatsapp)

        # Connect to WhatsApp
        await whatsapp.connect(force_qr=args.reset_session)

        # Send startup validation message (unless disabled)
        if not args.no_startup_validation:
            await whatsapp.send_startup_validation()

        # Initialize message agent
        message_agent = None
        if not args.no_polling:
            message_agent = MessageAgent(config, db, whatsapp)

        # Initialize vitality checker
        vitality_checker = VitalityChecker(config, whatsapp)
        vitality_checker.start()

        # Create background tasks
        tasks = []

        # WhatsApp message listener
        tasks.append(asyncio.create_task(whatsapp.start_listening()))

        # Message processing agent
        if message_agent:
            tasks.append(asyncio.create_task(message_agent.start()))

        # Rotation cleanup task
        tasks.append(asyncio.create_task(rotation_cleanup_task(db, config)))

        logger.info("=" * 60)
        logger.info("🚀 WhatsApp Bot is now running")
        logger.info("=" * 60)
        logger.info(f"  Phone: {config.whatsapp.phone_number}")
        logger.info(f"  Monitored entities: {len(config.monitored_entities)}")
        logger.info(f"  Polling: {'Enabled' if message_agent else 'Disabled'}")
        logger.info(f"  Vitality checks: {'Enabled' if config.vitality.enabled else 'Disabled'}")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop")
        logger.info("")

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Cleanup
        logger.info("\nShutting down...")
        if message_agent:
            message_agent.stop()
        vitality_checker.stop()
        whatsapp.disconnect()

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        db.close()
        logger.info("✅ Shutdown complete")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


def handle_shutdown(signum, frame):
    """Handle shutdown signals"""
    logger = logging.getLogger(__name__)
    logger.info(f"\nReceived signal {signum}")
    shutdown_event.set()


def main():
    """Main entry point"""
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = args.log_level or "INFO"
    setup_logging(log_level, args.log_file, args.quiet)

    logger = logging.getLogger(__name__)

    # Handle special modes
    if args.validate_config:
        validate_and_exit(args)

    if args.show_stats:
        show_stats_and_exit(args)

    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Run service
    try:
        asyncio.run(run_service(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
