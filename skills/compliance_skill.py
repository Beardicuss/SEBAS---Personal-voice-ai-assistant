# -*- coding: utf-8 -*-
"""
Compliance Management Skill
Phase 4.2: Compliance reporting and activity monitoring
"""

from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging
from datetime import datetime, timedelta


class ComplianceSkill(BaseSkill):
    """
    Skill for managing compliance and reporting.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'log_activity',
            'get_activity_log',
            'get_audit_events',
            'generate_compliance_report',
            'verify_security_policy'
        ]
        self.compliance_manager = None
        self._init_compliance_manager()
    
    def _init_compliance_manager(self):
        """Initialize compliance manager."""
        try:
            from integrations.compliance_manager import ComplianceManager
            self.compliance_manager = ComplianceManager()
        except Exception:
            logging.exception("Failed to initialize compliance manager")
            self.compliance_manager = None
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents
    
    def handle(self, intent: str, slots: dict) -> bool:
        if not self.compliance_manager:
            self.assistant.speak("Compliance management is not available")
            return False
        
        if intent == 'log_activity':
            return self._handle_log_activity(slots)
        elif intent == 'get_activity_log':
            return self._handle_get_activity_log(slots)
        elif intent == 'get_audit_events':
            return self._handle_get_audit_events(slots)
        elif intent == 'generate_compliance_report':
            return self._handle_generate_compliance_report(slots)
        elif intent == 'verify_security_policy':
            return self._handle_verify_security_policy()
        return False
    
    def _handle_log_activity(self, slots: dict) -> bool:
        """Handle log activity command."""
        try:
            user = slots.get('user', 'system')
            action = slots.get('action', 'unknown')
            resource = slots.get('resource', '')
            status = slots.get('status', 'success')
            
            self.compliance_manager.log_activity(
                user=user,
                action=action,
                resource=resource,
                status=status
            )
            
            return True
            
        except Exception:
            logging.exception("Failed to log activity")
            return False
    
    def _handle_get_activity_log(self, slots: dict) -> bool:
        """Handle get activity log command."""
        try:
            user = slots.get('user')
            action = slots.get('action')
            days = slots.get('days', 7)
            
            start_date = datetime.now() - timedelta(days=int(days)) if days else None
            
            activities = self.compliance_manager.get_activity_log(
                user=user,
                action=action,
                start_date=start_date,
                limit=50
            )
            
            if activities:
                count = len(activities)
                self.assistant.speak(f"Found {count} activity log entries")
            else:
                self.assistant.speak("No activity log entries found")
            
            return True
            
        except Exception:
            logging.exception("Failed to get activity log")
            self.assistant.speak("Failed to get activity log")
            return False
    
    def _handle_get_audit_events(self, slots: dict) -> bool:
        """Handle get audit events command."""
        try:
            event_type = slots.get('event_type')
            category = slots.get('category')
            severity = slots.get('severity')
            days = slots.get('days', 7)
            
            start_date = datetime.now() - timedelta(days=int(days)) if days else None
            
            events = self.compliance_manager.get_audit_events(
                event_type=event_type,
                category=category,
                severity=severity,
                start_date=start_date,
                limit=50
            )
            
            if events:
                count = len(events)
                self.assistant.speak(f"Found {count} audit events")
            else:
                self.assistant.speak("No audit events found")
            
            return True
            
        except Exception:
            logging.exception("Failed to get audit events")
            self.assistant.speak("Failed to get audit events")
            return False
    
    def _handle_generate_compliance_report(self, slots: dict) -> bool:
        """Handle generate compliance report command."""
        try:
            days = slots.get('days', 30)
            
            start_date = datetime.now() - timedelta(days=int(days))
            end_date = datetime.now()
            
            report = self.compliance_manager.generate_compliance_report(
                start_date=start_date,
                end_date=end_date
            )
            
            if report:
                total_activities = report.get('activity_summary', {}).get('total_activities', 0)
                success_rate = report.get('activity_summary', {}).get('success_rate', 0)
                compliance_status = report.get('compliance_status', 'unknown')
                
                self.assistant.speak(
                    f"Compliance report generated: {total_activities} activities, "
                    f"{success_rate:.1f}% success rate, status: {compliance_status}"
                )
            else:
                self.assistant.speak("Failed to generate compliance report")
            
            return report is not None
            
        except Exception:
            logging.exception("Failed to generate compliance report")
            self.assistant.speak("Failed to generate compliance report")
            return False
    
    def _handle_verify_security_policy(self) -> bool:
        """Handle verify security policy command."""
        try:
            results = self.compliance_manager.verify_security_policy()
            
            if results:
                compliance_status = results.get('compliance_status', 'unknown')
                passed = results.get('passed', 0)
                failed = results.get('failed', 0)
                warnings = results.get('warnings', 0)
                
                self.assistant.speak(
                    f"Security policy verification: {compliance_status}, "
                    f"{passed} passed, {failed} failed, {warnings} warnings"
                )
            else:
                self.assistant.speak("Failed to verify security policy")
            
            return results is not None
            
        except Exception:
            logging.exception("Failed to verify security policy")
            self.assistant.speak("Failed to verify security policy")
            return False

