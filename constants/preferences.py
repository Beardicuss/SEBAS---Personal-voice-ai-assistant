"""
Preference storage for SEBAS, including role persistence.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from sebas.constants.permissions import Role


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
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:
            logging.exception("PreferenceStore load failed")

    def save(self):
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
        except Exception:
            logging.exception("PreferenceStore save failed")

    def _json_default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    # ----------------------------------------------------------
    #  History
    # ----------------------------------------------------------

    def record_command(self, command: str):
        history = self.data.setdefault("history", [])
        history.append({"ts": datetime.now().isoformat(), "command": command})
        if len(history) > 200:
            del history[: len(history) - 200]
        self.save()

    # ----------------------------------------------------------
    #  Generic prefs
    # ----------------------------------------------------------

    def set_pref(self, key: str, value: Any):
        self.data.setdefault("prefs", {})[key] = value
        self.save()

    def get_pref(self, key: str, default=None):
        return (self.data.get("prefs") or {}).get(key, default)

    # ----------------------------------------------------------
    #  ROLE MANAGEMENT (NEW)
    # ----------------------------------------------------------

    def _ensure_role_exists(self):
        """Ensure role is always valid. Default = ADMIN_OWNER for your profile."""
        if "user_role" not in self.data:
            # Dante = ADMIN_OWNER by default
            self.data["user_role"] = Role.ADMIN_OWNER.name
            self.save()

    def set_user_role(self, role: Role):
        if not isinstance(role, Role):
            raise ValueError("role must be a Role enum value")
        self.data["user_role"] = role.name
        self.save()

    def get_user_role(self) -> Role:
        name = self.data.get("user_role", "").upper().strip()
        try:
            return Role[name]
        except Exception:
            logging.warning(f"Invalid stored role '{name}', reset to STANDARD")
            self.set_user_role(Role.STANDARD)
            return Role.STANDARD

    # ----------------------------------------------------------
    #  ACTIVE DIRECTORY CONFIG PLACEHOLDER (SAFE)
    # ----------------------------------------------------------

    def get_ad_config(self):
        """AD not implemented yet. Just return placeholder."""
        return self.data.get("ad_config", {"enabled": False})
