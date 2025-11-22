# -*- coding: utf-8 -*-
"""
AI Analytics Skill
Phase 6.1: Predictive Analytics and Anomaly Detection
"""

from sebas.skills.base_skill import BaseSkill
from typing import Dict, Any
import logging


class AIAnalyticsSkill(BaseSkill):
    """
    Skill for AI-powered analytics and predictions.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'detect_anomalies',
            'predict_disk_failure',
            'predict_memory_leak',
            'get_performance_suggestions',
            'get_troubleshooting_guide',
            'diagnose_issue'
        ]
        self.anomaly_detector = None
        self.predictive_analyzer = None
        self.performance_optimizer = None
        self.troubleshooting_guide = None
        self._init_analytics()
    
    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        return intent in self.intents
    
    def get_intents(self) -> list:
        """Get list of intents this skill can handle."""
        return self.intents
    
    def _init_analytics(self):
        """Initialize analytics components."""
        try:
            from sebas.integrations.ai_analytics import (
                AnomalyDetector, PredictiveAnalyzer,
                PerformanceOptimizer, TroubleshootingGuide
            )
            self.anomaly_detector = AnomalyDetector()
            self.predictive_analyzer = PredictiveAnalyzer()
            self.performance_optimizer = PerformanceOptimizer()
            self.troubleshooting_guide = TroubleshootingGuide()
        except Exception:
            logging.exception("Failed to initialize AI analytics")
    
    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'detect_anomalies':
            return self._handle_detect_anomalies()
        elif intent == 'predict_disk_failure':
            return self._handle_predict_disk_failure(slots)
        elif intent == 'predict_memory_leak':
            return self._handle_predict_memory_leak(slots)
        elif intent == 'get_performance_suggestions':
            return self._handle_get_performance_suggestions()
        elif intent == 'get_troubleshooting_guide':
            return self._handle_get_troubleshooting_guide(slots)
        elif intent == 'diagnose_issue':
            return self._handle_diagnose_issue(slots)
        return False
    
    def _handle_detect_anomalies(self) -> bool:
        """Handle detect anomalies command."""
        try:
            if not self.anomaly_detector:
                self.assistant.speak("Anomaly detection not available")
                return False
            
            # Collect metrics and detect anomalies
            metrics = self.anomaly_detector.collect_metrics()
            anomalies = self.anomaly_detector.detect_anomalies(metrics)
            
            if anomalies:
                critical = [a for a in anomalies if a.get('severity') == 'critical']
                high = [a for a in anomalies if a.get('severity') == 'high']
                
                if critical:
                    self.assistant.speak(f"Detected {len(critical)} critical anomalies and {len(high)} high severity anomalies")
                else:
                    self.assistant.speak(f"Detected {len(anomalies)} anomalies")
            else:
                self.assistant.speak("No anomalies detected")
            
            return True
            
        except Exception:
            logging.exception("Failed to detect anomalies")
            self.assistant.speak("Failed to detect anomalies")
            return False
    
    def _handle_predict_disk_failure(self, slots: dict) -> bool:
        """Handle predict disk failure command."""
        try:
            if not self.predictive_analyzer:
                self.assistant.speak("Predictive analysis not available")
                return False
            
            path = slots.get('path', 'C:\\')
            days = int(slots.get('days', 30))
            
            prediction = self.predictive_analyzer.predict_disk_space_failure(path, days)
            
            if prediction:
                days_until = prediction.get('predicted_failure_days', 0)
                risk = prediction.get('risk_level', 'unknown')
                self.assistant.speak(
                    f"Disk space prediction: {days_until:.0f} days until full. Risk level: {risk}"
                )
            else:
                self.assistant.speak("No disk space issues predicted in the near future")
            
            return True
            
        except Exception:
            logging.exception("Failed to predict disk failure")
            self.assistant.speak("Failed to predict disk failure")
            return False
    
    def _handle_predict_memory_leak(self, slots: dict) -> bool:
        """Handle predict memory leak command."""
        try:
            if not self.predictive_analyzer:
                self.assistant.speak("Predictive analysis not available")
                return False
            
            process_name = slots.get('process_name')
            prediction = self.predictive_analyzer.predict_memory_leak(process_name)
            
            if prediction:
                risk = prediction.get('risk_level', 'unknown')
                recommendation = prediction.get('recommendation', '')
                self.assistant.speak(f"Memory leak prediction: Risk level {risk}. {recommendation}")
            else:
                self.assistant.speak("No memory leak issues detected")
            
            return True
            
        except Exception:
            logging.exception("Failed to predict memory leak")
            self.assistant.speak("Failed to predict memory leak")
            return False
    
    def _handle_get_performance_suggestions(self) -> bool:
        """Handle get performance suggestions command."""
        try:
            if not self.performance_optimizer:
                self.assistant.speak("Performance optimizer not available")
                return False
            
            suggestions = self.performance_optimizer.analyze_performance()
            
            if suggestions:
                critical = [s for s in suggestions if s.get('severity') == 'critical']
                high = [s for s in suggestions if s.get('severity') == 'high']
                
                if critical:
                    self.assistant.speak(
                        f"Found {len(critical)} critical and {len(high)} high priority performance issues. "
                        f"Top suggestion: {critical[0].get('suggestion', '')}"
                    )
                else:
                    self.assistant.speak(f"Found {len(suggestions)} performance suggestions")
            else:
                self.assistant.speak("No performance issues detected")
            
            return True
            
        except Exception:
            logging.exception("Failed to get performance suggestions")
            self.assistant.speak("Failed to get performance suggestions")
            return False
    
    def _handle_get_troubleshooting_guide(self, slots: dict) -> bool:
        """Handle get troubleshooting guide command."""
        try:
            if not self.troubleshooting_guide:
                self.assistant.speak("Troubleshooting guide not available")
                return False
            
            issue_type = slots.get('issue_type', '')
            guide = self.troubleshooting_guide.get_troubleshooting_guide(issue_type)
            
            if guide:
                solutions = guide.get('solutions', [])
                if solutions:
                    self.assistant.speak(f"Troubleshooting guide for {issue_type}. First solution: {solutions[0]}")
                else:
                    self.assistant.speak(f"Found troubleshooting guide for {issue_type}")
            else:
                self.assistant.speak(f"No troubleshooting guide found for {issue_type}")
            
            return guide is not None
            
        except Exception:
            logging.exception("Failed to get troubleshooting guide")
            self.assistant.speak("Failed to get troubleshooting guide")
            return False
    
    def _handle_diagnose_issue(self, slots: dict) -> bool:
        """Handle diagnose issue command."""
        try:
            if not self.troubleshooting_guide:
                self.assistant.speak("Diagnostic system not available")
                return False
            
            symptoms_str = slots.get('symptoms', '')
            symptoms = [s.strip() for s in symptoms_str.split(',')] if symptoms_str else []
            
            if not symptoms:
                self.assistant.speak("Please specify symptoms to diagnose")
                return False
            
            matches = self.troubleshooting_guide.diagnose_issue(symptoms)
            
            if matches:
                top_match = matches[0]
                issue_type = top_match.get('issue_type', 'unknown')
                confidence = top_match.get('confidence', 0)
                self.assistant.speak(
                    f"Diagnosis: {issue_type} with {confidence*100:.0f}% confidence"
                )
            else:
                self.assistant.speak("Could not diagnose issue from provided symptoms")
            
            return len(matches) > 0
            
        except Exception:
            logging.exception("Failed to diagnose issue")
            self.assistant.speak("Failed to diagnose issue")
            return False