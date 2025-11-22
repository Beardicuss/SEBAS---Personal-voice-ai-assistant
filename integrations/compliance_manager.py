# -*- coding: utf-8 -*-
"""
Compliance Manager Stub
Phase 4.2 Compatibility Layer
Provides dummy implementations so ComplianceSkill can load without backend.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime


class ComplianceManager:
    """Stub compliance manager for Stage 2."""
    
    def __init__(self, service_client=None):
        """
        Initialize stub compliance manager.
        
        Args:
            service_client: Optional service client (ignored in stub)
        """
        self.audit_log_path = os.path.join(
            os.path.expanduser('~'), 
            '.sebas', 
            'audit', 
            'audit.log'
        )

        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        except Exception:
            logging.warning(f"Could not create directory for {self.audit_log_path}")

        logging.info(f"ComplianceManager initialized (stub) with log: {self.audit_log_path}")

    # === Activity logging === #

    def log_activity(self, **kwargs) -> bool:
        """Log an activity to audit log."""
        try:
            timestamp = datetime.now().isoformat()
            user = kwargs.get('user', 'unknown')
            action = kwargs.get('action', 'no_action')
            status = kwargs.get('status', 'ok')
            
            msg = f"[{timestamp}] {user} -> {action} (status: {status})"
            
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
            
            logging.debug(f"Activity logged: {msg}")
            return True
        except Exception as e:
            logging.exception(f"Failed to write activity log: {e}")
            return False

    def get_activity_log(self, **kwargs) -> List[Dict[str, Any]]:
        """Return recent activity logs."""
        try:
            if not os.path.exists(self.audit_log_path):
                return []
            
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Return last 50 entries
            return [{"line": line.strip()} for line in lines[-50:]]
        except Exception:
            logging.exception("Failed to read activity log")
            return []

    # === Audit Events === #

    def get_audit_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Return dummy audit event data."""
        return [
            {
                "event_type": "login",
                "category": "access",
                "severity": "low",
                "timestamp": datetime.now().isoformat()
            },
            {
                "event_type": "command_executed",
                "category": "system",
                "severity": "info",
                "timestamp": datetime.now().isoformat()
            }
        ]

    # === Compliance Reports === #

    def generate_compliance_report(self, **kwargs) -> Dict[str, Any]:
        """Generate a dummy compliance report."""
        return {
            "generated_at": datetime.now().isoformat(),
            "activity_summary": {
                "total_activities": 42,
                "success_rate": 97.5,
                "period": "last_30_days"
            },
            "compliance_status": "compliant",
            "findings": [],
            "recommendations": [
                "Continue monitoring system access",
                "Review audit logs weekly"
            ]
        }

    # === Security Policy Verification === #

    def verify_security_policy(self) -> Dict[str, Any]:
        """Simulate a policy verification run."""
        return {
            "compliance_status": "compliant",
            "checks_performed": [
                "UAC enabled",
                "Firewall active",
                "Defender running",
                "Auto-update enabled",
                "Guest account disabled"
            ],
            "passed": 5,
            "failed": 0,
            "warnings": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    # === Compliance Check === #
    
    def run_compliance_check(self, **kwargs) -> Dict[str, Any]:
        """Run a comprehensive compliance check."""
        return {
            "overall_status": "compliant",
            "score": 95,
            "checks": {
                "uac": {"status": "pass", "details": "UAC is enabled"},
                "firewall": {"status": "pass", "details": "Firewall is active"},
                "defender": {"status": "pass", "details": "Defender is running"},
                "updates": {"status": "pass", "details": "Auto-update enabled"},
                "guest": {"status": "pass", "details": "Guest account disabled"}
            },
            "timestamp": datetime.now().isoformat()
        }