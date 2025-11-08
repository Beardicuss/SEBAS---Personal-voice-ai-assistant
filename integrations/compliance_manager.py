# -*- coding: utf-8 -*-
"""
Compliance & Reporting
Phase 4.2: System auditing, compliance reporting, and activity monitoring
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import threading


class ComplianceManager:
    """
    Manages compliance reporting, security policy verification,
    and user activity monitoring.
    """
    
    def __init__(self, audit_log_path: Optional[str] = None):
        """
        Initialize Compliance Manager.
        
        Args:
            audit_log_path: Path to store audit logs
        """
        if audit_log_path is None:
            audit_log_path = os.path.join(os.path.expanduser('~'), 'sebas_audit.log')
        
        self.audit_log_path = audit_log_path
        self.activity_log_path = os.path.join(os.path.expanduser('~'), 'sebas_activity.log')
        self.lock = threading.Lock()
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.activity_log_path), exist_ok=True)
    
    def log_activity(self, user: str, action: str, resource: str,
                    status: str = "success", details: Optional[Dict] = None):
        """
        Log user activity.
        
        Args:
            user: Username
            action: Action performed
            resource: Resource affected
            status: Status (success, failure, denied)
            details: Additional details
        """
        try:
            activity = {
                'timestamp': datetime.now().isoformat(),
                'user': user,
                'action': action,
                'resource': resource,
                'status': status,
                'details': details or {}
            }
            
            with self.lock:
                with open(self.activity_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(activity) + '\n')
                    
        except Exception:
            logging.exception("Failed to log activity")
    
    def log_audit_event(self, event_type: str, category: str, 
                       description: str, severity: str = "info",
                       details: Optional[Dict] = None):
        """
        Log audit event.
        
        Args:
            event_type: Type of event
            category: Event category
            description: Event description
            severity: Severity level (info, warning, error, critical)
            details: Additional details
        """
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'category': category,
                'description': description,
                'severity': severity,
                'details': details or {}
            }
            
            with self.lock:
                with open(self.audit_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event) + '\n')
                    
        except Exception:
            logging.exception("Failed to log audit event")
    
    def get_activity_log(self, user: Optional[str] = None,
                        action: Optional[str] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict]:
        """
        Get activity log entries.
        
        Args:
            user: Filter by user
            action: Filter by action
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of entries to return
            
        Returns:
            List of activity log entries
        """
        try:
            activities = []
            
            if not os.path.exists(self.activity_log_path):
                return activities
            
            with open(self.activity_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        activity = json.loads(line.strip())
                        
                        # Apply filters
                        if user and activity.get('user') != user:
                            continue
                        if action and activity.get('action') != action:
                            continue
                        
                        timestamp = datetime.fromisoformat(activity.get('timestamp', ''))
                        if start_date and timestamp < start_date:
                            continue
                        if end_date and timestamp > end_date:
                            continue
                        
                        activities.append(activity)
                        
                        if len(activities) >= limit:
                            break
                            
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            return activities
            
        except Exception:
            logging.exception("Failed to get activity log")
            return []
    
    def get_audit_events(self, event_type: Optional[str] = None,
                        category: Optional[str] = None,
                        severity: Optional[str] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict]:
        """
        Get audit event entries.
        
        Args:
            event_type: Filter by event type
            category: Filter by category
            severity: Filter by severity
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of entries to return
            
        Returns:
            List of audit event entries
        """
        try:
            events = []
            
            if not os.path.exists(self.audit_log_path):
                return events
            
            with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        
                        # Apply filters
                        if event_type and event.get('event_type') != event_type:
                            continue
                        if category and event.get('category') != category:
                            continue
                        if severity and event.get('severity') != severity:
                            continue
                        
                        timestamp = datetime.fromisoformat(event.get('timestamp', ''))
                        if start_date and timestamp < start_date:
                            continue
                        if end_date and timestamp > end_date:
                            continue
                        
                        events.append(event)
                        
                        if len(events) >= limit:
                            break
                            
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            return events
            
        except Exception:
            logging.exception("Failed to get audit events")
            return []
    
    def generate_compliance_report(self, start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate compliance status report.
        
        Args:
            start_date: Start date for report period
            end_date: End date for report period
            
        Returns:
            Dict with compliance report data
        """
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.now()
            
            # Get activity and audit data
            activities = self.get_activity_log(start_date=start_date, end_date=end_date, limit=1000)
            audit_events = self.get_audit_events(start_date=start_date, end_date=end_date, limit=1000)
            
            # Calculate statistics
            total_activities = len(activities)
            successful_activities = len([a for a in activities if a.get('status') == 'success'])
            failed_activities = len([a for a in activities if a.get('status') == 'failure'])
            denied_activities = len([a for a in activities if a.get('status') == 'denied'])
            
            # Group by action
            actions = {}
            for activity in activities:
                action = activity.get('action', 'unknown')
                actions[action] = actions.get(action, 0) + 1
            
            # Group by user
            users = {}
            for activity in activities:
                user = activity.get('user', 'unknown')
                users[user] = users.get(user, 0) + 1
            
            # Count audit events by severity
            severity_counts = {}
            for event in audit_events:
                severity = event.get('severity', 'info')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count audit events by category
            category_counts = {}
            for event in audit_events:
                category = event.get('category', 'unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            report = {
                'report_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'generated_at': datetime.now().isoformat(),
                'activity_summary': {
                    'total_activities': total_activities,
                    'successful': successful_activities,
                    'failed': failed_activities,
                    'denied': denied_activities,
                    'success_rate': (successful_activities / total_activities * 100) if total_activities > 0 else 0
                },
                'activity_by_action': actions,
                'activity_by_user': users,
                'audit_summary': {
                    'total_events': len(audit_events),
                    'by_severity': severity_counts,
                    'by_category': category_counts
                },
                'top_actions': sorted(actions.items(), key=lambda x: x[1], reverse=True)[:10],
                'top_users': sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
            return report
            
        except Exception:
            logging.exception("Failed to generate compliance report")
            return {}
    
    def verify_security_policy(self, policy_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verify security policy compliance.
        
        Args:
            policy_rules: Optional custom policy rules
            
        Returns:
            Dict with policy verification results
        """
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'checks': [],
                'compliance_status': 'unknown',
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
            
            # Default policy checks
            if policy_rules is None:
                policy_rules = {
                    'min_password_length': 8,
                    'require_antivirus': True,
                    'require_firewall': True,
                    'require_updates': True,
                    'audit_logging_enabled': True
                }
            
            # Check password policy (if AD available)
            try:
                from integrations.ad_client import ADClient
                # This would check AD password policy
                results['checks'].append({
                    'check': 'password_policy',
                    'status': 'info',
                    'message': 'Password policy check not implemented'
                })
            except:
                pass
            
            # Check antivirus (if security manager available)
            try:
                from integrations.security_manager import SecurityManager
                security_mgr = SecurityManager()
                defender_status = security_mgr.get_defender_status()
                
                if defender_status.get('AntivirusEnabled'):
                    results['checks'].append({
                        'check': 'antivirus_enabled',
                        'status': 'pass',
                        'message': 'Antivirus is enabled'
                    })
                    results['passed'] += 1
                else:
                    results['checks'].append({
                        'check': 'antivirus_enabled',
                        'status': 'fail',
                        'message': 'Antivirus is not enabled'
                    })
                    results['failed'] += 1
            except:
                results['checks'].append({
                    'check': 'antivirus_enabled',
                    'status': 'warning',
                    'message': 'Could not verify antivirus status'
                })
                results['warnings'] += 1
            
            # Check firewall
            try:
                if defender_status.get('FirewallEnabled'):
                    results['checks'].append({
                        'check': 'firewall_enabled',
                        'status': 'pass',
                        'message': 'Firewall is enabled'
                    })
                    results['passed'] += 1
                else:
                    results['checks'].append({
                        'check': 'firewall_enabled',
                        'status': 'fail',
                        'message': 'Firewall is not enabled'
                    })
                    results['failed'] += 1
            except:
                results['checks'].append({
                    'check': 'firewall_enabled',
                    'status': 'warning',
                    'message': 'Could not verify firewall status'
                })
                results['warnings'] += 1
            
            # Check audit logging
            audit_log_exists = os.path.exists(self.audit_log_path)
            if audit_log_exists:
                results['checks'].append({
                    'check': 'audit_logging',
                    'status': 'pass',
                    'message': 'Audit logging is enabled'
                })
                results['passed'] += 1
            else:
                results['checks'].append({
                    'check': 'audit_logging',
                    'status': 'warning',
                    'message': 'Audit logging file not found'
                })
                results['warnings'] += 1
            
            # Determine overall compliance status
            if results['failed'] == 0 and results['warnings'] == 0:
                results['compliance_status'] = 'compliant'
            elif results['failed'] == 0:
                results['compliance_status'] = 'mostly_compliant'
            else:
                results['compliance_status'] = 'non_compliant'
            
            return results
            
        except Exception:
            logging.exception("Failed to verify security policy")
            return {'compliance_status': 'error'}

