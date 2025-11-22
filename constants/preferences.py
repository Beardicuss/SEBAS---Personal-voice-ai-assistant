"""
Preference storage for SEBAS, including role persistence.
FIXED: Correct import paths
"""

import json
import logging
import os
from datetime import datetime  # FIXED: Use standard Python datetime
from typing import Any, Dict, Optional

from sebas.constants.permissions import Role  # CORRECT: Import from constants.permissions


class PreferenceStore:
    """
    Centralized user preferences storage.

    Stores:
    - language
    - last used commands
    - user role (STANDARD / ADMIN / OWNER / ADMIN_OWNER)
    - future biometric identifiers
    - custom SEBAS settings
    """

    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._load()
        self._ensure_role_exists()

    # ----------------------------------------------------------
    #  File operations
    # ----------------------------------------------------------

    def _load(self):
        """Load preferences from JSON file."""
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logging.info(f"[PreferenceStore] Loaded preferences from {self.path}")
        except Exception:
            logging.exception("PreferenceStore load failed")
            self.data = {}

    def save(self):
        """Save preferences to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    self.data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=self._json_default
                )
            logging.debug(f"[PreferenceStore] Saved preferences to {self.path}")
        except Exception:
            logging.exception("PreferenceStore save failed")

    def _json_default(self, o):
        """JSON serializer for objects not serializable by default."""
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    # ----------------------------------------------------------
    #  History
    # ----------------------------------------------------------

    def record_command(self, command: str):
        """Record a command to history with timestamp."""
        history = self.data.setdefault("history", [])
        history.append({"ts": datetime.now().isoformat(), "command": command})
        
        # Keep only last 200 commands
        if len(history) > 200:
            del history[: len(history) - 200]
        
        self.save()

    def get_command_history(self, limit: int = 50) -> list:
        """Get recent command history."""
        history = self.data.get("history", [])
        return history[-limit:] if history else []

    # ----------------------------------------------------------
    #  Generic prefs
    # ----------------------------------------------------------

    def set_pref(self, key: str, value: Any):
        """Set a generic preference value."""
        self.data.setdefault("prefs", {})[key] = value
        self.save()

    def get_pref(self, key: str, default=None):
        """Get a generic preference value."""
        return (self.data.get("prefs") or {}).get(key, default)

    # ----------------------------------------------------------
    #  ROLE MANAGEMENT
    # ----------------------------------------------------------

    def _ensure_role_exists(self):
        """Ensure role is always valid. Default = ADMIN_OWNER for owner profile."""
        if "user_role" not in self.data:
            # Default owner role
            self.data["user_role"] = Role.ADMIN_OWNER.name
            self.save()
            logging.info(f"[PreferenceStore] Initialized default role: {Role.ADMIN_OWNER.name}")

    def set_user_role(self, role: Role):
        """Set the user's role."""
        if not isinstance(role, Role):
            raise ValueError("role must be a Role enum value")
        self.data["user_role"] = role.name
        self.save()
        logging.info(f"[PreferenceStore] User role set to: {role.name}")

    def get_user_role(self) -> Role:
        """Get the user's current role."""
        name = self.data.get("user_role", "").upper().strip()
        try:
            return Role[name]
        except (KeyError, ValueError):
            logging.warning(f"Invalid stored role '{name}', resetting to STANDARD")
            self.set_user_role(Role.STANDARD)
            return Role.STANDARD

    # ----------------------------------------------------------
    #  ACTIVE DIRECTORY CONFIG PLACEHOLDER
    # ----------------------------------------------------------

    def get_ad_config(self) -> dict:
        """Get Active Directory configuration. Not implemented yet."""
        return self.data.get("ad_config", {"enabled": False})

    def set_ad_config(self, config: dict):
        """Set Active Directory configuration."""
        self.data["ad_config"] = config
        self.save()

    # ----------------------------------------------------------
    #  Utility Methods
    # ----------------------------------------------------------

    def clear_history(self):
        """Clear command history."""
        self.data["history"] = []
        self.save()
        logging.info("[PreferenceStore] Command history cleared")

    def export_preferences(self) -> dict:
        """Export all preferences as a dictionary."""
        return self.data.copy()

    def import_preferences(self, data: dict):
        """Import preferences from a dictionary."""
        self.data = data
        self._ensure_role_exists()
        self.save()
        logging.info("[PreferenceStore] Preferences imported")