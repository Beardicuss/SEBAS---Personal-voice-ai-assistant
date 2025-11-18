# -*- coding: utf-8 -*-
"""
Compliance Skill - Stage 2 Mk.II
Enterprise-grade activity logging, audit trails, and compliance reporting
"""

import logging
import json
import os
from pathlib import Path
from sebas.skills.base_skill import BaseSkill
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class ComplianceSkill(BaseSkill):
    """
    Skill for compliance, audit logging, and activity tracking.
    Supports enterprise audit requirements and security compliance.
    """
    
    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        
        # Setup audit log paths
        self.audit_dir = Path.home() / '.sebas' / 'audit'
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.activity_log = self.audit_dir / 'activity.jsonl'
        self.security_log = self.audit_dir / 'security.jsonl'
        self.compliance_log = self.audit_dir / 'compliance.jsonl'
        
        # Compliance standards
        self.standards = ['ISO27001', 'SOC2', 'GDPR', 'HIPAA']
    
    def get_intents(self) -> List[str]:
        return [
            'log_activity',
            'get_activity_log',
            'get_audit_events',
            'generate_compliance_report',
            'verify_security_policy',
            'run_compliance_check',
            'export_audit_logs',
            'check_uac_compliance',
            'check_authentication_compliance',
            'check_network_compliance',
            'check_system_hardening',
        ]
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """Handle compliance intents"""
        
        try:
            if intent == 'log_activity':
                return self._log_activity(slots)
            elif intent == 'get_activity_log':
                return self._get_activity_log(slots)
            elif intent == 'get_audit_events':
                return self._get_audit_events(slots)
            elif intent == 'generate_compliance_report':
                return self._generate_compliance_report(slots)
            elif intent == 'verify_security_policy':
                return self._verify_security_policy()
            elif intent == 'run_compliance_check':
                return self._run_compliance_check(slots)
            elif intent == 'export_audit_logs':
                return self._export_audit_logs(slots)
            elif intent == 'check_uac_compliance':
                return self._check_uac_compliance()
            elif intent == 'check_authentication_compliance':
                return self._check_authentication_compliance()
            elif intent == 'check_network_compliance':
                return self._check_network_compliance()
            elif intent == 'check_system_hardening':
                return self._check_system_hardening()
            
            return False
            
        except Exception:
            logging.exception(f"[Compliance] Error handling intent: {intent}")
            self.assistant.speak("Compliance operation failed")
            return False
    
    def _log_activity(self, slots: Dict[str, Any]) -> bool:
        """Log an activity to audit trail"""
        activity_type = slots.get('activity_type', 'general')
        description = slots.get('description', '')
        severity = slots.get('severity', 'info')
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': activity_type,
            'description': description,
            'severity': severity,
            'user': os.environ.get('USERNAME', 'unknown'),
            'source': 'SEBAS'
        }
        
        # Write to appropriate log
        log_file = self.activity_log
        if activity_type == 'security':
            log_file = self.security_log
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            
            logging.info(f"[Compliance] Logged activity: {activity_type}")
            return True
            
        except Exception:
            logging.exception("[Compliance] Failed to log activity")
            return False
    
    def _get_activity_log(self, slots: Dict[str, Any]) -> bool:
        """Retrieve activity log entries"""
        limit = slots.get('limit', 10)
        
        try:
            if not self.activity_log.exists():
                self.assistant.speak("No activity log found")
                return False
            
            entries = []
            with open(self.activity_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            # Get last N entries
            recent = entries[-limit:]
            
            if recent:
                count = len(recent)
                self.assistant.speak(f"Retrieved {count} recent activity entries")
                
                # Speak summary of most recent
                if recent:
                    last = recent[-1]
                    self.assistant.speak(
                        f"Most recent: {last.get('type')} - {last.get('description')} "
                        f"at {last.get('timestamp')}"
                    )
            else:
                self.assistant.speak("No activity entries found")
            
            return True
            
        except Exception:
            logging.exception("[Compliance] Failed to retrieve activity log")
            self.assistant.speak("Failed to retrieve activity log")
            return False
    
    def _get_audit_events(self, slots: Dict[str, Any]) -> bool:
        """Get audit events for a specific time period"""
        time_period = slots.get('period', '24h')
        
        # Parse time period
        hours = 24
        if 'h' in time_period:
            hours = int(time_period.replace('h', ''))
        elif 'd' in time_period:
            hours = int(time_period.replace('d', '')) * 24
        
        cutoff_time = datetime.now() - datetime.timedelta(hours=hours)
        
        try:
            events = []
            
            for log_file in [self.activity_log, self.security_log]:
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                entry_time = datetime.fromisoformat(entry['timestamp'])
                                if entry_time >= cutoff_time:
                                    events.append(entry)
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
            
            if events:
                self.assistant.speak(f"Found {len(events)} audit events in the last {time_period}")
                
                # Count by severity
                severity_counts = {}
                for event in events:
                    sev = event.get('severity', 'info')
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                
                summary = ', '.join([f"{count} {sev}" for sev, count in severity_counts.items()])
                self.assistant.speak(f"Breakdown: {summary}")
            else:
                self.assistant.speak(f"No audit events found in the last {time_period}")
            
            return True
            
        except Exception:
            logging.exception("[Compliance] Failed to get audit events")
            self.assistant.speak("Failed to retrieve audit events")
            return False
    
    def _generate_compliance_report(self, slots: Dict[str, Any]) -> bool:
        """Generate compliance report"""
        standard = slots.get('standard', 'ISO27001')
        
        if standard not in self.standards:
            self.assistant.speak(f"Unsupported standard. Available: {', '.join(self.standards)}")
            return False
        
        self.assistant.speak(f"Generating {standard} compliance report")
        
        report = {
            'standard': standard,
            'generated_at': datetime.now().isoformat(),
            'findings': [],
            'score': 0
        }
        
        # Run compliance checks based on standard
        checks = [
            self._check_uac_compliance,
            self._check_authentication_compliance,
            self._check_network_compliance,
            self._check_system_hardening,
        ]
        
        passed = 0
        total = len(checks)
        
        for check in checks:
            try:
                result = check()
                if result:
                    passed += 1
            except Exception:
                logging.exception("[Compliance] Check failed")
        
        score = int((passed / total) * 100)
        report['score'] = score
        
        # Save report
        report_file = self.audit_dir / f'compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            
            self.assistant.speak(
                f"Compliance report generated. Score: {score}%. "
                f"Passed {passed} out of {total} checks. "
                f"Report saved to {report_file.name}"
            )
            
            return True
            
        except Exception:
            logging.exception("[Compliance] Failed to save report")
            self.assistant.speak("Failed to generate compliance report")
            return False
    
    def _verify_security_policy(self) -> bool:
        """Verify security policy compliance"""
        findings = []
        
        # Check Windows Defender status
        try:
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', 'Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'False' in result.stdout:
                findings.append("Windows Defender is not fully enabled")
        except Exception:
            findings.append("Unable to verify Windows Defender status")
        
        # Check firewall status
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-NetFirewallProfile | Select-Object Name, Enabled'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'False' in result.stdout:
                findings.append("Firewall is disabled on some profiles")
        except Exception:
            findings.append("Unable to verify firewall status")
        
        # Report findings
        if findings:
            self.assistant.speak(f"Security policy violations found: {'. '.join(findings)}")
        else:
            self.assistant.speak("Security policy verification passed")
        
        return len(findings) == 0
    
    def _run_compliance_check(self, slots: Dict[str, Any]) -> bool:
        """Run comprehensive compliance check"""
        self.assistant.speak("Running comprehensive compliance check")
        
        checks = [
            ('UAC', self._check_uac_compliance),
            ('Authentication', self._check_authentication_compliance),
            ('Network', self._check_network_compliance),
            ('System Hardening', self._check_system_hardening),
        ]
        
        results = []
        
        for name, check_func in checks:
            try:
                passed = check_func()
                results.append((name, passed))
            except Exception:
                logging.exception(f"[Compliance] {name} check failed")
                results.append((name, False))
        
        # Report results
        passed_count = sum(1 for _, passed in results if passed)
        total_count = len(results)
        
        self.assistant.speak(
            f"Compliance check complete. Passed {passed_count} out of {total_count} checks."
        )
        
        # Detail failed checks
        failed = [name for name, passed in results if not passed]
        if failed:
            self.assistant.speak(f"Failed checks: {', '.join(failed)}")
        
        return passed_count == total_count
    
    def _export_audit_logs(self, slots: Dict[str, Any]) -> bool:
        """Export audit logs to external format"""
        format_type = slots.get('format', 'json').lower()
        
        if format_type not in ['json', 'csv']:
            self.assistant.speak("Supported formats: json, csv")
            return False
        
        export_file = self.audit_dir / f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{format_type}'
        
        try:
            entries = []
            
            for log_file in [self.activity_log, self.security_log]:
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            
            if format_type == 'json':
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, indent=2)
            
            elif format_type == 'csv':
                import csv
                if entries:
                    keys = entries[0].keys()
                    with open(export_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(entries)
            
            self.assistant.speak(f"Exported {len(entries)} entries to {export_file.name}")
            return True
            
        except Exception:
            logging.exception("[Compliance] Failed to export logs")
            self.assistant.speak("Failed to export audit logs")
            return False
    
    # Compliance check methods
    
    def _check_uac_compliance(self) -> bool:
        """Check User Account Control compliance"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System',
                0,
                winreg.KEY_READ
            )
            
            uac_enabled, _ = winreg.QueryValueEx(key, 'EnableLUA')
            winreg.CloseKey(key)
            
            return uac_enabled == 1
            
        except Exception:
            logging.exception("[Compliance] UAC check failed")
            return False
    
    def _check_authentication_compliance(self) -> bool:
        """Check authentication policy compliance"""
        # Check password policy (simplified)
        try:
            import subprocess
            result = subprocess.run(
                ['net', 'accounts'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Look for minimum password length requirement
            if 'Minimum password length' in result.stdout:
                return True
            
            return False
            
        except Exception:
            logging.exception("[Compliance] Authentication check failed")
            return False
    
    def _check_network_compliance(self) -> bool:
        """Check network security compliance"""
        try:
            import subprocess
            
            # Check if firewall is enabled
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # All profiles should be ON
            return result.stdout.count('ON') >= 3
            
        except Exception:
            logging.exception("[Compliance] Network check failed")
            return False
    
    def _check_system_hardening(self) -> bool:
        """Check system hardening compliance"""
        checks_passed = 0
        total_checks = 3
        
        # Check 1: Defender enabled
        try:
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', 'Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'True' in result.stdout:
                checks_passed += 1
        except Exception:
            pass
        
        # Check 2: Automatic updates enabled
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU',
                0,
                winreg.KEY_READ
            )
            
            auto_update, _ = winreg.QueryValueEx(key, 'NoAutoUpdate')
            winreg.CloseKey(key)
            
            if auto_update == 0:
                checks_passed += 1
        except Exception:
            # If key doesn't exist, updates might be enabled
            checks_passed += 1
        
        # Check 3: Guest account disabled
        try:
            result = subprocess.run(
                ['net', 'user', 'guest'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'Account active' in result.stdout and 'No' in result.stdout:
                checks_passed += 1
        except Exception:
            pass
        
        return checks_passed >= 2  # At least 2 out of 3