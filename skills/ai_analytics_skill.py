# Replace skills/ai_analytics_skill.py with this corrected version

# -*- coding: utf-8 -*-
"""
AI Analytics Skill - Stage 2 Mk.II (FIXED)
Properly inherits from BaseSkill
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
    """
    
    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        
        # Historical data storage (in-memory)
        self.cpu_history = deque(maxlen=1000)
        self.memory_history = deque(maxlen=1000)
        self.disk_history = deque(maxlen=100)
        
        # Anomaly thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0
        
        # Monitoring state
        self._monitoring_active = False
        
        # Start background monitoring
        try:
            self._start_monitoring()
            logging.info("[AIAnalytics] Initialized successfully")
        except Exception as e:
            logging.error(f"[AIAnalytics] Failed to start monitoring: {e}")
    
    def get_intents(self) -> List[str]:
        return [
            'detect_anomalies',
            'predict_disk_failure',
            'predict_memory_leak',
            'get_performance_suggestions',
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
                    
                    # Disk usage (less frequent)
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
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logging.info("[AIAnalytics] Background monitoring started")
    
    def _detect_anomalies(self) -> bool:
        """Detect system anomalies"""
        anomalies = []
        
        # CPU check
        if len(self.cpu_history) >= 10:
            recent_cpu = [x['value'] for x in list(self.cpu_history)[-10:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu)
            
            if avg_cpu > self.cpu_threshold:
                anomalies.append(f"High CPU usage: {avg_cpu:.1f}%")
        
        # Memory check
        if len(self.memory_history) >= 10:
            recent_mem = [x['value'] for x in list(self.memory_history)[-10:]]
            avg_mem = sum(recent_mem) / len(recent_mem)
            
            if avg_mem > self.memory_threshold:
                anomalies.append(f"High memory usage: {avg_mem:.1f}%")
        
        # Report findings
        if anomalies:
            self.assistant.speak(f"Detected {len(anomalies)} anomalies: {'. '.join(anomalies)}")
        else:
            self.assistant.speak("No anomalies detected. System is running normally.")
        
        return True
    
    def _predict_disk_failure(self) -> bool:
        """Predict potential disk failure"""
        if len(self.disk_history) < 3:
            self.assistant.speak("Not enough data to predict disk failure.")
            return False
        
        recent = list(self.disk_history)[-3:]
        current_usage = recent[-1]['value']
        
        if current_usage > 90:
            self.assistant.speak(f"Warning: Disk usage critical at {current_usage}%. Consider cleanup.")
        elif current_usage > 80:
            self.assistant.speak(f"Disk usage at {current_usage}%. Monitor closely.")
        else:
            self.assistant.speak("Disk usage is healthy.")
        
        return True
    
    def _predict_memory_leak(self) -> bool:
        """Predict memory leak"""
        if len(self.memory_history) < 20:
            self.assistant.speak("Not enough data to analyze memory trends.")
            return False
        
        recent = [x['value'] for x in list(self.memory_history)[-20:]]
        
        # Simple trend detection
        increasing = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        
        if increasing >= 15:  # 75% increasing
            self.assistant.speak("Potential memory leak detected. Consider restarting applications.")
        else:
            self.assistant.speak("Memory usage is normal.")
        
        return True
    
    def _get_performance_suggestions(self) -> bool:
        """Provide performance suggestions"""
        suggestions = []
        
        # CPU check
        if len(self.cpu_history) >= 10:
            avg_cpu = sum(x['value'] for x in list(self.cpu_history)[-10:]) / 10
            if avg_cpu > 70:
                suggestions.append("CPU usage is high. Consider closing unnecessary applications.")
        
        # Memory check  
        if len(self.memory_history) >= 10:
            avg_mem = sum(x['value'] for x in list(self.memory_history)[-10:]) / 10
            if avg_mem > 80:
                suggestions.append("Memory usage is high. Close browser tabs or heavy applications.")
        
        if suggestions:
            self.assistant.speak(f"Performance suggestions: {'. '.join(suggestions)}")
        else:
            self.assistant.speak("System performance is optimal.")
        
        return True
    
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
        
        if issues:
            self.assistant.speak(f"Diagnosed {len(issues)} issues: {'. '.join(issues)}")
        else:
            self.assistant.speak("System diagnosis complete. No critical issues found.")
        
        return True