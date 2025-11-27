"""
Message Agent Module

Polls database for new messages, queries Perplexity API with entity-specific prompts
and session memory, then sends responses back via WhatsApp.
"""

import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path

from config import reload_config

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Client for Perplexity API"""

    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        """
        Initialize Perplexity client

        Args:
            api_key: Perplexity API key
            model: Model name
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = "https://api.perplexity.ai"

    async def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Call Perplexity chat completion API

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Assistant's response text

        Raises:
            Exception: If API call fails
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API error: {e.response.status_code} - {e.response.text}")
            logger.error(f"Request payload: {payload}")
            raise Exception(f"Perplexity API returned {e.response.status_code}")

        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}", exc_info=True)
            raise


class MessageAgent:
    """AI response agent"""

    def __init__(self, config, database, whatsapp_client):
        """
        Initialize message agent

        Args:
            config: Configuration object
            database: Database instance
            whatsapp_client: WhatsApp client instance
        """
        self.config = config
        self.db = database
        self.whatsapp = whatsapp_client

        # Initialize Perplexity client
        self.perplexity = PerplexityClient(
            api_key=config.perplexity_api_key,
            model=config.perplexity.model,
            temperature=config.perplexity.temperature,
            max_tokens=config.perplexity.max_tokens
        )

        self.is_running = False
        # For self-debug chats, drop stale sessions older than this to avoid pulling
        # historical context into a new debug exchange.
        self.self_session_stale_seconds = getattr(config.self, "stale_session_seconds", 60)
        # Track last bot responses per chat to avoid re-processing our own replies
        self.last_bot_response = {}
        # Track current config hash
        self.config_hash = None
        self._init_config_hash()
        # Limit the amount of history we send to the model to prevent runaway prompts
        self.max_context_messages = 20
        # Default response delay (seconds) before LLM kicks in
        self.response_delay_default = getattr(config, "response_delay_default", 5)
        # Lock to prevent concurrent polling cycles
        self._processing_lock = asyncio.Lock()

    @staticmethod
    def check_and_strip_wake_word(content: str) -> tuple:
        """
        Check if message starts with wake word and return (has_wake_word, stripped_content).

        Supports multiple variations:
        - English: "hey bot", "hello bot", "hi bot" (case-insensitive)
        - Hebrew: "הי בוט", "היי בוט", "הלו בוט"

        Returns:
            (True, content_without_wake_word) if wake word found
            (False, original_content) if wake word not found

        Examples:
            >>> check_and_strip_wake_word("hey bot what time is it")
            (True, "what time is it")

            >>> check_and_strip_wake_word("hello bot how are you")
            (True, "how are you")

            >>> check_and_strip_wake_word("הי בוט מה השעה")
            (True, "מה השעה")

            >>> check_and_strip_wake_word("היי בוט ספר לי")
            (True, "ספר לי")

            >>> check_and_strip_wake_word("hello everyone")
            (False, "hello everyone")
        """
        if not content or not isinstance(content, str):
            return False, content

        # Normalize: strip whitespace, lowercase for English
        normalized = content.strip()
        normalized_lower = normalized.lower()

        # English wake word variations
        english_wake_words = [
            ("hello bot", 9),  # (pattern, length)
            ("hey bot", 7),
            ("hi bot", 6),
        ]

        for wake_word, length in english_wake_words:
            if normalized_lower.startswith(wake_word):
                # Strip wake word and any following whitespace
                stripped = normalized[length:].lstrip()
                return True, stripped

        # Hebrew wake word variations
        hebrew_wake_words = [
            ("הלו בוט", 7),    # "hello bot" in Hebrew
            ("היי בוט", 7),    # "hey bot" in Hebrew (with extra yod)
            ("הי בוט", 6),     # "hi bot" in Hebrew
        ]

        for wake_word, length in hebrew_wake_words:
            if normalized.startswith(wake_word):
                # Strip wake word and any following whitespace
                stripped = normalized[length:].lstrip()
                return True, stripped

        return False, content

    def _resolve_prompt(self, prompt_value: str, prompt_is_file: bool = False) -> str:
        """Load prompt text, supporting file paths when requested or auto-detected."""
        from pathlib import Path

        if prompt_is_file or ("/" in prompt_value and Path(prompt_value).exists()):
            path = Path(prompt_value)
            try:
                return path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read prompt file {path}: {e}")
                return prompt_value

        return prompt_value

    def _hash_config_file(self) -> Optional[str]:
        """Compute SHA256 hash of the current config file"""
        try:
            config_path = Path(self.config.config_file)
            data = config_path.read_bytes()
            return hashlib.sha256(data).hexdigest()
        except Exception as e:
            logger.warning(f"Unable to hash config file {getattr(self.config, 'config_file', 'app.json')}: {e}")
            return None

    def _maybe_reload_config(self):
        """Reload configuration if app.json hash changed."""
        current_hash = self._hash_config_file()
        if not current_hash:
            return

        stored_hash = None
        try:
            stored_hash = self.db.get_config_hash()
        except Exception:
            logger.warning("Could not read config hash from DB", exc_info=True)

        if stored_hash == current_hash and self.config_hash == current_hash:
            return  # no change

        logger.info("Detected config change, reloading configuration...")
        try:
            new_config = reload_config(self.config.config_file, getattr(self.config, "env_file", ".env"))
            self.config = new_config
            # Rebuild Perplexity client with new settings
            self.perplexity = PerplexityClient(
                api_key=new_config.perplexity_api_key,
                model=new_config.perplexity.model,
                temperature=new_config.perplexity.temperature,
                max_tokens=new_config.perplexity.max_tokens
            )
            self.self_session_stale_seconds = getattr(new_config.self, "stale_session_seconds", 60)
            self.response_delay_default = getattr(new_config, "response_delay_default", 5)
            self.config_hash = current_hash
            self.db.set_config_hash(current_hash)
            logger.info("✅ Config reloaded successfully")
            # Surface a clear notice to main stdout that app.json was refreshed.
            logging.getLogger().info("🔄 app.json refreshed and reloaded")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}", exc_info=True)

    def _init_config_hash(self):
        """Set initial config hash from DB or current file."""
        current_hash = self._hash_config_file()
        if not current_hash:
            return
        try:
            stored_hash = self.db.get_config_hash()
            if stored_hash != current_hash:
                self.db.set_config_hash(current_hash)
            self.config_hash = current_hash
        except Exception:
            logger.warning("Could not initialize config hash in DB", exc_info=True)

    def _parse_timestamp(self, value) -> datetime:
        """Convert timestamps from DB into timezone-aware UTC datetimes."""
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = datetime.fromisoformat(str(value))
            except Exception:
                dt = datetime.utcnow()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _get_session_memory_config(self, chat_jid: str):
        """Return the session memory config for the target chat."""
        return self.config.get_session_memory_for_entity(chat_jid)

    def _prune_context(self, context: List[Dict], session_memory_config, now: datetime) -> List[Dict]:
        """
        Trim context based on session window (duration mode) and hard message count limit.
        Old entries outside the duration window are dropped so stale exchanges are not reused.
        """
        if not context:
            return []

        pruned = []
        cutoff = None
        if session_memory_config.reset_mode == "duration":
            duration_minutes = session_memory_config.get_duration_minutes()
            if duration_minutes:
                cutoff = now - timedelta(minutes=duration_minutes)

        for entry in context:
            if cutoff is None:
                pruned.append(entry)
                continue
            ts_text = entry.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_text) if ts_text else None
            except Exception:
                ts = None
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts is None or ts >= cutoff:
                pruned.append(entry)

        # Keep only the most recent slice to avoid giant prompts
        if len(pruned) > self.max_context_messages:
            pruned = pruned[-self.max_context_messages:]

        return pruned

    def _format_context_for_prompt(self, context: List[Dict]) -> str:
        """Render context as readable lines for debug/system prompt."""
        lines = []
        for entry in context:
            role = entry.get("role", "user").upper()
            content = entry.get("content", "").strip()
            if not content:
                continue
            ts = entry.get("timestamp")
            if ts:
                lines.append(f"[{ts}] {role}: {content}")
            else:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _augment_prompt_with_context(self, prompt: str, context_text: str) -> str:
        """Append context summary to the system prompt."""
        if not context_text:
            return prompt

        sender_note = "\nNote: Messages include sender information in the format '[From: phone_number]' or '[Message from: phone_number]'. Use this to personalize responses and refer to specific people appropriately."
        return f"{prompt}\n\nConversation context (most recent first):\n{context_text}{sender_note}"

    async def _maybe_wait_for_user_response(self, chat_jid: str, sender: str,
                                            message_time: datetime, delay_seconds: int) -> bool:
        """
        Wait for a user response before proceeding to the LLM.
        Returns True if we should proceed with LLM, False if user responded in time.
        """
        if delay_seconds <= 0:
            return True

        deadline = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        check_interval = min(1, delay_seconds)

        while datetime.now(timezone.utc) < deadline:
            # If a new unprocessed incoming message arrives after the original timestamp,
            # treat it as the user taking over and skip LLM response.
            try:
                if self.db.has_unprocessed_message_after(chat_jid, message_time, sender):
                    return False
            except Exception:
                logger.warning("Failed to check for follow-up message", exc_info=True)
                break
            await asyncio.sleep(check_interval)

        return True

    def _append_and_trim_context(self, context: List[Dict], user_message: str,
                                 assistant_message: str, user_time: datetime,
                                 response_time: datetime, session_memory_config,
                                 sender: str = None) -> List[Dict]:
        """
        Add the latest user/assistant exchanges and re-apply trimming rules.

        Args:
            sender: Optional sender phone/JID to include in user message context
        """
        updated = list(context)

        # Include sender information in user message if available
        user_content = user_message
        if sender:
            user_content = f"[From: {sender}] {user_message}"

        updated.append({
            "role": "user",
            "content": user_content,
            "timestamp": user_time.isoformat()
        })
        updated.append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": response_time.isoformat()
        })
        return self._prune_context(updated, session_memory_config, response_time)

    async def start(self):
        """Start the message polling loop"""
        self.is_running = True
        logger.info("Message agent started")

        while self.is_running:
            try:
                await asyncio.sleep(self.config.polling.interval_seconds)
                await self.process_new_messages()

            except Exception as e:
                logger.error(f"Error in message agent loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    def stop(self):
        """Stop the message polling loop"""
        self.is_running = False
        logger.info("Message agent stopped")

    async def process_new_messages(self):
        """Process messages with lock to prevent concurrent cycles"""

        # Skip if already processing
        if self._processing_lock.locked():
            logger.debug("Polling cycle in progress, skipping")
            return

        async with self._processing_lock:
            try:
                self._maybe_reload_config()

                # Sync from Go bridge
                monitored_jids = [e.get_identifier() for e in self.config.monitored_entities if e.active]
                if self.config.self.active:
                    monitored_jids.append(self.config.get_self_jid())

                synced_count = self.db.sync_from_go_bridge(
                    monitored_jids=monitored_jids,
                    lookback_hours=24
                )

                if synced_count > 0:
                    logger.info(f"Synced {synced_count} new message(s) from Go bridge")

                # Atomically fetch and lock messages
                messages = self.db.fetch_and_lock_messages(limit=10, timeout_seconds=300)

                if not messages:
                    return

                logger.info(f"Processing {len(messages)} new messages...")

                for msg in messages:
                    try:
                        await self.process_message(msg)
                        self.db.mark_message_completed(msg["id"])
                    except Exception as e:
                        logger.error(f"Failed to process {msg['id']}: {e}", exc_info=True)
                        self.db.mark_message_failed(msg["id"], max_retries=3)

            except Exception as e:
                logger.error(f"Error in polling cycle: {e}", exc_info=True)

    async def process_message(self, message: Dict):
        """
        Process a single message

        Args:
            message: Message dict from database
        """
        try:
            msg_id = message["id"]

            # IDEMPOTENCY CHECK
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT processing_status FROM messages WHERE id = ?", (msg_id,))
            row = cursor.fetchone()
            if row and row[0] == 2:
                logger.info(f"Message {msg_id} already completed, skipping")
                return

            chat_jid = message["chat_jid"]
            sender = message["sender"]
            content = message["content"]
            is_from_me = message.get("is_from_me", False)

            # Show first 50 chars of message for visibility
            content_preview = content[:50] + "..." if len(content) > 50 else content
            logger.info(f"Processing message {msg_id} from {chat_jid}: '{content_preview}'")

            # Determine if message is from the bot itself
            self_jid = self.config.get_self_jid()
            from_bot = msg_id.startswith("sent_") or sender == self_jid or sender.endswith(self_jid)

            # Skip bot-originated messages entirely (prevents ack/loops)
            if from_bot:
                logger.info(f"Skipping bot-originated message {msg_id}")
                # Marking handled by caller
                return

            # Check for config changes before processing
            self._maybe_reload_config()

            # Use consistent session user ID
            if self.config.is_self_message(chat_jid):
                session_user = self.config.get_self_jid()
            else:
                session_user = sender

            # Avoid feedback loops: if this message matches the last response we sent to this chat,
            # skip it (it's our own previous reply surfacing from the bridge).
            if not self.config.is_self_message(chat_jid):
                last_response = self.last_bot_response.get(chat_jid)
                if is_from_me and last_response and content == last_response:
                    logger.info(f"Skipping bot-sent echo {msg_id} in {chat_jid}")
                    # Marking handled by caller
                    return

            # Check if this is a message to yourself
            if self.config.is_self_message(chat_jid):
                if not self.config.self.active:
                    logger.info(f"Self messages disabled, skipping {msg_id}")
                    # Marking handled by caller
                    return

                # IMPORTANT: For self-messages, both user and bot messages have is_from_me=1
                # We identify bot responses by their message ID pattern (starts with "sent_")
                if msg_id.startswith("sent_"):
                    logger.info(f"Skipping bot-sent self message {msg_id}")
                    # Marking handled by caller
                    return

                # Use self configuration
                prompt = self._resolve_prompt(
                    prompt_value=self.config.self.prompt,
                    prompt_is_file=getattr(self.config.self, "prompt_is_file", False)
                )
                persona = self.config.self.persona
                debug_enabled = getattr(self.config.self, "debug", True)
                logger.info(f"Processing self message with prompt: {prompt[:50]}...")
                session_memory_config = self.config.session_memory

                # Clear stale self sessions so first message starts fresh
                try:
                    reset = self.db.reset_stale_session(
                        user_jid=session_user,
                        chat_jid=chat_jid,
                        stale_after_seconds=self.self_session_stale_seconds
                    )
                    if reset:
                        logger.info(f"Reset stale self session for {chat_jid}")
                except Exception:
                    logger.warning("Failed to check/reset stale self session", exc_info=True)
            else:
                # Get entity configuration
                entity = self.config.get_entity_by_jid(chat_jid)
                if not entity:
                    logger.warning(f"No active entity config for {chat_jid}, skipping")
                    # Marking handled by caller
                    return

                prompt = entity.prompt
                persona = entity.persona
                debug_enabled = getattr(entity, "debug", False)
                prompt = self._resolve_prompt(
                    prompt_value=prompt,
                    prompt_is_file=getattr(entity, "prompt_is_file", False)
                )
                session_memory_config = self._get_session_memory_config(chat_jid)

                # === WAKE WORD CHECK ===
                # Skip wake word check for self messages (messages to yourself)
                if hasattr(entity, 'hey_bot') and entity.hey_bot:
                    has_wake_word, stripped_content = self.check_and_strip_wake_word(content)

                    if not has_wake_word:
                        logger.info(f"[BOT-IGNORE] Message {msg_id} from {chat_jid} - no wake word detected")
                        # Return without processing (silent filter)
                        # Caller will mark as completed
                        return

                    # Use stripped content for LLM
                    content = stripped_content

                    # Validate content is not empty after stripping
                    if not content or not content.strip():
                        logger.warning(f"[BOT-IGNORE] Message {msg_id} has empty content after wake word stripping")
                        # Return without processing
                        return

                    logger.info(f"[BOT-ACTIVATED] Wake word detected in {msg_id}, stripped to: {content[:50]}...")
                # === END WAKE WORD CHECK ===

            event_time = self._parse_timestamp(message.get("timestamp"))
            session_memory_config = session_memory_config or self.config.session_memory
            response_delay = self.config.get_response_delay_for_entity(chat_jid)

            # Optional wait to let the human reply themselves before bot steps in
            if not self.config.is_self_message(chat_jid) and response_delay > 0:
                proceed = await self._maybe_wait_for_user_response(
                    chat_jid=chat_jid,
                    sender=sender,
                    message_time=event_time,
                    delay_seconds=response_delay
                )
                if not proceed:
                    logger.info(f"User responded within {response_delay}s for {msg_id}; skipping bot reply.")
                    # Marking handled by caller
                    return

            # Load and prune context based on per-entity session memory
            session = self.db.get_or_create_session(
                user_jid=session_user,
                chat_jid=chat_jid,
                session_memory_config=session_memory_config,
                aliases=None,
                current_time=event_time
            )
            context = self.db.get_session_context(session["session_id"])
            context = self._prune_context(context, session_memory_config, event_time)
            context_text = self._format_context_for_prompt(context)
            augmented_prompt = self._augment_prompt_with_context(prompt, context_text)

            # For debug-enabled chats, send debug info BEFORE querying LLM
            if debug_enabled:
                try:
                    debug_message = (
                        "** DEBUG INFO **\n"
                        f"[User Entry]: {content}\n"
                        f"[Prompt]: {augmented_prompt}\n"
                        f"[Persona]: {persona}\n"
                        f"[Context]:\n{context_text or 'None'}"
                    )
                    logger.info(f"📤 About to send debug info for message {msg_id} to {chat_jid}")
                    await self.whatsapp.send_message(chat_jid, debug_message)
                    logger.info(f"✅ Successfully sent debug info for message {msg_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send debug info for {msg_id}: {e}", exc_info=True)
                    # Continue processing even if debug send fails

            # Query LLM with augmented prompt and sender info
            response = await self.query_llm(
                prompt=augmented_prompt,
                context=context,
                message=content,
                sender=sender
            )

            # Send response
            await self.whatsapp.send_message(chat_jid, response)
            # Track last bot response for loop avoidance
            self.last_bot_response[chat_jid] = response

            # Persist updated context (user + assistant)
            response_time = datetime.now(timezone.utc)
            updated_context = self._append_and_trim_context(
                context=context,
                user_message=content,
                assistant_message=response,
                user_time=event_time,
                response_time=response_time,
                session_memory_config=session_memory_config,
                sender=sender
            )
            try:
                self.db.update_session_context(
                    session_id=session["session_id"],
                    context=updated_context,
                    session_memory_config=session_memory_config,
                    activity_time=response_time
                )
            except Exception:
                logger.warning("Failed to update session context", exc_info=True)

            logger.info(f"✅ Processed message {msg_id}")

        except Exception as e:
            logger.error(f"Error processing message {message.get('id')}: {e}", exc_info=True)
            # Re-raise to let caller handle marking as failed
            raise

    async def query_llm(self, prompt: str, context: List[Dict], message: str, sender: str = None) -> str:
        """
        Query Perplexity API with message and context

        Args:
            message: User's message
            context: Previous conversation context (user/assistant turns)
            prompt: System prompt (already augmented with context summary)
            sender: Sender's phone number/JID (for context)

        Returns:
            AI response text
        """
        try:
            # Build messages array for API - prompt is already augmented with context summary
            # Context is included as text in the system prompt, not as separate messages
            messages = [{"role": "system", "content": prompt}]

            # Validate user message is not empty
            if not message or not message.strip():
                logger.error("Cannot send empty message to LLM")
                return "Please provide a message with content after the wake word."

            # Format user message with sender information for better context
            if sender:
                # Include sender phone/JID in the message for LLM context
                user_message_with_context = f"[Message from: {sender}]\n{message}"
            else:
                user_message_with_context = message

            # Add the current user message
            messages.append({"role": "user", "content": user_message_with_context})

            logger.info(f"Querying Perplexity with {len(messages)} messages (context in system prompt: {len(context)} entries)")
            logger.debug(f"System prompt: {prompt[:200]}...")

            # Call Perplexity API
            response = await self.perplexity.chat_completion(messages)

            logger.info(f"✅ Received response from Perplexity: {response[:100]}...")

            return response

        except Exception as e:
            logger.error(f"Error querying LLM: {e}", exc_info=True)
            return f"Sorry, I encountered an error processing your message: {str(e)}"


if __name__ == "__main__":
    # Test message agent
    from config import get_config
    from database import Database
    from whatsapp_client import WhatsAppClient

    logging.basicConfig(level=logging.INFO)

    try:
        config = get_config()
        db = Database()
        db.initialize()

        whatsapp = WhatsAppClient(config, db)
        agent = MessageAgent(config, db, whatsapp)

        logger.info("✅ Message agent initialized")
        logger.info(f"  Model: {config.perplexity.model}")
        logger.info(f"  Polling interval: {config.polling.interval_seconds}s")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
