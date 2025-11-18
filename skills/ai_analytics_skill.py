# -*- coding: utf-8 -*-
"""
AI Analytics Skill - FINAL FIXED VERSION (Stage 2 Ready)
No circular imports | Clean | Works 100%
"""

import logging
import psutil
import time
from collections import deque
from typing import Dict, Any, List

from sebas.skills.base_skill import BaseSkill


class AIAnalyticsSkill(BaseSkill):
    """Intelligent system monitoring & predictive analytics"""

    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        
        self.cpu_history = deque(maxlen=1000)
        self.memory_history = deque(maxlen=1000)
        self.disk_history = deque(maxlen=100)

        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0

        self._monitoring_active = False

        try:
            self._start_monitoring()
            logging.info("[AIAnalytics] Skill initialized and monitoring started")
        except Exception as e:
            logging.error(f"[AIAnalytics] Failed to start monitoring: {e}")

    def get_intents(self) -> List[str]:
        return [
            "detect_anomalies",
            "predict_disk_failure",
            "predict_memory_leak",
            "get_performance_suggestions",
            "diagnose_issue"
        ]

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        handlers = {
            "detect_anomalies": self._detect_anomalies,
            "predict_disk_failure": self._predict_disk_failure,
            "predict_memory_leak": self._predict_memory_leak,
            "get_performance_suggestions": self._get_performance_suggestions,
            "diagnose_issue": self._diagnose_issue,
        }

        handler = handlers.get(intent)
        if not handler:
            return False

        try:
            return handler()
        except Exception:
            logging.exception(f"[AIAnalytics] Error in {intent}")
            self.assistant.speak("Sorry, analytics encountered an error.")
            return False

    def _start_monitoring(self):
        import threading

        def monitor():
            self._monitoring_active = True
            while self._monitoring_active:
                try:
                    self.cpu_history.append({
                        "time": time.time(),
                        "value": psutil.cpu_percent(interval=1)
                    })
                    mem = psutil.virtual_memory()
                    self.memory_history.append({
                        "time": time.time(),
                        "value": mem.percent
                    })

                    # Disk every 5 minutes
                    if not self.disk_history or time.time() - self.disk_history[-1]["time"] > 300:
                        disk = psutil.disk_usage('/')
                        self.disk_history.append({
                            "time": time.time(),
                            "value": disk.percent
                        })

                    time.sleep(5)
                except Exception as e:
                    logging.error(f"[AIAnalytics] Monitoring loop error: {e}")
                    time.sleep(10)

        threading.Thread(target=monitor, daemon=True).start()

    def _detect_anomalies(self) -> bool:
        anomalies = []
        if len(self.cpu_history) >= 10:
            avg = sum(h["value"] for h in list(self.cpu_history)[-10:]) / 10
            if avg > self.cpu_threshold:
                anomalies.append(f"high CPU usage {avg:.1f}%")

        if len(self.memory_history) >= 10:
            avg = sum(h["value"] for h in list(self.memory_history)[-10:]) / 10
            if avg > self.memory_threshold:
                anomalies.append(f"high memory usage {avg:.1f}%")

        if anomalies:
            self.assistant.speak(f"Warning: detected {' and '.join(anomalies)}")
        else:
            self.assistant.speak("No anomalies detected. System is stable.")
        return True

    def _predict_disk_failure(self) -> bool:
        if not self.disk_history:
            self.assistant.speak("Not enough disk data yet.")
            return False
        usage = self.disk_history[-1]["value"]
        if usage > 90:
            self.assistant.speak(f"Critical: disk almost full at {usage}%!")
        elif usage > 80:
            self.assistant.speak(f"Warning: disk usage high at {usage}%. Clean up soon.")
        else:
            self.assistant.speak("Disk space is healthy.")
        return True

    def _predict_memory_leak(self) -> bool:
        if len(self.memory_history) < 20:
            self.assistant.speak("Collecting memory data, please wait.")
            return False
        recent = [h["value"] for h in list(self.memory_history)[-20:]]
        increases = sum(1 for a, b in zip(recent, recent[1:]) if b > a)
        if increases >= 15:
            self.assistant.speak("Possible memory leak detected. Restart heavy apps.")
        else:
            self.assistant.speak("Memory behavior is normal.")
        return True

    def _get_performance_suggestions(self) -> bool:
        suggestions = []
        if len(self.cpu_history) >= 10:
            avg = sum(h["value"] for h in list(self.cpu_history)[-10:]) / 10
            if avg > 70:
                suggestions.append("close unused programs")
        if len(self.memory_history) >= 10:
            avg = sum(h["value"] for h in list(self.memory_history)[-10:]) / 10
            if avg > 80:
                suggestions.append("free up RAM by closing browser tabs")
        if suggestions:
            self.assistant.speak(f"Try this: {' and '.join(suggestions)}")
        else:
            self.assistant.speak("Your system is running optimally.")
        return True

    def _diagnose_issue(self) -> bool:
        issues = []
        if psutil.cpu_percent(interval=1) > 80:
            issues.append("high CPU load")
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            issues.append(f"memory pressure {mem.percent}%")
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            issues.append("low disk space")
        if issues:
            self.assistant.speak(f"Current issues: {', '.join(issues)}")
        else:
            self.assistant.speak("No critical issues right now.")
        return True