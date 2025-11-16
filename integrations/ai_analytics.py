# -*- coding: utf-8 -*-
"""
AI Analytics Skill - Stage 2 Mk.II (FIXED)
Provides predictive analytics and anomaly detection using statistical methods
Completely self-contained with no external integration dependencies
"""

import logging
import psutil
import time
from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, Any, List, Optional
from sebas.datetime import datetime, timedelta
from collections import deque


class AIAnalyticsSkill(BaseSkill):
    """
    Skill for predictive analytics and intelligent system monitoring.
    Uses statistical methods and heuristics (no heavy ML required).
    Completely self-contained - no external integration dependencies.
    """
    
    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        
        # Historical data storage (in-memory)
        self.cpu_history = deque(maxlen=1000)
        self.memory_history = deque(maxlen=1000)
        self.disk_history = deque(maxlen=100)
        self.network_history = deque(maxlen=1000)
        
        # Anomaly thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0
        
        # Monitoring state
        self._monitoring_active = False
        
        # Start background monitoring
        try:
            self._start_monitoring()
            logging.info("[AIAnalytics] Initialized successfully with background monitoring")
        except Exception as e:
            logging.error(f"[AIAnalytics] Failed to start monitoring: {e}")
            # Don't fail completely - skill can still work without background monitoring
    
    def get_intents(self) -> List[str]:
        return [
            'detect_anomalies',
            'predict_disk_failure',
            'predict_memory_leak',
            'get_performance_suggestions',
            'get_troubleshooting_guide',
            'diagnose_issue',
        ]
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """Handle AI analytics intents"""
        
        try:
            if intent == 'detect_anomalies':
                return self._detect_anomalies()
            elif intent == 'predict_disk_failure':
                return self._predict_disk_failure()
            elif intent == 'predict_memory_leak':
                return self._predict_memory_leak()
            elif intent == 'get_performance_suggestions':
                return self._get_performance_suggestions()
            elif intent == 'get_troubleshooting_guide':
                return self._get_troubleshooting_guide(slots)
            elif intent == 'diagnose_issue':
                return self._diagnose_issue(slots)
            
            return False
            
        except Exception:
            logging.exception(f"[AIAnalytics] Error handling intent: {intent}")
            self.assistant.speak("Analytics failed")
            return False
    
    def _start_monitoring(self):
        """Start background monitoring thread"""
        import threading
        
        def monitor_loop():
            self._monitoring_active = True
            
            while self._monitoring_active:
                try:
                    # Collect metrics every 5 seconds
                    self.cpu_history.append({
                        'time': time.time(),
                        'value': psutil.cpu_percent(interval=1)
                    })
                    
                    mem = psutil.virtual_memory()
                    self.memory_history.append({
                        'time': time.time(),
                        'value': mem.percent
                    })
                    
                    # Disk usage (less frequent - every 5 minutes)
                    if len(self.disk_history) == 0 or time.time() - self.disk_history[-1]['time'] > 300:
                        disk = psutil.disk_usage('/')
                        self.disk_history.append({
                            'time': time.time(),
                            'value': disk.percent
                        })
                    
                    time.sleep(5)
                    
                except Exception as e:
                    logging.error(f"[AIAnalytics] Monitoring error: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=monitor_loop, daemon=True, name="AIAnalyticsMonitor")
        thread.start()
        logging.info("[AIAnalytics] Background monitoring thread started")
    
    def _detect_anomalies(self) -> bool:
        """Detect system anomalies using statistical methods"""
        anomalies = []
        
        # CPU anomaly detection
        if len(self.cpu_history) >= 10:
            recent_cpu = [x['value'] for x in list(self.cpu_history)[-10:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu)
            
            if avg_cpu > self.cpu_threshold:
                anomalies.append(f"High CPU usage: {avg_cpu:.1f}%")
        
        # Memory anomaly detection
        if len(self.memory_history) >= 10:
            recent_mem = [x['value'] for x in list(self.memory_history)[-10:]]
            avg_mem = sum(recent_mem) / len(recent_mem)
            
            if avg_mem > self.memory_threshold:
                anomalies.append(f"High memory usage: {avg_mem:.1f}%")
            
            # Check for memory leak pattern (steady increase)
            if self._detect_memory_leak_pattern(recent_mem):
                anomalies.append("Potential memory leak detected")
        
        # Disk space anomaly
        if len(self.disk_history) >= 1:
            recent_disk = self.disk_history[-1]['value']
            if recent_disk > self.disk_threshold:
                anomalies.append(f"Low disk space: {100 - recent_disk:.1f}% free")
        
        # Report findings
        if anomalies:
            self.assistant.speak(f"Detected {len(anomalies)} anomalies: {'. '.join(anomalies)}")
        else:
            self.assistant.speak("No anomalies detected. System is running normally.")
        
        return True
    
    def _detect_memory_leak_pattern(self, values: List[float]) -> bool:
        """Detect if memory usage shows leak pattern (steady increase)"""
        if len(values) < 5:
            return False
        
        # Check if each value is higher than previous (with small tolerance)
        increases = 0
        for i in range(1, len(values)):
            if values[i] > values[i-1] + 0.5:  # 0.5% tolerance
                increases += 1
        
        # If 80% of samples show increase, likely a leak
        return increases >= len(values) * 0.8
    
    def _predict_disk_failure(self) -> bool:
        """Predict potential disk failure based on trends"""
        if len(self.disk_history) < 3:
            self.assistant.speak("Not enough data to predict disk failure. Please wait a few minutes for data collection.")
            return False
        
        # Calculate rate of disk space consumption
        recent_points = list(self.disk_history)[-3:]
        time_diff = recent_points[-1]['time'] - recent_points[0]['time']
        usage_diff = recent_points[-1]['value'] - recent_points[0]['value']
        
        if time_diff > 0:
            rate_per_hour = (usage_diff / time_diff) * 3600
            
            if rate_per_hour > 0.5:  # Losing more than 0.5% per hour
                # Calculate time until full
                current_free = 100 - recent_points[-1]['value']
                hours_until_full = current_free / rate_per_hour
                days_until_full = hours_until_full / 24
                
                if days_until_full < 7:
                    self.assistant.speak(
                        f"Warning: At current rate, disk will be full in {days_until_full:.1f} days. "
                        f"Consider running disk cleanup."
                    )
                else:
                    self.assistant.speak(f"Disk usage is normal. Approximately {days_until_full:.0f} days of space remaining.")
            else:
                self.assistant.speak("Disk usage is stable. No immediate concerns.")
        else:
            self.assistant.speak("Disk usage is stable.")
        
        return True
    
    def _predict_memory_leak(self) -> bool:
        """Predict memory leak based on trends"""
        if len(self.memory_history) < 20:
            self.assistant.speak("Not enough data to analyze memory trends. Background monitoring is collecting data.")
            return False
        
        recent = [x['value'] for x in list(self.memory_history)[-20:]]
        
        if self._detect_memory_leak_pattern(recent):
            # Calculate leak rate
            time_span = self.memory_history[-1]['time'] - self.memory_history[-20]['time']
            mem_increase = recent[-1] - recent[0]
            rate_per_hour = (mem_increase / time_span) * 3600
            
            self.assistant.speak(
                f"Potential memory leak detected. Memory increasing at {rate_per_hour:.2f}% per hour. "
                f"Consider restarting affected applications."
            )
            
            # Try to identify culprit process
            try:
                processes = sorted(
                    psutil.process_iter(['name', 'memory_percent']),
                    key=lambda p: p.info['memory_percent'],
                    reverse=True
                )
                
                top_process = processes[0]
                if top_process.info['memory_percent'] > 20:
                    self.assistant.speak(
                        f"Top memory consumer: {top_process.info['name']} "
                        f"using {top_process.info['memory_percent']:.1f}%"
                    )
            except Exception:
                pass
        else:
            self.assistant.speak("Memory usage is normal. No leak pattern detected.")
        
        return True
    
    def _get_performance_suggestions(self) -> bool:
        """Provide performance optimization suggestions"""
        suggestions = []
        
        # CPU suggestions
        if len(self.cpu_history) >= 10:
            recent_cpu = [x['value'] for x in list(self.cpu_history)[-10:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu)
            
            if avg_cpu > 70:
                suggestions.append("CPU usage is high. Consider closing unnecessary applications.")
        
        # Memory suggestions
        if len(self.memory_history) >= 10:
            recent_mem = [x['value'] for x in list(self.memory_history)[-10:]]
            avg_mem = sum(recent_mem) / len(recent_mem)
            
            if avg_mem > 80:
                suggestions.append("Memory usage is high. Consider closing browser tabs or heavy applications.")
        
        # Disk suggestions
        if len(self.disk_history) >= 1:
            disk_usage = self.disk_history[-1]['value']
            if disk_usage > 85:
                suggestions.append("Disk space is low. Run disk cleanup or move files to external storage.")
        
        # Check for many running processes
        try:
            process_count = len(psutil.pids())
            if process_count > 200:
                suggestions.append(f"Many processes running ({process_count}). Consider closing unused applications.")
        except Exception:
            pass
        
        # Report suggestions
        if suggestions:
            self.assistant.speak(f"Performance suggestions: {'. '.join(suggestions)}")
        else:
            self.assistant.speak("System performance is optimal. No suggestions at this time.")
        
        return True
    
    def _get_troubleshooting_guide(self, slots: Dict[str, Any]) -> bool:
        """Provide troubleshooting guidance"""
        issue = slots.get('issue', '').lower()
        
        guides = {
            'slow': "For slow performance: Check CPU and memory usage, close unnecessary apps, run disk cleanup, and check for malware.",
            'crash': "For crashes: Check event logs, update drivers, run memory diagnostics, and check for overheating.",
            'network': "For network issues: Check cable connections, restart router, flush DNS cache, and check firewall settings.",
            'disk': "For disk issues: Run disk check, free up space, defragment drive, and check SMART status.",
        }
        
        for key, guide in guides.items():
            if key in issue:
                self.assistant.speak(guide)
                return True
        
        self.assistant.speak("Please specify the issue: slow, crash, network, or disk.")
        return False
    
    def _diagnose_issue(self, slots: Dict[str, Any]) -> bool:
        """Diagnose current system issues"""
        issues = []
        
        # Check CPU
        cpu = psutil.cpu_percent(interval=1)
        if cpu > 80:
            issues.append(f"High CPU usage at {cpu}%")
        
        # Check memory
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            issues.append(f"High memory usage at {mem.percent}%")
        
        # Check disk
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            issues.append(f"Low disk space, only {100 - disk.percent:.1f}% free")
        
        # Check temperatures (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 80:
                            issues.append(f"High temperature: {name} at {entry.current}°C")
        except Exception:
            pass
        
        if issues:
            self.assistant.speak(f"Diagnosed {len(issues)} issues: {'. '.join(issues)}")
        else:
            self.assistant.speak("System diagnosis complete. No critical issues found.")
        
        return True
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status (for debugging)"""
        return {
            'active': self._monitoring_active,
            'cpu_samples': len(self.cpu_history),
            'memory_samples': len(self.memory_history),
            'disk_samples': len(self.disk_history),
        }