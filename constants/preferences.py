# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict
from constants.permissions import Role


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

    def get_user_role(self) -> Role:
        # Check if AD integration is enabled and role is set from AD
        if self.get_pref('ad_role_enabled', False):
            ad_role = self.get_pref('ad_role')
            if ad_role and ad_role.upper() in Role.__members__:
                return Role[ad_role.upper()]
        
        # Fallback to manual role setting
        role_name = self.get_pref('user_role', 'STANDARD').upper()
        return Role[role_name] if role_name in Role.__members__ else Role.STANDARD

    def set_user_role(self, role: Role, from_ad: bool = False):
        if from_ad:
            self.set_pref('ad_role', role.name)
            self.set_pref('ad_role_enabled', True)
        else:
            self.set_pref('user_role', role.name)
            self.set_pref('ad_role_enabled', False)
    
    def get_ad_config(self) -> dict:
        """Get Active Directory configuration."""
        return {
            'enabled': self.get_pref('ad_enabled', False),
            'domain': self.get_pref('ad_domain'),
            'ldap_server': self.get_pref('ad_ldap_server'),
            'use_windows_auth': self.get_pref('ad_use_windows_auth', True),
            'bind_user': self.get_pref('ad_bind_user'),
            'role_mappings': self.get_pref('ad_role_mappings', {})
        }
    
    def set_ad_config(self, config: dict):
        """Set Active Directory configuration."""
        if 'enabled' in config:
            self.set_pref('ad_enabled', config['enabled'])
        if 'domain' in config:
            self.set_pref('ad_domain', config['domain'])
        if 'ldap_server' in config:
            self.set_pref('ad_ldap_server', config['ldap_server'])
        if 'use_windows_auth' in config:
            self.set_pref('ad_use_windows_auth', config['use_windows_auth'])
        if 'bind_user' in config:
            self.set_pref('ad_bind_user', config['bind_user'])
        if 'role_mappings' in config:
            self.set_pref('ad_role_mappings', config['role_mappings'])
