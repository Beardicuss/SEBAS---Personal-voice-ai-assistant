import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from sebas.constants.permissions import Role


class PreferenceStore:
    """
    Lightweight key/value store for SEBAS preferences.
    Handles: prefs, history, user role, AD config.
    """

    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._load()

    # ----------------------------------------------------
    # Load & Save
    # ----------------------------------------------------
    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:
            logging.exception("PreferenceStore load failed")

    def save(self):
        try:
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

    # ----------------------------------------------------
    # Command History
    # ----------------------------------------------------
    def record_command(self, command: str):
        history = self.data.setdefault("history", [])
        history.append({
            "ts": datetime.now().isoformat(),
            "command": command,
        })

        if len(history) > 200:  # keep last 200 commands
            del history[:-200]

        self.save()

    # ----------------------------------------------------
    # General Preferences
    # ----------------------------------------------------
    def set_pref(self, key: str, value: Any):
        self.data.setdefault("prefs", {})[key] = value
        self.save()

    def get_pref(self, key: str, default=None):
        return (self.data.get("prefs") or {}).get(key, default)

    # ----------------------------------------------------
    # Active Directory config support
    # ----------------------------------------------------
    def get_ad_config(self) -> Dict[str, Any]:
        """
        Returns AD config dictionary or empty dict.
        Ensures main.py will never crash.
        """
        return self.data.get("ad_config", {}) or {}

    # ----------------------------------------------------
    # User Role handling
    # ----------------------------------------------------
    def set_user_role(self, role, from_ad: bool = False):
        """
        main.py may pass either:
            - Role.ADMIN (enum)
            - "ADMIN" (string)
        Normalize everything to a plain uppercase string.
        """

        if isinstance(role, Role):
            role = role.name
        elif isinstance(role, str):
            role = role.strip().upper()
        else:
            logging.warning(f"Invalid role type: {role!r}")
            return

        user_data = self.data.setdefault("user", {})
        user_data["role"] = role
        user_data["role_from_ad"] = bool(from_ad)

        self.save()

    def get_user_role(self) -> Optional[Role]:
        """
        Returns Role enum or None.
        If stored value is invalid — return None.
        """
        role_name = (
            (self.data.get("user") or {}).get("role")
        )

        if not role_name:
            return None

        try:
            return Role[role_name.upper()]
        except KeyError:
            logging.warning(f"Unknown role in prefs: {role_name}")
            return None
