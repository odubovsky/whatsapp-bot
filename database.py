"""
Database Management Module

Manages all SQLite database operations including message storage,
session memory, configurable rotation cleanup, and WhatsApp device session.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager
import pytz


class Database:
    """SQLite database manager with rotation and session handling"""

    def __init__(self, db_path: str = "store/whatsapp_bot.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """Create database connection with optimizations"""
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow multi-threaded access
            timeout=10.0
        )
        self.conn.row_factory = sqlite3.Row  # Dict-like access

        # Performance optimizations
        self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")

    def initialize(self):
        """Create tables and indexes if not exist"""
        cursor = self.conn.cursor()

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_jid TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT,
                timestamp TIMESTAMP NOT NULL,
                is_from_me BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp
            ON messages(chat_jid, timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON messages(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sender
            ON messages(sender)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed
            ON messages(processed)
        """)

        # Chat sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_jid TEXT NOT NULL,
                chat_jid TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON chat_sessions(expires_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_chat
            ON chat_sessions(user_jid, chat_jid)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_activity
            ON chat_sessions(last_activity DESC)
        """)

        # WhatsApp device session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_device (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                session_data TEXT NOT NULL,
                last_connected TIMESTAMP NOT NULL
            )
        """)

        # App state table (for config hash, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

        # Run schema migration if needed
        self.migrate_schema_v2()

        # Clear pending messages on startup (start fresh)
        self.clear_pending_messages_on_startup()

    def migrate_schema_v2(self):
        """Migrate schema to add processing state columns"""
        import logging
        logger = logging.getLogger(__name__)

        cursor = self.conn.cursor()

        # Check current columns
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]

        migration_needed = False

        # Add each column individually if missing
        if 'processing_status' not in columns:
            logger.info("Adding processing_status column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN processing_status INTEGER DEFAULT 0")
            migration_needed = True

        if 'processing_started_at' not in columns:
            logger.info("Adding processing_started_at column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN processing_started_at TIMESTAMP")
            migration_needed = True

        if 'processing_completed_at' not in columns:
            logger.info("Adding processing_completed_at column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN processing_completed_at TIMESTAMP")
            migration_needed = True

        if 'synced_at' not in columns:
            logger.info("Adding synced_at column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN synced_at TIMESTAMP")
            migration_needed = True

        if 'retry_count' not in columns:
            logger.info("Adding retry_count column...")
            cursor.execute("ALTER TABLE messages ADD COLUMN retry_count INTEGER DEFAULT 0")
            migration_needed = True

        if migration_needed:
            logger.info("Creating indexes...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_status
                ON messages(processing_status, timestamp)
            """)

            logger.info("Migrating existing data...")
            cursor.execute("UPDATE messages SET synced_at = created_at WHERE synced_at IS NULL")
            cursor.execute("UPDATE messages SET processing_status = 2 WHERE processed = 1")

            self.conn.commit()
            logger.info("✅ Schema migration complete")

    def clear_pending_messages_on_startup(self):
        """Mark all pending/in-progress messages as completed and clear all sessions on startup to start fresh"""
        import logging
        logger = logging.getLogger(__name__)

        cursor = self.conn.cursor()

        # Count pending messages
        cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE processing_status IN (0, 1)
        """)
        pending_count = cursor.fetchone()[0]

        # Count existing sessions
        cursor.execute("SELECT COUNT(*) FROM chat_sessions")
        session_count = cursor.fetchone()[0]

        if pending_count > 0 or session_count > 0:
            logger.info(f"Clearing {pending_count} pending message(s) and {session_count} session(s) from previous run...")

            # Mark all pending/in-progress messages as completed
            if pending_count > 0:
                cursor.execute("""
                    UPDATE messages
                    SET processing_status = 2,
                        processing_completed_at = CURRENT_TIMESTAMP,
                        processed = 1
                    WHERE processing_status IN (0, 1)
                """)

            # Delete all chat sessions to start fresh
            if session_count > 0:
                cursor.execute("DELETE FROM chat_sessions")

            self.conn.commit()
            logger.info(f"✅ Cleared {pending_count} pending message(s) and {session_count} session(s) - starting fresh")

    # ==========================================
    # MESSAGE OPERATIONS
    # ==========================================

    def insert_message(self, msg_id: str, chat_jid: str, sender: str,
                       content: str, timestamp: datetime, is_from_me: bool) -> bool:
        """
        Store new message (idempotent - preserves processing state).

        Returns:
            True if new message was inserted, False if message already existed
        """
        cursor = self.conn.cursor()

        # Try to insert new message
        cursor.execute("""
            INSERT OR IGNORE INTO messages
            (id, chat_jid, sender, content, timestamp, is_from_me,
             processing_status, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        """, (msg_id, chat_jid, sender, content, timestamp, is_from_me))

        inserted = cursor.rowcount > 0

        # If message exists, only update synced_at (don't overwrite state)
        if not inserted:
            cursor.execute("""
                UPDATE messages SET synced_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (msg_id,))

        self.conn.commit()
        return inserted

    def get_unprocessed_messages(self, limit: int = 10) -> List[Dict]:
        """
        Get messages that haven't been processed by LLM agent yet.
        Returns recent unprocessed messages from monitored entities.
        Includes own messages (is_from_me=1) for testing/debug purposes.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE processed = 0
            ORDER BY timestamp ASC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def mark_message_processed(self, msg_id: str):
        """Mark message as processed (legacy method - prefer mark_message_completed)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET processed = 1
            WHERE id = ?
        """, (msg_id,))
        self.conn.commit()

    def fetch_and_lock_messages(self, limit: int = 10, timeout_seconds: int = 300) -> List[Dict]:
        """
        Atomically fetch unprocessed messages and mark as processing.
        Includes retry logic for timed-out messages.
        """
        cursor = self.conn.cursor()
        timeout_threshold = datetime.now() - timedelta(seconds=timeout_seconds)

        # Start atomic transaction
        self.conn.execute("BEGIN IMMEDIATE")

        try:
            # Find messages to process (including own messages for testing/triggering bot)
            cursor.execute("""
                SELECT id FROM messages
                WHERE (
                    (processing_status = 0)  -- Fresh messages
                    OR
                    (processing_status = 1 AND processing_started_at < ? AND retry_count < 3)
                )
                ORDER BY timestamp ASC
                LIMIT ?
            """, (timeout_threshold, limit))

            message_ids = [row[0] for row in cursor.fetchall()]

            if not message_ids:
                self.conn.commit()
                return []

            # Mark as processing atomically
            placeholders = ','.join('?' * len(message_ids))
            cursor.execute(f"""
                UPDATE messages
                SET processing_status = 1,
                    processing_started_at = CURRENT_TIMESTAMP,
                    retry_count = retry_count + 1
                WHERE id IN ({placeholders})
            """, message_ids)

            # Fetch full data
            cursor.execute(f"""
                SELECT * FROM messages WHERE id IN ({placeholders}) ORDER BY timestamp ASC
            """, message_ids)

            messages = [dict(row) for row in cursor.fetchall()]
            self.conn.commit()
            return messages

        except Exception as e:
            self.conn.rollback()
            raise

    def mark_message_completed(self, msg_id: str):
        """Mark message as successfully processed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET processing_status = 2,
                processing_completed_at = CURRENT_TIMESTAMP,
                processed = 1
            WHERE id = ?
        """, (msg_id,))
        self.conn.commit()

    def mark_message_failed(self, msg_id: str, max_retries: int = 3):
        """Mark message as failed (retry if under limit)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET processing_status = CASE
                WHEN retry_count < ? THEN 0
                ELSE 3
            END
            WHERE id = ?
        """, (max_retries, msg_id))
        self.conn.commit()

    def get_messages_for_chat(self, chat_jid: str, limit: int = 50) -> List[Dict]:
        """Get recent messages from specific chat"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE chat_jid = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (chat_jid, limit))

        return [dict(row) for row in cursor.fetchall()]

    def has_unprocessed_message_after(self, chat_jid: str, after_timestamp,
                                      sender: Optional[str] = None) -> bool:
        """Check if there is an unprocessed incoming message after the provided timestamp."""
        # Normalize timestamp to string for SQLite comparison
        ts_value = after_timestamp
        try:
            if hasattr(after_timestamp, "isoformat"):
                ts_value = after_timestamp.isoformat()
        except Exception:
            pass

        cursor = self.conn.cursor()
        params = [chat_jid, ts_value]
        sender_clause = ""
        if sender:
            sender_clause = "AND sender = ?"
            params.append(sender)

        cursor.execute(f"""
            SELECT 1 FROM messages
            WHERE chat_jid = ?
              AND processed = 0
              AND is_from_me = 0
              AND timestamp > ?
              {sender_clause}
            LIMIT 1
        """, params)

        return cursor.fetchone() is not None

    # ==========================================
    # MESSAGE ROTATION / CLEANUP
    # ==========================================

    def cleanup_old_messages(self, retention_days: int) -> int:
        """
        Delete messages older than configured retention period.
        Called periodically by background task.
        """
        cutoff = datetime.now() - timedelta(days=retention_days)

        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM messages
            WHERE created_at < ?
        """, (cutoff,))

        deleted = cursor.rowcount
        self.conn.commit()

        return deleted

    # ==========================================
    # SESSION MEMORY OPERATIONS
    # ==========================================

    def get_or_create_session(self, user_jid: str, chat_jid: str,
                               session_memory_config, aliases: Optional[List[str]] = None,
                               current_time: Optional[datetime] = None) -> Dict:
        """
        Get active session or create new one.
        Handles expiry calculation based on config.

        Args:
            user_jid: Primary user identifier for the session
            chat_jid: Chat identifier
            session_memory_config: Session memory settings
            aliases: Optional additional identifiers that should map to the same session
            current_time: Timestamp of the triggering message (UTC aware preferred)
        """
        # Build candidate identifiers (primary first)
        candidate_ids = [user_jid]
        if aliases:
            for a in aliases:
                if a not in candidate_ids:
                    candidate_ids.append(a)

        # Try to get existing session, but verify expiry in Python to avoid
        # timezone/string comparison surprises in SQLite.
        cursor = self.conn.cursor()
        placeholders = ",".join("?" for _ in candidate_ids)
        cursor.execute(f"""
            SELECT * FROM chat_sessions
            WHERE user_jid IN ({placeholders}) AND chat_jid = ?
            ORDER BY created_at DESC
        """, (*candidate_ids, chat_jid))

        now_utc = self._to_utc(self._parse_datetime(current_time)) or datetime.now(pytz.utc)
        for row in cursor.fetchall():
            expires_at = self._to_utc(self._parse_datetime(row["expires_at"]))
            if expires_at and expires_at > now_utc:
                return dict(row)
            # Drop expired sessions so they don't leak context
            self._delete_session(row["session_id"])

        # Create new session
        created_at = now_utc
        session_id = f"{user_jid}_{chat_jid}_{int(created_at.timestamp())}"
        expires_at = self._calculate_session_expiry(created_at, session_memory_config)

        cursor.execute("""
            INSERT INTO chat_sessions
            (session_id, user_jid, chat_jid, context, created_at, expires_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_jid,
            chat_jid,
            "[]",
            created_at.isoformat(),
            expires_at.isoformat(),
            created_at.isoformat()
        ))

        self.conn.commit()

        return {
            "session_id": session_id,
            "user_jid": user_jid,
            "chat_jid": chat_jid,
            "context": "[]",
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_activity": created_at.isoformat()
        }

    def _calculate_session_expiry(self, base_time: datetime,
                                   session_memory_config) -> datetime:
        """
        Calculate session expiry based on config mode:
        - 'time': Expire at specific time (e.g., 2:00 AM)
        - 'duration': Expire X hours after creation
        - 'same_day': Expire at midnight
        """
        tz = session_memory_config.get_timezone()
        # Work in configured timezone, then convert back to UTC for storage
        base_time = self._to_utc(base_time) or datetime.now(pytz.utc)
        created_local = base_time.astimezone(tz)

        if session_memory_config.reset_mode == "time":
            # Parse reset time (e.g., "02:00")
            reset_hour, reset_minute = map(int, session_memory_config.reset_time.split(":"))

            # Calculate next occurrence of reset time
            reset_today = created_local.replace(hour=reset_hour, minute=reset_minute,
                                               second=0, microsecond=0)

            if created_local < reset_today:
                expiry_local = reset_today
            else:
                expiry_local = reset_today + timedelta(days=1)

        elif session_memory_config.reset_mode == "duration":
            # Expire X minutes/hours after the provided base time
            duration_minutes = session_memory_config.get_duration_minutes()
            if duration_minutes is None:
                raise ValueError("Duration-based session memory requires reset_hours or reset_minutes")
            expiry_local = created_local + timedelta(minutes=duration_minutes)

        elif session_memory_config.reset_mode == "same_day":
            # Expire at midnight
            expiry_local = (created_local + timedelta(days=1)).replace(hour=0, minute=0,
                                                                       second=0, microsecond=0)

        else:
            raise ValueError(f"Unknown reset_mode: {session_memory_config.reset_mode}")

        return expiry_local.astimezone(pytz.utc)

    def update_session_context(self, session_id: str, context: List[Dict],
                               session_memory_config, activity_time: Optional[datetime] = None):
        """
        Update session conversation context and advance expiry based on latest activity.
        """
        now = self._to_utc(self._parse_datetime(activity_time)) or datetime.now(pytz.utc)
        expires_at = self._calculate_session_expiry(now, session_memory_config)
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE chat_sessions
            SET context = ?, last_activity = ?, expires_at = ?
            WHERE session_id = ?
        """, (json.dumps(context), now.isoformat(), expires_at.isoformat(), session_id))
        self.conn.commit()

    def get_session_context(self, session_id: str) -> List[Dict]:
        """Get conversation context for session"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context FROM chat_sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        if row and row["context"]:
            return json.loads(row["context"])
        return []

    def cleanup_expired_sessions(self) -> int:
        """Delete sessions past their expiry time"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_id, expires_at FROM chat_sessions
        """)

        now_utc = datetime.now(pytz.utc)
        expired_ids = []
        for row in cursor.fetchall():
            expires_at = self._to_utc(self._parse_datetime(row["expires_at"]))
            if expires_at and expires_at < now_utc:
                expired_ids.append(row["session_id"])

        for session_id in expired_ids:
            cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))

        self.conn.commit()

        return len(expired_ids)

    def reset_stale_session(self, user_jid: str, chat_jid: str,
                            stale_after_seconds: int = 600) -> bool:
        """
        Delete the most recent session if its last_activity is older than the given age.
        Useful for self-debug chats to avoid pulling ancient context on the first message.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_id, last_activity
            FROM chat_sessions
            WHERE user_jid = ? AND chat_jid = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_jid, chat_jid))

        row = cursor.fetchone()
        if not row:
            return False

        last_activity = self._to_utc(self._parse_datetime(row["last_activity"]))
        if not last_activity:
            return False

        age = datetime.now(pytz.utc) - last_activity
        if age.total_seconds() > stale_after_seconds:
            self._delete_session(row["session_id"])
            return True

        return False

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from DB values (handles strings with/without timezone)"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value)
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

    def _to_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is timezone-aware UTC"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(pytz.utc)

    def _delete_session(self, session_id: str):
        """Delete a single session by id"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        self.conn.commit()

    # ==========================================
    # APP STATE (CONFIG HASH)
    # ==========================================

    def get_config_hash(self) -> Optional[str]:
        """Get stored config hash from app_state"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM app_state WHERE key = 'config_hash'")
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_config_hash(self, hash_value: str):
        """Store config hash in app_state"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO app_state (key, value, updated_at)
            VALUES ('config_hash', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """, (hash_value,))
        self.conn.commit()

    # ==========================================
    # WHATSAPP DEVICE SESSION
    # ==========================================

    def save_whatsapp_session(self, session_data: str):
        """Save WhatsApp authentication session"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO whatsapp_device
            (id, session_data, last_connected)
            VALUES (1, ?, ?)
        """, (session_data, datetime.now()))
        self.conn.commit()

    def load_whatsapp_session(self) -> Optional[str]:
        """Load WhatsApp authentication session"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_data FROM whatsapp_device WHERE id = 1
        """)

        row = cursor.fetchone()
        return row["session_data"] if row else None

    def clear_whatsapp_session(self):
        """Clear WhatsApp session (force re-authentication)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM whatsapp_device WHERE id = 1")
        self.conn.commit()

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM messages")
        message_count = cursor.fetchone()["count"]

        cursor.execute("SELECT expires_at FROM chat_sessions")
        now_utc = datetime.now(pytz.utc)
        active_sessions = 0
        for row in cursor.fetchall():
            expires_at = self._to_utc(self._parse_datetime(row["expires_at"]))
            if expires_at and expires_at > now_utc:
                active_sessions += 1

        cursor.execute("SELECT last_connected FROM whatsapp_device WHERE id = 1")
        row = cursor.fetchone()
        last_connected = row["last_connected"] if row else None

        # Get database file size
        cursor.execute("""
            SELECT page_count * page_size as size
            FROM pragma_page_count(), pragma_page_size()
        """)
        db_size = cursor.fetchone()["size"]

        return {
            "total_messages": message_count,
            "active_sessions": active_sessions,
            "last_whatsapp_connection": last_connected,
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / 1024 / 1024, 2)
        }

    def sync_from_go_bridge(self, bridge_db_path: str = "whatsapp-bridge/store/messages.db",
                            monitored_jids: List[str] = None,
                            include_own_messages: bool = True,
                            lookback_hours: int = 24) -> int:
        """
        Sync messages using lookback window instead of MAX(timestamp).
        Handles out-of-order message delivery correctly.

        Args:
            bridge_db_path: Path to Go bridge messages database
            monitored_jids: List of JIDs to monitor (only sync these chats)
            include_own_messages: If True, sync messages you sent to yourself (for testing/debug)
            lookback_hours: Hours to look back for messages (default 24)

        Returns:
            Number of new messages synced
        """
        import os

        if not os.path.exists(bridge_db_path):
            return 0

        # Connect to Go bridge database (read-only)
        bridge_conn = sqlite3.connect(f"file:{bridge_db_path}?mode=ro", uri=True)
        bridge_conn.row_factory = sqlite3.Row
        bridge_cursor = bridge_conn.cursor()

        try:
            # Use lookback window instead of MAX(timestamp)
            lookback_threshold = datetime.now() - timedelta(hours=lookback_hours)

            # Build query to get messages from monitored chats
            if monitored_jids:
                placeholders = ",".join("?" * len(monitored_jids))
                if include_own_messages:
                    # Include both incoming messages AND messages sent to monitored JIDs
                    query = f"""
                        SELECT id, chat_jid, sender, content, timestamp, is_from_me
                        FROM messages
                        WHERE timestamp > ?
                        AND chat_jid IN ({placeholders})
                        ORDER BY timestamp ASC
                    """
                else:
                    # Only incoming messages (original behavior)
                    query = f"""
                        SELECT id, chat_jid, sender, content, timestamp, is_from_me
                        FROM messages
                        WHERE timestamp > ?
                        AND chat_jid IN ({placeholders})
                        AND is_from_me = 0
                        ORDER BY timestamp ASC
                    """
                params = [lookback_threshold] + monitored_jids
            else:
                if include_own_messages:
                    query = """
                        SELECT id, chat_jid, sender, content, timestamp, is_from_me
                        FROM messages
                        WHERE timestamp > ?
                        ORDER BY timestamp ASC
                    """
                else:
                    query = """
                        SELECT id, chat_jid, sender, content, timestamp, is_from_me
                        FROM messages
                        WHERE timestamp > ?
                        AND is_from_me = 0
                        ORDER BY timestamp ASC
                    """
                params = [lookback_threshold]

            bridge_cursor.execute(query, params)
            bridge_messages = bridge_cursor.fetchall()

            synced_count = 0
            for msg in bridge_messages:
                # Insert into our database (INSERT OR IGNORE preserves state)
                try:
                    inserted = self.insert_message(
                        msg_id=msg["id"],
                        chat_jid=msg["chat_jid"],
                        sender=msg["sender"],
                        content=msg["content"] or "",
                        timestamp=msg["timestamp"],
                        is_from_me=msg["is_from_me"]
                    )
                    if inserted:
                        synced_count += 1
                except sqlite3.IntegrityError:
                    # Message already exists, skip
                    pass

            return synced_count

        finally:
            bridge_conn.close()

    def vacuum(self):
        """Optimize database (reclaim space after deletions)"""
        self.conn.execute("VACUUM")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Test database initialization
    import os

    # Use test database
    test_db = "store/test_whatsapp_bot.db"
    os.makedirs("store", exist_ok=True)

    db = Database(test_db)
    db.initialize()

    print("✅ Database initialized successfully")
    stats = db.get_stats()
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Database size: {stats['database_size_mb']} MB")

    db.close()
    os.remove(test_db)
    print("✅ Test database cleaned up")
