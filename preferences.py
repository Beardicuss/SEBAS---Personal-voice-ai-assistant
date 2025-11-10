# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict


class PreferenceStore:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
        except Exception:
            logging.exception("PreferenceStore load failed")

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, default=self._json_default)
        except Exception:
            logging.exception("PreferenceStore save failed")

    def _json_default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    def record_command(self, command: str):
        history = self.data.setdefault('history', [])
        history.append({"ts": datetime.now().isoformat(), "command": command})
        if len(history) > 200:
            del history[:len(history)-200]
        self.save()

    def set_pref(self, key: str, value: Any):
        self.data.setdefault('prefs', {})[key] = value
        self.save()

    def get_pref(self, key: str, default=None):
        return (self.data.get('prefs') or {}).get(key, default)

