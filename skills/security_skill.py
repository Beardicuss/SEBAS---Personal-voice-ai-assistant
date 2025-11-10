# -*- coding: utf-8 -*-
"""
Security Management Skill
Phase 4.1: Threat Management and Access Control
"""
from typing import Optional
from integrations.security_manager import SecurityManager
from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging


class SecuritySkill(BaseSkill):
    def __init__(self, assistant):
        super().__init__(assistant)
        self.security_manager: Optional[SecurityManager] = None
        self.intents = [
            'get_defender_status',
            'run_defender_scan',
            'get_defender_threats',
            'remove_defender_threat',
            'get_security_updates',
            'detect_suspicious_processes',
            'terminate_suspicious_process',
            'get_file_permissions',
            'set_file_permissions',
            'get_audit_policy',
            'set_audit_policy',
            # Phase 4 additions
            'check_password_strength',
            'guide_2fa_setup'
        ]
        self._init_security_manager()

    def _init_security_manager(self):
        """Initialize security manager."""
        try:
            from integrations.security_manager import SecurityManager
            self.security_manager = SecurityManager()
        except Exception:
            logging.exception("Failed to initialize security manager")
            self.security_manager = None

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def get_intents(self) -> list:
        return self.intents

    def handle(self, intent: str, slots: dict) -> bool:
        if not self.security_manager:
            self.assistant.speak("Security management is not available")
            return False

        slots = slots or {}

        try:
            if intent == 'get_defender_status':
                return self._handle_get_defender_status()
            elif intent == 'run_defender_scan':
                return self._handle_run_defender_scan(slots)
            elif intent == 'get_defender_threats':
                return self._handle_get_defender_threats()
            elif intent == 'remove_defender_threat':
                return self._handle_remove_defender_threat(slots)
            elif intent == 'get_security_updates':
                return self._handle_get_security_updates()
            elif intent == 'detect_suspicious_processes':
                return self._handle_detect_suspicious_processes()
            elif intent == 'terminate_suspicious_process':
                return self._handle_terminate_suspicious_process(slots)
            elif intent == 'get_file_permissions':
                return self._handle_get_file_permissions(slots)
            elif intent == 'set_file_permissions':
                return self._handle_set_file_permissions(slots)
            elif intent == 'get_audit_policy':
                return self._handle_get_audit_policy()
            elif intent == 'set_audit_policy':
                return self._handle_set_audit_policy(slots)
            elif intent == 'check_password_strength':
                return self._handle_check_password_strength(slots)
            elif intent == 'guide_2fa_setup':
                return self._handle_guide_2fa_setup(slots)
            return False
        except Exception:
            logging.exception(f"Error handling security intent {intent}")
            self.assistant.speak("An error occurred while executing that security command")
            return False

    def _handle_get_defender_status(self) -> bool:
        """Handle get Defender status command."""
        assert self.security_manager is not None
        try:
            status = self.security_manager.get_defender_status()
            if not status:
                self.assistant.speak("Could not get Defender status")
                return False

            av_enabled = status.get('AntivirusEnabled', False)
            rt_enabled = status.get('RealTimeProtectionEnabled', False)
            fw_enabled = status.get('FirewallEnabled', False)

            self.assistant.speak(
                f"Windows Defender status: Antivirus {'enabled' if av_enabled else 'disabled'}, "
                f"Real-time protection {'enabled' if rt_enabled else 'disabled'}, "
                f"Firewall {'enabled' if fw_enabled else 'disabled'}"
            )
            return True
        except Exception:
            logging.exception("Failed to get Defender status")
            self.assistant.speak("Failed to get Defender status")
            return False

    def _handle_run_defender_scan(self, slots: dict) -> bool:
        """Handle run Defender scan command."""
        assert self.security_manager is not None
        if not self.assistant.has_permission('run_defender_scan'):
            return False
        try:
            scan_type = slots.get('scan_type', 'quick')
            success, message = self.security_manager.run_defender_scan(scan_type)
            self.assistant.speak(message if success else f"Failed to start scan: {message}")
            return success
        except Exception:
            logging.exception("Failed to run Defender scan")
            self.assistant.speak("Failed to run Defender scan")
            return False

    def _handle_get_defender_threats(self) -> bool:
        """Handle get Defender threats command."""
        assert self.security_manager is not None
        if not self.assistant.has_permission('get_defender_threats'):
            return False
        try:
            threats = self.security_manager.get_defender_threats()
            if threats:
                count = len(threats)
                names = [t.get('ThreatName', 'Unknown') for t in threats[:5]]
                self.assistant.speak(f"Found {count} threats: {', '.join(names)}")
            else:
                self.assistant.speak("No threats detected")
            return True
        except Exception:
            logging.exception("Failed to get Defender threats")
            self.assistant.speak("Failed to get Defender threats")
            return False

    def _handle_remove_defender_threat(self, slots: dict) -> bool:
        assert self.security_manager is not None
        if not self.assistant.has_permission('remove_defender_threat'):
            return False
        try:
            threat_id = slots.get('threat_id')
            if not self.assistant.confirm_action("Remove detected threats?"):
                return False
            success, message = self.security_manager.remove_defender_threat(threat_id)
            self.assistant.speak(message if success else f"Failed to remove threat: {message}")
            return success
        except Exception:
            logging.exception("Failed to remove Defender threat")
            self.assistant.speak("Failed to remove threat")
            return False

    def _handle_get_security_updates(self) -> bool:
        assert self.security_manager is not None
        try:
            updates = self.security_manager.get_security_updates()
            if updates:
                self.assistant.speak(f"Found {len(updates)} security updates")
            else:
                self.assistant.speak("No security updates found")
            return True
        except Exception:
            logging.exception("Failed to get security updates")
            self.assistant.speak("Failed to get security updates")
            return False

    def _handle_detect_suspicious_processes(self) -> bool:
        assert self.security_manager is not None
        if not self.assistant.has_permission('detect_suspicious_processes'):
            return False
        try:
            suspicious = self.security_manager.detect_suspicious_processes()
            if suspicious:
                count = len(suspicious)
                names = [s.get('name', 'Unknown') for s in suspicious[:5]]
                self.assistant.speak(f"Found {count} suspicious processes: {', '.join(names)}")
            else:
                self.assistant.speak("No suspicious processes detected")
            return True
        except Exception:
            logging.exception("Failed to detect suspicious processes")
            self.assistant.speak("Failed to detect suspicious processes")
            return False

    def _handle_terminate_suspicious_process(self, slots: dict) -> bool:
        assert self.security_manager is not None
        if not self.assistant.has_permission('terminate_suspicious_process'):
            return False
        try:
            pid = slots.get('pid')
            if not pid:
                self.assistant.speak("Please specify a process ID")
                return False
            if not self.assistant.confirm_action(f"Terminate process {pid}?"):
                return False
            success, message = self.security_manager.terminate_process(int(pid), force=True)
            self.assistant.speak(message if success else f"Failed to terminate process: {message}")
            return success
        except Exception:
            logging.exception("Failed to terminate process")
            self.assistant.speak("Failed to terminate process")
            return False

    def _handle_get_file_permissions(self, slots: dict) -> bool:
        assert self.security_manager is not None
        try:
            path = slots.get('path')
            if not path:
                self.assistant.speak("Please specify a file or folder path")
                return False
            result = self.security_manager.get_file_permissions(path)
            if isinstance(result, dict) and result.get('status') == 'ok':
                self.assistant.speak(f"Retrieved permissions for {path}")
                return True
            self.assistant.speak("Failed to retrieve permissions")
            return False
        except Exception:
            logging.exception("Failed to get file permissions")
            self.assistant.speak("Failed to get file permissions")
            return False

    def _handle_set_file_permissions(self, slots: dict) -> bool:
        assert self.security_manager is not None
        if not self.assistant.has_permission('set_file_permissions'):
            return False
        try:
            path = slots.get('path')
            user = slots.get('user')
            perms = slots.get('permissions', 'F')
            recursive = slots.get('recursive', False)
            if not path or not user:
                self.assistant.speak("Please specify path and user")
                return False
            success, message = self.security_manager.set_file_permissions(path, user, perms, recursive)
            self.assistant.speak(message if success else f"Failed to set permissions: {message}")
            return success
        except Exception:
            logging.exception("Failed to set file permissions")
            self.assistant.speak("Failed to set file permissions")
            return False

    def _handle_get_audit_policy(self) -> bool:
        assert self.security_manager is not None
        try:
            policy = self.security_manager.get_audit_policy()
            if isinstance(policy, dict) and policy.get('status') == 'ok':
                self.assistant.speak("Retrieved audit policy")
                return True
            self.assistant.speak("Failed to retrieve audit policy")
            return False
        except Exception:
            logging.exception("Failed to get audit policy")
            self.assistant.speak("Failed to get audit policy")
            return False

    def _handle_set_audit_policy(self, slots: dict) -> bool:
        assert self.security_manager is not None
        if not self.assistant.has_permission('set_audit_policy'):
            return False
        try:
            cat = slots.get('category')
            sub = slots.get('subcategory')
            suc = slots.get('success', True)
            fail = slots.get('failure', True)
            if not cat or not sub:
                self.assistant.speak("Please specify category and sub category")
                return False
            success, message = self.security_manager.set_audit_policy(cat, sub, suc, fail)
            self.assistant.speak(message if success else f"Failed to set audit policy: {message}")
            return success
        except Exception:
            logging.exception("Failed to set audit policy")
            self.assistant.speak("Failed to set audit policy")
            return False

    def _handle_check_password_strength(self, slots: dict) -> bool:
        try:
            password = slots.get('password', '')
            if not password:
                self.assistant.speak("Please provide a password to evaluate")
                return False

            length = len(password)
            categories = sum(
                1 for check in (str.islower, str.isupper, str.isdigit, lambda c: not c.isalnum())
                if any(check(ch) for ch in password)
            )

            has_common = any(p in password.lower() for p in (
                'password', '1234', 'qwerty', 'admin', 'letmein', 'welcome', 'iloveyou', 'abc123'
            ))
            repeats = any(password[i] == password[i-1] == password[i-2] for i in range(2, length)) if length >= 3 else False

            score = 0
            if length >= 16: score += 4
            elif length >= 12: score += 3
            elif length >= 10: score += 2
            elif length >= 8: score += 1
            score += max(0, categories - 1)
            if has_common: score -= 3
            if repeats: score -= 1
            if password.lower() == password or password.upper() == password: score -= 1
            score = max(0, min(8, score))

            verdict = 'strong' if score >= 7 else 'good' if score >= 5 else 'weak' if score >= 3 else 'very weak'
            recs = []
            if length < 12: recs.append('increase length to at least 12-16 characters')
            if categories < 3: recs.append('mix upper, lower, numbers, and symbols')
            if has_common: recs.append('avoid common phrases and sequences')
            if repeats: recs.append('avoid repeated characters')
            if password.isalnum(): recs.append('add symbols to improve entropy')

            msg = f"Password looks {verdict}." + (f" Suggestions: {', '.join(recs)}" if recs else "")
            self.assistant.speak(msg)
            return True
        except Exception:
            logging.exception("Password strength evaluation failed")
            self.assistant.speak("Password evaluation failed")
            return False

    def _handle_guide_2fa_setup(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or '').lower()
            if provider in ('', 'windows', 'microsoft', 'hello'):
                self.assistant.speak(
                    "To enable Windows Hello and 2-step verification: Open Settings, Accounts, Sign-in options. "
                    "Set up Windows Hello PIN or biometrics. Then open Accounts, Email & accounts, Manage my Microsoft account. "
                    "In Security basics, turn on Two-step verification and add an authenticator app or phone number."
                )
            elif provider in ('google', 'gmail'):
                self.assistant.speak(
                    "To enable Google 2-Step Verification: Open myaccount.google.com, Security, 2-Step Verification. "
                    "Follow the wizard to add your phone or an authenticator app. Save backup codes securely."
                )
            elif provider == 'github':
                self.assistant.speak(
                    "To enable GitHub 2FA: Open github.com, Settings, Password and authentication. "
                    "Enable Two-factor authentication, choose app-based, and store recovery codes safely."
                )
            else:
                self.assistant.speak(
                    "I can guide Windows, Microsoft, Google, or GitHub. Say: guide two factor for Windows or Google."
                )
            return True
        except Exception:
            logging.exception("2FA guidance failed")
            self.assistant.speak("Failed to provide 2FA guidance")
            return False