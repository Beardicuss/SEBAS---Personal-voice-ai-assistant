# -*- coding: utf-8 -*-
"""
Compliance Manager Stub
Phase 4.2 Compatibility Layer
This provides dummy implementations so the assistant can run without backend integrations.
"""

import os
import logging
from typing import Optional, Dict, Any, List


class ComplianceManager:
    def __init__(self, audit_log_path: str = "logs/audit.log"):
        """Initialize a stub compliance manager."""
        self.audit_log_path = audit_log_path

        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        except Exception:
            logging.warning(f"Could not create directory for {self.audit_log_path}")

        logging.info(f"ComplianceManager initialized (stub) with log path: {self.audit_log_path}")

    # === Activity logging === #

    def log_activity(self, **kwargs) -> bool:
        """Simulate logging an activity."""
        try:
            msg = f"[LOG] {kwargs.get('user', 'unknown')} -> {kwargs.get('action', 'no_action')} ({kwargs.get('status', 'ok')})"
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
            logging.info(msg)
            return True
        except Exception as e:
            logging.exception(f"Failed to write activity log: {e}")
            return False

    def get_activity_log(self, **kwargs) -> List[Dict[str, Any]]:
        """Return mock activity logs."""
        try:
            if not os.path.exists(self.audit_log_path):
                return []
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [{"line": line.strip()} for line in lines[-50:]]  # last 50 entries
        except Exception:
            logging.exception("Failed to read activity log")
            return []

    # === Audit Events === #

    def get_audit_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Return dummy audit event data."""
        return [
            {"event_type": "login", "category": "access", "severity": "low"},
            {"event_type": "file_delete", "category": "filesystem", "severity": "medium"}
        ]

    # === Compliance Reports === #

    def generate_compliance_report(self, **kwargs) -> Dict[str, Any]:
        """Generate a dummy compliance report."""
        return {
            "activity_summary": {
                "total_activities": 42,
                "success_rate": 97.5
            },
            "compliance_status": "compliant"
        }

    # === Security Policy Verification === #

    def verify_security_policy(self) -> Dict[str, Any]:
        """Simulate a policy verification run."""
        return {
            "compliance_status": "compliant",
            "passed": 5,
            "failed": 0,
            "warnings": 1
        }
