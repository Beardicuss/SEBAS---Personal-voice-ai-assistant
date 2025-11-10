# -*- coding: utf-8 -*-
"""
AI-Powered Analytics
Phase 6.1: Predictive Analytics and Anomaly Detection
"""

import logging
import psutil
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import deque
import json
import os


class AnomalyDetector:
    """
    Detects anomalies in system behavior.
    """
    
    def __init__(self, history_window: int = 100):
        """
        Initialize Anomaly Detector.
        
        Args:
            history_window: Number of data points to keep in history
        """
        self.history_window = history_window
        self.cpu_history = deque(maxlen=history_window)
        self.memory_history = deque(maxlen=history_window)
        self.disk_io_history = deque(maxlen=history_window)
        self.network_history = deque(maxlen=history_window)
        self.process_count_history = deque(maxlen=history_window)
    
    def collect_metrics(self) -> Dict[str, float]:
        """
        Collect current system metrics.
        
        Returns:
            Dict with current metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            process_count = len(psutil.pids())
            
            metrics = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
                'network_sent_bytes': network.bytes_sent if network else 0,
                'network_recv_bytes': network.bytes_recv if network else 0,
                'process_count': process_count,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add to history
            self.cpu_history.append(cpu_percent)
            self.memory_history.append(memory.percent)
            if disk_io:
                self.disk_io_history.append(disk_io.read_bytes + disk_io.write_bytes)
            if network:
                self.network_history.append(network.bytes_sent + network.bytes_recv)
            self.process_count_history.append(process_count)
            
            return metrics
            
        except Exception:
            logging.exception("Failed to collect metrics")
            return {}
    
    def detect_anomalies(self, metrics: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Detect anomalies in system metrics.
        
        Args:
            metrics: Optional current metrics (if None, collects new metrics)
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        if metrics is None:
            metrics = self.collect_metrics()
        
        # CPU anomaly detection
        if len(self.cpu_history) > 10:
            cpu_mean = statistics.mean(self.cpu_history)
            cpu_stdev = statistics.stdev(self.cpu_history) if len(self.cpu_history) > 1 else 0
            
            if cpu_stdev > 0:
                z_score = (metrics['cpu_percent'] - cpu_mean) / cpu_stdev
                if abs(z_score) > 2.5:  # 2.5 standard deviations
                    anomalies.append({
                        'type': 'cpu_anomaly',
                        'severity': 'high' if z_score > 3 else 'medium',
                        'metric': 'cpu_percent',
                        'value': metrics['cpu_percent'],
                        'expected_range': f"{cpu_mean - 2*cpu_stdev:.1f} - {cpu_mean + 2*cpu_stdev:.1f}",
                        'description': f"CPU usage is {z_score:.1f} standard deviations from normal"
                    })
        
        # Memory anomaly detection
        if len(self.memory_history) > 10:
            memory_mean = statistics.mean(self.memory_history)
            memory_stdev = statistics.stdev(self.memory_history) if len(self.memory_history) > 1 else 0
            
            if memory_stdev > 0:
                z_score = (metrics['memory_percent'] - memory_mean) / memory_stdev
                if abs(z_score) > 2.5:
                    anomalies.append({
                        'type': 'memory_anomaly',
                        'severity': 'high' if z_score > 3 else 'medium',
                        'metric': 'memory_percent',
                        'value': metrics['memory_percent'],
                        'expected_range': f"{memory_mean - 2*memory_stdev:.1f} - {memory_mean + 2*memory_stdev:.1f}",
                        'description': f"Memory usage is {z_score:.1f} standard deviations from normal"
                    })
        
        # Process count anomaly
        if len(self.process_count_history) > 10:
            process_mean = statistics.mean(self.process_count_history)
            process_stdev = statistics.stdev(self.process_count_history) if len(self.process_count_history) > 1 else 0
            
            if process_stdev > 0:
                z_score = (metrics['process_count'] - process_mean) / process_stdev
                if abs(z_score) > 2.5:
                    anomalies.append({
                        'type': 'process_count_anomaly',
                        'severity': 'medium',
                        'metric': 'process_count',
                        'value': metrics['process_count'],
                        'expected_range': f"{process_mean - 2*process_stdev:.0f} - {process_mean + 2*process_stdev:.0f}",
                        'description': f"Process count is {z_score:.1f} standard deviations from normal"
                    })
        
        # Threshold-based checks
        if metrics['cpu_percent'] > 90:
            anomalies.append({
                'type': 'cpu_threshold',
                'severity': 'critical',
                'metric': 'cpu_percent',
                'value': metrics['cpu_percent'],
                'description': 'CPU usage exceeds 90%'
            })
        
        if metrics['memory_percent'] > 90:
            anomalies.append({
                'type': 'memory_threshold',
                'severity': 'critical',
                'metric': 'memory_percent',
                'value': metrics['memory_percent'],
                'description': 'Memory usage exceeds 90%'
            })
        
        return anomalies


class PredictiveAnalyzer:
    """
    Provides predictive analysis and failure prediction.
    """
    
    def __init__(self):
        """Initialize Predictive Analyzer."""
        self.disk_history = []
        self.memory_history = []
        self.error_history = []
    
    def predict_disk_space_failure(self, path: str = "/", days_ahead: int = 30) -> Optional[Dict[str, Any]]:
        """
        Predict when disk space will run out.
        
        Args:
            path: Disk path to analyze
            days_ahead: Number of days to predict ahead
            
        Returns:
            Prediction dict or None
        """
        try:
            usage = psutil.disk_usage(path)
            current_free = usage.free
            current_used = usage.used
            total = usage.total
            
            # Simple linear prediction based on recent usage changes
            # In production, use more sophisticated models
            if len(self.disk_history) > 7:
                recent_usage = self.disk_history[-7:]
                if len(recent_usage) > 1:
                    # Calculate average daily growth
                    daily_growth = sum(
                        recent_usage[i] - recent_usage[i-1] 
                        for i in range(1, len(recent_usage))
                    ) / (len(recent_usage) - 1)
                    
                    if daily_growth > 0:
                        days_until_full = current_free / daily_growth if daily_growth > 0 else None
                        
                        if days_until_full and days_until_full < days_ahead:
                            return {
                                'path': path,
                                'predicted_failure_days': days_until_full,
                                'current_free_gb': current_free / (1024**3),
                                'current_used_gb': current_used / (1024**3),
                                'daily_growth_gb': daily_growth / (1024**3),
                                'risk_level': 'high' if days_until_full < 7 else 'medium',
                                'recommendation': 'Consider cleaning up disk space or expanding storage'
                            }
            
            # Store current usage
            self.disk_history.append(current_used)
            if len(self.disk_history) > 30:
                self.disk_history.pop(0)
            
            return None
            
        except Exception:
            logging.exception("Failed to predict disk space failure")
            return None
    
    def predict_memory_leak(self, process_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Predict potential memory leaks.
        
        Args:
            process_name: Optional process name to analyze
            
        Returns:
            Prediction dict or None
        """
        try:
            if process_name:
                # Analyze specific process
                for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                    try:
                        if proc.info['name'].lower() == process_name.lower():
                            mem_info = proc.info['memory_info']
                            memory_mb = mem_info.rss / (1024 * 1024)
                            
                            # Simple check: if memory usage is consistently high
                            # In production, use more sophisticated analysis
                            if memory_mb > 1000:  # More than 1GB
                                return {
                                    'process_name': process_name,
                                    'memory_mb': memory_mb,
                                    'risk_level': 'medium',
                                    'recommendation': f'Process {process_name} is using significant memory. Monitor for leaks.'
                                }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            else:
                # System-wide analysis
                memory = psutil.virtual_memory()
                if memory.percent > 85:
                    return {
                        'system_wide': True,
                        'memory_percent': memory.percent,
                        'risk_level': 'high',
                        'recommendation': 'System memory usage is high. Check for memory leaks or excessive processes.'
                    }
            
            return None
            
        except Exception:
            logging.exception("Failed to predict memory leak")
            return None


