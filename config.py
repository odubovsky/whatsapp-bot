from __future__ import annotations

"""
Configuration Management Module

Loads and validates configuration from .env and app.json files.
Provides typed access to all configuration settings.
"""

import os
import json
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
import pytz
from pathlib import Path

# Load .env file
load_dotenv()


@dataclass
class SelfConfig:
    """Configuration for messages sent to yourself (for testing/debugging)"""
    active: bool = False
    prompt: str = "You are a helpful assistant."
    persona: str = "helpful and concise"
    stale_session_seconds: int = 60
    debug: bool = True
    prompt_is_file: bool = False

    def validate(self):
        """Validate self configuration"""
        if self.active and not self.prompt:
            raise ValueError("self.prompt is required when self.active is true")
        if self.stale_session_seconds is not None and self.stale_session_seconds <= 0:
            raise ValueError("self.stale_session_seconds must be greater than 0")
        if self.prompt_is_file:
            path = Path(self.prompt)
            if not path.exists():
                raise ValueError(f"Self prompt file not found: {self.prompt}")


@dataclass
class WhatsAppConfig:
    """WhatsApp connection settings"""
    phone_number: str

    def validate(self):
        """Validate WhatsApp configuration"""
        if not self.phone_number:
            raise ValueError("whatsapp.phone_number is required")


@dataclass
class PollingConfig:
    """Message polling settings"""
    interval_seconds: int = 5
    max_concurrent_messages: int = 10
    processing_timeout_seconds: int = 300
    max_retries: int = 3
    lookback_hours: int = 24

    def validate(self):
        """Validate polling configuration"""
        if self.interval_seconds < 1 or self.interval_seconds > 300:
            raise ValueError("polling.interval_seconds must be between 1 and 300")
        if self.lookback_hours < 1 or self.lookback_hours > 168:
            raise ValueError("polling.lookback_hours must be between 1 and 168 (1 week)")


@dataclass
class RotationConfig:
    """Message rotation/cleanup settings"""
    messages_retention_days: int = 7
    cleanup_interval_hours: int = 24

    def validate(self):
        """Validate rotation configuration"""
        if self.messages_retention_days < 1 or self.messages_retention_days > 365:
            raise ValueError("rotation.messages_retention_days must be between 1 and 365")
        if self.cleanup_interval_hours < 1 or self.cleanup_interval_hours > 168:
            raise ValueError("rotation.cleanup_interval_hours must be between 1 and 168")


@dataclass
class SessionMemoryConfig:
    """Session memory expiration settings"""
    reset_mode: Literal["time", "duration", "same_day"]
    reset_time: Optional[str] = None  # e.g., "02:00"
    reset_hours: Optional[int] = None  # e.g., 24
    reset_minutes: Optional[int] = None  # Alternative to hours for short-lived contexts
    timezone: str = "UTC"

    def get_timezone(self):
        """Returns pytz timezone object"""
        try:
            return pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {self.timezone}")

    def validate(self):
        """Ensure correct fields are set based on mode"""
        if self.reset_mode == "time" and not self.reset_time:
            raise ValueError("session_memory.reset_time required when reset_mode is 'time'")
        if self.reset_mode == "duration" and not (self.reset_hours or self.reset_minutes):
            raise ValueError("session_memory.reset_hours or reset_minutes required when reset_mode is 'duration'")

        # Validate reset_time format (HH:MM)
        if self.reset_time:
            try:
                datetime.strptime(self.reset_time, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid reset_time format: {self.reset_time}. Use HH:MM (24-hour)")

        # Validate reset_hours range
        if self.reset_hours and (self.reset_hours < 1 or self.reset_hours > 168):
            raise ValueError("session_memory.reset_hours must be between 1 and 168")
        if self.reset_minutes and (self.reset_minutes < 1 or self.reset_minutes > 10080):
            raise ValueError("session_memory.reset_minutes must be between 1 and 10080 (7 days)")

        # Validate timezone
        self.get_timezone()

    def get_duration_minutes(self) -> Optional[int]:
        """Return the duration window in minutes for duration mode"""
        if self.reset_mode != "duration":
            return None
        if self.reset_minutes:
            return self.reset_minutes
        if self.reset_hours:
            return self.reset_hours * 60
        return None


@dataclass
class MonitoredEntity:
    """Represents a user or group to monitor"""
    type: Literal["user", "group"]
    name: str
    prompt: str
    persona: str
    active: bool = True  # Whether to monitor this entity
    debug: bool = False  # Send debug info before LLM call
    jid: Optional[str] = None  # For groups
    phone: Optional[str] = None  # For users
    prompt_is_file: bool = False
    session_memory: Optional[SessionMemoryConfig] = None  # Optional per-entity override
    response_delay: Optional[int] = None  # Seconds to wait before responding (per-entity override)
    hey_bot: bool = False  # Require wake word (e.g., "hey bot", "hello bot", "הי בוט", "היי בוט") to respond

    def get_identifier(self) -> str:
        """Returns JID or phone@s.whatsapp.net"""
        if self.type == "group":
            return self.jid
        else:
            # Strip + prefix if present (WhatsApp JIDs don't use +)
            phone = self.phone.lstrip('+') if self.phone else ''
            return f"{phone}@s.whatsapp.net"

    def validate(self):
        """Validate entity configuration"""
        if self.type == "group" and not self.jid:
            raise ValueError(f"Group entity '{self.name}' must have 'jid' field")
        if self.type == "user" and not self.phone:
            raise ValueError(f"User entity '{self.name}' must have 'phone' field")
        if not self.prompt:
            raise ValueError(f"Entity '{self.name}' must have 'prompt' field")
        if self.prompt_is_file:
            path = Path(self.prompt)
            if not path.exists():
                raise ValueError(f"Prompt file not found for entity '{self.name}': {self.prompt}")
        if self.session_memory:
            self.session_memory.validate()
        if self.response_delay is not None and self.response_delay < 0:
            raise ValueError(f"response_delay for '{self.name}' must be >= 0")
        if not isinstance(self.hey_bot, bool):
            raise ValueError(f"hey_bot for '{self.name}' must be boolean, got {type(self.hey_bot)}")


@dataclass
class VitalityConfig:
    """Daily health check settings"""
    enabled: bool = True
    time: str = "09:00"  # HH:MM format
    timezone: str = "UTC"
    message: str = "🤖 WhatsApp Bot is operational"

    def get_timezone(self):
        """Returns pytz timezone object"""
        try:
            return pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {self.timezone}")

    def validate(self):
        """Validate vitality configuration"""
        # Validate time format
        try:
            datetime.strptime(self.time, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid vitality.time format: {self.time}. Use HH:MM (24-hour)")

        # Validate timezone
        self.get_timezone()


@dataclass
class PerplexityConfig:
    """Perplexity API settings"""
    model: str = "llama-3.1-sonar-large-128k-online"
    temperature: float = 0.7
    max_tokens: int = 500

    def validate(self):
        """Validate Perplexity configuration"""
        if self.temperature < 0.0 or self.temperature > 1.0:
            raise ValueError("perplexity.temperature must be between 0.0 and 1.0")
        if self.max_tokens < 100 or self.max_tokens > 4000:
            raise ValueError("perplexity.max_tokens must be between 100 and 4000")


class Config:
    """Main configuration class - singleton pattern"""

    def __init__(self, config_file: str = "app.json", env_file: str = ".env"):
        # Load from .env
        if env_file != ".env":
            load_dotenv(env_file, override=True)
        self.env_file = env_file

        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.database_path = os.getenv("DATABASE_PATH", "store/whatsapp_bot.db")

        # Validate required env vars
        if not self.perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in .env file")

        # Load from app.json
        self.config_file = config_file
        self._load_app_config()

    def _load_app_config(self):
        """Load and parse app.json"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(
                f"{self.config_file} not found. "
                f"Copy from app.json.example and configure."
            )

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_file}: {e}")

        # Parse sections
        self.whatsapp = WhatsAppConfig(**data.get("whatsapp", {}))
        self.whatsapp.validate()

        # Global response delay (seconds) before LLM kicks in
        self.response_delay_default = int(data.get("response_delay", 5))
        if self.response_delay_default < 0:
            raise ValueError("response_delay must be >= 0")

        # Parse self configuration (messages to yourself)
        self.self = SelfConfig(**data.get("self", {}))
        self.self.validate()

        # Parse monitored entities
        entities_data = data.get("monitored_entities", [])
        if not entities_data:
            raise ValueError("At least one monitored entity is required in app.json")

        self.monitored_entities: List[MonitoredEntity] = []
        for entity_data in entities_data:
            # Allow per-entity session_memory override
            entity_payload = dict(entity_data)
            entity_session_memory = entity_payload.pop("session_memory", None)

            entity = MonitoredEntity(**entity_payload)
            entity.validate()
            if entity_session_memory:
                entity.session_memory = self._parse_session_memory_config(
                    entity_session_memory,
                    f"monitored entity '{entity.name}' session_memory"
                )
                entity.session_memory.validate()
            self.monitored_entities.append(entity)

        self.polling = PollingConfig(**data.get("polling", {}))
        self.polling.validate()

        self.rotation = RotationConfig(**data.get("rotation", {}))
        self.rotation.validate()

        self.session_memory = self._parse_session_memory_config(
            data.get("session_memory", {}),
            "session_memory"
        )

        self.vitality = VitalityConfig(**data.get("vitality", {}))
        self.vitality.validate()

        self.perplexity = PerplexityConfig(**data.get("perplexity", {}))
        self.perplexity.validate()

        # Build lookup maps for fast access
        self._build_entity_maps()

    def _parse_session_memory_config(self, config_data, label: str) -> SessionMemoryConfig:
        """Parse and validate a session_memory config block."""
        try:
            cfg = SessionMemoryConfig(**(config_data or {}))
            cfg.validate()
            return cfg
        except Exception as e:
            raise ValueError(f"Invalid {label}: {e}")

    def _build_entity_maps(self):
        """Create lookup dictionaries for entities (only active ones)"""
        self.entity_by_jid: Dict[str, MonitoredEntity] = {}

        for entity in self.monitored_entities:
            if entity.active:  # Only include active entities
                identifier = entity.get_identifier()
                self.entity_by_jid[identifier] = entity

    def get_self_jid(self) -> str:
        """Get JID for messages sent to yourself"""
        phone = self.whatsapp.phone_number.lstrip('+')
        return f"{phone}@s.whatsapp.net"

    def is_self_message(self, jid: str) -> bool:
        """Check if this is a message to yourself"""
        return jid == self.get_self_jid()

    def get_entity_by_jid(self, jid: str) -> Optional[MonitoredEntity]:
        """
        Get monitored entity by JID
        Returns None if entity is not active or not found
        """
        return self.entity_by_jid.get(jid)

    def is_monitored(self, jid: str) -> bool:
        """Check if JID is in monitored entities (and active)"""
        return jid in self.entity_by_jid

    def get_prompt_for_entity(self, jid: str) -> Optional[str]:
        """Get LLM prompt for specific entity"""
        entity = self.get_entity_by_jid(jid)
        return entity.prompt if entity else None

    def get_persona_for_entity(self, jid: str) -> Optional[str]:
        """Get persona for specific entity"""
        entity = self.get_entity_by_jid(jid)
        return entity.persona if entity else None

    def get_session_memory_for_entity(self, jid: str) -> SessionMemoryConfig:
        """Get session memory config, falling back to the global default."""
        entity = self.get_entity_by_jid(jid)
        if entity and entity.session_memory:
            return entity.session_memory
        return self.session_memory

    def get_response_delay_for_entity(self, jid: str) -> int:
        """Get response delay in seconds, with per-entity override."""
        entity = self.get_entity_by_jid(jid)
        if entity and entity.response_delay is not None:
            return max(0, int(entity.response_delay))
        return max(0, int(self.response_delay_default))

    def save_to_file(self, file_path: str) -> bool:
        """
        Save configuration to JSON file with backup

        Args:
            file_path: Path to app.json file

        Returns:
            True if successful, raises exception otherwise
        """
        import shutil

        # Backup existing file
        backup_path = f"{file_path}.backup"
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)

        try:
            # Convert to dict
            config_dict = {
                "whatsapp": {
                    "phone_number": self.whatsapp.phone_number
                },
                "self": {
                    "active": self.self.active,
                    "prompt": self.self.prompt,
                    "persona": self.self.persona,
                    "stale_session_seconds": self.self.stale_session_seconds,
                    "debug": self.self.debug
                },
                "monitored_entities": [
                    {
                        "type": entity.type,
                        "jid": entity.jid if entity.type == "group" else None,
                        "phone": entity.phone if entity.type == "user" else None,
                        "name": entity.name,
                        "active": entity.active,
                        "debug": entity.debug,
                        "hey_bot": entity.hey_bot,
                        "prompt": entity.prompt,
                        "persona": entity.persona,
                        "response_delay": entity.response_delay,
                        "session_memory": {
                            "reset_mode": entity.session_memory.reset_mode,
                            "reset_minutes": entity.session_memory.reset_minutes,
                            "reset_time": entity.session_memory.reset_time,
                            "timezone": entity.session_memory.timezone
                        }
                    }
                    for entity in self.monitored_entities
                ],
                "polling": {
                    "interval_seconds": self.polling.interval_seconds,
                    "max_concurrent_messages": self.polling.max_concurrent_messages,
                    "processing_timeout_seconds": self.polling.processing_timeout_seconds,
                    "max_retries": self.polling.max_retries,
                    "lookback_hours": self.polling.lookback_hours
                },
                "rotation": {
                    "messages_retention_days": self.rotation.messages_retention_days,
                    "cleanup_interval_hours": self.rotation.cleanup_interval_hours
                },
                "session_memory": {
                    "reset_mode": self.session_memory.reset_mode,
                    "reset_time": self.session_memory.reset_time,
                    "timezone": self.session_memory.timezone
                },
                "vitality": {
                    "enabled": self.vitality.enabled,
                    "time": self.vitality.time,
                    "timezone": self.vitality.timezone,
                    "message": self.vitality.message
                },
                "perplexity": {
                    "model": self.perplexity.model,
                    "temperature": self.perplexity.temperature,
                    "max_tokens": self.perplexity.max_tokens
                }
            }

            # Remove None values from monitored_entities
            for entity_dict in config_dict["monitored_entities"]:
                if entity_dict["jid"] is None:
                    del entity_dict["jid"]
                if entity_dict["phone"] is None:
                    del entity_dict["phone"]

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            # Validate JSON can be read back
            with open(file_path, 'r') as f:
                json.load(f)

            return True

        except Exception as e:
            # Restore backup on error
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            raise e


# Global config instance - loaded once at startup
_config_instance = None


def get_config(config_file: str = "app.json", env_file: str = ".env") -> Config:
    """Get or create config singleton"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file, env_file)
    return _config_instance


def reload_config(config_file: str = "app.json", env_file: str = ".env") -> Config:
    """Force reload config (useful for testing or live updates)"""
    global _config_instance
    _config_instance = Config(config_file, env_file)
    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print("✅ Configuration loaded successfully")
        print(f"  Phone: {config.whatsapp.phone_number}")
        print(f"  Monitored entities: {len(config.monitored_entities)}")
        print(f"  Polling interval: {config.polling.interval_seconds}s")
        print(f"  Session memory mode: {config.session_memory.reset_mode}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        exit(1)
