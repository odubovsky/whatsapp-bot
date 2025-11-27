"""
Configuration Handler Module

Provides interactive WhatsApp-based configuration interface for modifying app.json.
Only works in self group for security.
"""

import logging
import json
import shutil
import os
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone
from config import Config

logger = logging.getLogger(__name__)


class ConfigurationHandler:
    """Handles interactive configuration mode via WhatsApp"""

    def __init__(self, database):
        """
        Initialize configuration handler

        Args:
            database: Database instance
        """
        self.db = database

    @staticmethod
    def is_config_trigger(message: str) -> bool:
        """Check if message is a configuration trigger"""
        if not message:
            return False

        normalized = message.strip().lower()
        return normalized in ["bot config", "bot-config", "bot_config"]

    @staticmethod
    def is_exit_command(message: str) -> bool:
        """Check if message is an exit command"""
        if not message:
            return False

        normalized = message.strip().lower()
        return normalized in ["0", "exit"]

    def get_session(self, chat_jid: str) -> Optional[Dict]:
        """Get existing config session for chat"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT chat_jid, current_step, selected_entity_index, selected_option,
                   created_at, updated_at
            FROM config_sessions
            WHERE chat_jid = ?
        """, (chat_jid,))

        row = cursor.fetchone()
        if row:
            return {
                "chat_jid": row[0],
                "current_step": row[1],
                "selected_entity_index": row[2],
                "selected_option": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
        return None

    def create_session(self, chat_jid: str, step: str = "list") -> Dict:
        """Create a new config session"""
        cursor = self.db.conn.cursor()

        # Clear any existing session first
        cursor.execute("DELETE FROM config_sessions WHERE chat_jid = ?", (chat_jid,))

        # Create new session
        cursor.execute("""
            INSERT INTO config_sessions (chat_jid, current_step, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (chat_jid, step))

        self.db.conn.commit()
        return self.get_session(chat_jid)

    def update_session(self, chat_jid: str, step: str, entity_index: Optional[int] = None,
                      option: Optional[int] = None):
        """Update existing config session"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE config_sessions
            SET current_step = ?,
                selected_entity_index = ?,
                selected_option = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE chat_jid = ?
        """, (step, entity_index, option, chat_jid))
        self.db.conn.commit()

    def clear_session(self, chat_jid: str):
        """Clear config session"""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM config_sessions WHERE chat_jid = ?", (chat_jid,))
        self.db.conn.commit()
        logger.info(f"Cleared config session for {chat_jid}")

    def handle_config_trigger(self, config: Config) -> str:
        """Handle initial config trigger - list all entities"""
        return self.list_entities(config)

    def list_entities(self, config: Config) -> str:
        """Format and return list of all entities"""
        lines = ["The bot is now in configuration mode. Here's the current setup:", ""]

        for idx, entity in enumerate(config.monitored_entities, start=1):
            # Format entity header
            if entity.type == "group":
                lines.append(f"[{idx}] Group - {entity.name} - JID: {entity.jid}")
            else:  # user
                lines.append(f"[{idx}] User - {entity.name} - Phone: {entity.phone}")

            # Format current settings
            active_str = "Yes" if entity.active else "No"
            hey_bot_str = "Yes" if entity.hey_bot else "No"
            debug_str = "Yes" if entity.debug else "No"
            delay_str = f"{entity.response_delay}s"

            lines.append(f"    Active: {active_str} | Hey Bot: {hey_bot_str} | Response Delay: {delay_str} | Debug: {debug_str}")
            lines.append("")

        lines.append(f"Select an entity to modify [1-{len(config.monitored_entities)}] or type '0' to exit:")
        return "\n".join(lines)

    def handle_message(self, message: str, config: Config, session: Dict) -> str:
        """Route message based on current step"""
        current_step = session["current_step"]

        if current_step == "list":
            return self.handle_entity_selection(message, config, session)
        elif current_step == "entity_select":
            return self.handle_option_selection(message, config, session)
        elif current_step == "delay_input":
            return self.handle_delay_input(message, config, session)
        else:
            return "Invalid session state. Type 'bot config' to restart or '0' to exit."

    def handle_entity_selection(self, message: str, config: Config, session: Dict) -> str:
        """Handle entity number selection"""
        try:
            entity_num = int(message.strip())
            entity_index = entity_num - 1

            # Validate entity number
            if entity_index < 0 or entity_index >= len(config.monitored_entities):
                return f"Invalid entity number. Please select 1-{len(config.monitored_entities)} or type '0' to exit."

            entity = config.monitored_entities[entity_index]

            # Update session with selected entity
            self.update_session(session["chat_jid"], "entity_select", entity_index=entity_index)

            # Format entity details
            lines = []
            if entity.type == "group":
                lines.append(f"You chose to modify: {entity.name} (Group)")
                lines.append(f"JID: {entity.jid}")
            else:
                lines.append(f"You chose to modify: {entity.name} (User)")
                lines.append(f"Phone: {entity.phone}")

            lines.append("")
            lines.append("Current settings:")
            lines.append(f"- Active: {'Yes' if entity.active else 'No'}")
            lines.append(f"- Hey Bot: {'Yes' if entity.hey_bot else 'No'}")
            lines.append(f"- Debug: {'Yes' if entity.debug else 'No'}")
            lines.append(f"- Response Delay: {entity.response_delay}s")
            lines.append("")
            lines.append("What would you like to modify:")

            # Build options based on current state
            option_num = 1
            if entity.active:
                lines.append(f"{option_num}. Change Active to No")
                option_num += 1
            else:
                lines.append(f"{option_num}. Change Active to Yes")
                option_num += 1

            if entity.hey_bot:
                lines.append(f"{option_num}. Change Hey Bot to No")
                option_num += 1
            else:
                lines.append(f"{option_num}. Change Hey Bot to Yes")
                option_num += 1

            if entity.debug:
                lines.append(f"{option_num}. Change Debug to No")
                option_num += 1
            else:
                lines.append(f"{option_num}. Change Debug to Yes")
                option_num += 1

            lines.append(f"{option_num}. Set Response Delay (currently {entity.response_delay}s)")

            lines.append("")
            lines.append(f"Select an option [1-{option_num}] or type '0' to exit:")

            return "\n".join(lines)

        except ValueError:
            return f"Invalid input. Please enter a number (1-{len(config.monitored_entities)}) or '0' to exit."

    def handle_option_selection(self, message: str, config: Config, session: Dict) -> str:
        """Handle option selection for modifying entity"""
        try:
            option_num = int(message.strip())

            if option_num < 1 or option_num > 4:
                return "Invalid option. Please select 1-4 or type '0' to exit."

            entity_index = session["selected_entity_index"]
            entity = config.monitored_entities[entity_index]

            # Handle delay input separately
            if option_num == 4:
                self.update_session(session["chat_jid"], "delay_input",
                                   entity_index=entity_index, option=option_num)
                return f"Current response delay is {entity.response_delay}s.\nEnter new delay in seconds (0-300) or type '0' to exit:"

            # Handle boolean toggles (options 1-3)
            config_path = "/Users/odedd/coding/whatsapp-bot/app.json"
            success, new_value = self.update_and_save_config(config, config_path, entity_index, option_num)

            if success:
                # Clear session after successful update
                self.clear_session(session["chat_jid"])

                # Format success message
                entity = config.monitored_entities[entity_index]
                lines = ["Configuration updated successfully!", ""]

                if entity.type == "group":
                    lines.append(f"Updated entity: {entity.name} (Group)")
                    lines.append(f"JID: {entity.jid}")
                else:
                    lines.append(f"Updated entity: {entity.name} (User)")
                    lines.append(f"Phone: {entity.phone}")

                lines.append("")
                lines.append("New settings:")

                # Show which setting changed
                if option_num == 1:
                    lines.append(f"- Active: {'Yes' if entity.active else 'No'} <- Changed")
                else:
                    lines.append(f"- Active: {'Yes' if entity.active else 'No'}")

                if option_num == 2:
                    lines.append(f"- Hey Bot: {'Yes' if entity.hey_bot else 'No'} <- Changed")
                else:
                    lines.append(f"- Hey Bot: {'Yes' if entity.hey_bot else 'No'}")

                if option_num == 3:
                    lines.append(f"- Debug: {'Yes' if entity.debug else 'No'} <- Changed")
                else:
                    lines.append(f"- Debug: {'Yes' if entity.debug else 'No'}")

                lines.append(f"- Response Delay: {entity.response_delay}s")
                lines.append("")
                lines.append("Configuration saved to app.json")
                lines.append("Type 'bot config' to modify another entity or continue chatting normally.")

                return "\n".join(lines)
            else:
                return f"Failed to update configuration: {new_value}"

        except ValueError:
            return "Invalid input. Please enter a number (1-4) or '0' to exit."

    def handle_delay_input(self, message: str, config: Config, session: Dict) -> str:
        """Handle response delay value input"""
        try:
            delay = int(message.strip())

            if delay < 0 or delay > 300:
                return "Invalid delay. Please enter a value between 0 and 300 seconds or type '0' to exit."

            entity_index = session["selected_entity_index"]
            config_path = "/Users/odedd/coding/whatsapp-bot/app.json"

            success, msg = self.update_and_save_config(config, config_path, entity_index, 4, delay)

            if success:
                # Clear session after successful update
                self.clear_session(session["chat_jid"])

                entity = config.monitored_entities[entity_index]
                lines = ["Configuration updated successfully!", ""]

                if entity.type == "group":
                    lines.append(f"Updated entity: {entity.name} (Group)")
                    lines.append(f"JID: {entity.jid}")
                else:
                    lines.append(f"Updated entity: {entity.name} (User)")
                    lines.append(f"Phone: {entity.phone}")

                lines.append("")
                lines.append("New settings:")
                lines.append(f"- Active: {'Yes' if entity.active else 'No'}")
                lines.append(f"- Hey Bot: {'Yes' if entity.hey_bot else 'No'}")
                lines.append(f"- Debug: {'Yes' if entity.debug else 'No'}")
                lines.append(f"- Response Delay: {entity.response_delay}s <- Changed")
                lines.append("")
                lines.append("Configuration saved to app.json")
                lines.append("Type 'bot config' to modify another entity or continue chatting normally.")

                return "\n".join(lines)
            else:
                return f"Failed to update configuration: {msg}"

        except ValueError:
            return "Invalid input. Please enter a number (0-300) or type '0' to exit."

    def update_and_save_config(self, config: Config, config_path: str,
                                entity_index: int, option: int,
                                value: Optional[int] = None) -> Tuple[bool, str]:
        """
        Update config object and save to file with backup

        Args:
            config: AppConfig instance
            config_path: Path to app.json
            entity_index: Index of entity to modify
            option: Which option to modify (1=active, 2=hey_bot, 3=debug, 4=delay)
            value: Optional value for delay (option 4)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create backup
            backup_path = f"{config_path}.backup"
            if os.path.exists(config_path):
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Modify entity
            entity = config.monitored_entities[entity_index]

            if option == 1:
                entity.active = not entity.active
                change_desc = f"Active: {entity.active}"
            elif option == 2:
                entity.hey_bot = not entity.hey_bot
                change_desc = f"Hey Bot: {entity.hey_bot}"
            elif option == 3:
                entity.debug = not entity.debug
                change_desc = f"Debug: {entity.debug}"
            elif option == 4:
                entity.response_delay = value
                change_desc = f"Response Delay: {value}s"
            else:
                return False, "Invalid option"

            # Save to file
            config.save_to_file(config_path)

            # Validate by reading back
            Config(config_path)

            logger.info(f"Configuration updated: Entity {entity_index} - {change_desc}")
            return True, change_desc

        except Exception as e:
            logger.error(f"Failed to update config: {e}", exc_info=True)

            # Restore backup if exists
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, config_path)
                    logger.info("Restored backup after error")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")

            return False, str(e)