class PerformanceOptimizer:
    """
    Provides performance optimization suggestions.
    """
    
    def analyze_performance(self) -> List[Dict[str, Any]]:
        """
        Analyze system performance and provide suggestions.
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        try:
            # CPU analysis
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            if cpu_percent > 80:
                suggestions.append({
                    'category': 'cpu',
                    'severity': 'high',
                    'issue': f'High CPU usage: {cpu_percent:.1f}%',
                    'suggestion': 'Consider closing unnecessary applications or optimizing running processes',
                    'priority': 1
                })
            
            # Memory analysis
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                suggestions.append({
                    'category': 'memory',
                    'severity': 'high',
                    'issue': f'High memory usage: {memory.percent:.1f}%',
                    'suggestion': 'Consider closing memory-intensive applications or increasing RAM',
                    'priority': 1
                })
            
            # Disk analysis
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                suggestions.append({
                    'category': 'disk',
                    'severity': 'critical',
                    'issue': f'Disk space low: {disk.percent:.1f}% used',
                    'suggestion': 'Clean up disk space immediately. Delete temporary files or move data to external storage',
                    'priority': 1
                })
            
            # Process analysis
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 10 or proc_info['memory_percent'] > 5:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by resource usage
            processes.sort(key=lambda x: (x.get('cpu_percent', 0) + x.get('memory_percent', 0)), reverse=True)
            
            if processes and len(processes) > 10:
                top_process = processes[0]
                suggestions.append({
                    'category': 'processes',
                    'severity': 'medium',
                    'issue': f'Many resource-intensive processes running',
                    'suggestion': f"Top resource consumer: {top_process.get('name', 'Unknown')} ({top_process.get('cpu_percent', 0):.1f}% CPU, {top_process.get('memory_percent', 0):.1f}% Memory)",
                    'priority': 2
                })
            
            return sorted(suggestions, key=lambda x: x['priority'])
            
        except Exception:
            logging.exception("Failed to analyze performance")
            return []


class TroubleshootingGuide:
    """
    Provides automated troubleshooting guidance.
    """
    
    def __init__(self):
        """Initialize Troubleshooting Guide."""
        self.knowledge_base = {
            'high_cpu': {
                'symptoms': ['High CPU usage', 'System slowdown', 'Unresponsive applications'],
                'causes': ['Too many processes', 'Malware', 'Resource-intensive application', 'Background tasks'],
                'solutions': [
                    'Check Task Manager for high CPU processes',
                    'Close unnecessary applications',
                    'Run antivirus scan',
                    'Check for Windows updates',
                    'Restart the system'
                ]
            },
            'high_memory': {
                'symptoms': ['High memory usage', 'System slowdown', 'Applications crashing'],
                'causes': ['Memory leak', 'Too many applications', 'Insufficient RAM', 'Background services'],
                'solutions': [
                    'Close memory-intensive applications',
                    'Check for memory leaks in running processes',
                    'Restart applications',
                    'Increase virtual memory',
                    'Add more RAM'
                ]
            },
            'disk_full': {
                'symptoms': ['Disk space warnings', 'Cannot save files', 'Application errors'],
                'causes': ['Too many files', 'Large temporary files', 'System backups', 'Downloads'],
                'solutions': [
                    'Delete temporary files',
                    'Empty recycle bin',
                    'Uninstall unused programs',
                    'Move files to external storage',
                    'Use disk cleanup utility'
                ]
            },
            'network_issues': {
                'symptoms': ['Slow internet', 'Connection timeouts', 'Cannot connect'],
                'causes': ['Network congestion', 'DNS issues', 'Firewall blocking', 'Router problems'],
                'solutions': [
                    'Restart network adapter',
                    'Flush DNS cache',
                    'Check firewall settings',
                    'Restart router',
                    'Check network cables'
                ]
            },
            'service_failure': {
                'symptoms': ['Service stopped', 'Application errors', 'Feature not working'],
                'causes': ['Service crash', 'Configuration error', 'Dependency missing', 'Permission issues'],
                'solutions': [
                    'Restart the service',
                    'Check service logs',
                    'Verify service dependencies',
                    'Check service permissions',
                    'Reinstall the application'
                ]
            }
        }
    
    def get_troubleshooting_guide(self, issue_type: str) -> Optional[Dict[str, Any]]:
        """
        Get troubleshooting guide for an issue type.
        
        Args:
            issue_type: Type of issue (e.g., 'high_cpu', 'high_memory')
            
        Returns:
            Troubleshooting guide dict or None
        """
        return self.knowledge_base.get(issue_type)
    
    def diagnose_issue(self, symptoms: List[str]) -> List[Dict[str, Any]]:
        """
        Diagnose issues based on symptoms.
        
        Args:
            symptoms: List of symptom descriptions
            
        Returns:
            List of potential issues with solutions
        """
        matches = []
        
        for issue_type, guide in self.knowledge_base.items():
            score = 0
            for symptom in symptoms:
                if any(symptom.lower() in s.lower() for s in guide['symptoms']):
                    score += 1
            
            if score > 0:
                matches.append({
                    'issue_type': issue_type,
                    'confidence': score / len(guide['symptoms']),
                    'guide': guide
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches
