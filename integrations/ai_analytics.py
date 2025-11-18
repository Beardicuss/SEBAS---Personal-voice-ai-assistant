# -*- coding: utf-8 -*-
"""
AI Analytics Integration - CORRECTED VERSION
Replace sebas/integrations/ai_analytics.py with this file
"""

import psutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque


class AnomalyDetector:
    """
    Detects system anomalies using statistical methods.
    No ML dependencies required - uses heuristics and thresholds.
    """
    
    def __init__(self):
        self.baseline_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.thresholds = {
            'cpu_critical': 90,
            'cpu_high': 75,
            'memory_critical': 90,
            'memory_high': 80,
            'disk_critical': 95,
            'disk_high': 85,
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids()),
                'network_connections': len(psutil.net_connections()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Failed to collect metrics: {e}")
            return {}
    
    def detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in system metrics."""
        anomalies = []
        
        # Store metrics for baseline
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                self.baseline_metrics[key].append(value)
        
        # CPU anomalies
        cpu = metrics.get('cpu_percent', 0)
        if cpu > self.thresholds['cpu_critical']:
            anomalies.append({
                'type': 'cpu',
                'severity': 'critical',
                'value': cpu,
                'message': f'CPU usage critical: {cpu}%'
            })
        elif cpu > self.thresholds['cpu_high']:
            anomalies.append({
                'type': 'cpu',
                'severity': 'high',
                'value': cpu,
                'message': f'CPU usage high: {cpu}%'
            })
        
        # Memory anomalies
        memory = metrics.get('memory_percent', 0)
        if memory > self.thresholds['memory_critical']:
            anomalies.append({
                'type': 'memory',
                'severity': 'critical',
                'value': memory,
                'message': f'Memory usage critical: {memory}%'
            })
        elif memory > self.thresholds['memory_high']:
            anomalies.append({
                'type': 'memory',
                'severity': 'high',
                'value': memory,
                'message': f'Memory usage high: {memory}%'
            })
        
        # Disk anomalies
        disk = metrics.get('disk_percent', 0)
        if disk > self.thresholds['disk_critical']:
            anomalies.append({
                'type': 'disk',
                'severity': 'critical',
                'value': disk,
                'message': f'Disk space critical: {disk}%'
            })
        elif disk > self.thresholds['disk_high']:
            anomalies.append({
                'type': 'disk',
                'severity': 'high',
                'value': disk,
                'message': f'Disk space high: {disk}%'
            })
        
        # Process count anomaly
        process_count = metrics.get('process_count', 0)
        if len(self.baseline_metrics['process_count']) > 10:
            avg_processes = sum(self.baseline_metrics['process_count']) / len(self.baseline_metrics['process_count'])
            if process_count > avg_processes * 1.5:
                anomalies.append({
                    'type': 'processes',
                    'severity': 'medium',
                    'value': process_count,
                    'message': f'Unusual process count: {process_count} (avg: {avg_processes:.0f})'
                })
        
        return anomalies


class PredictiveAnalyzer:
    """
    Provides predictive analytics for system resources.
    Uses trend analysis and linear extrapolation.
    """
    
    def __init__(self):
        self.history: Dict[str, List[tuple]] = defaultdict(list)  # (timestamp, value)
    
    def predict_disk_space_failure(self, path: str = '/', days: int = 30) -> Optional[Dict[str, Any]]:
        """Predict when disk space will run out."""
        try:
            disk = psutil.disk_usage(path)
            current_usage = disk.percent
            
            # Store current measurement
            self.history['disk_usage'].append((datetime.now(), current_usage))
            
            # Need at least 10 data points for prediction
            if len(self.history['disk_usage']) < 10:
                return None
            
            # Calculate trend (simple linear regression)
            recent = self.history['disk_usage'][-30:]  # Last 30 measurements
            if len(recent) < 2:
                return None
            
            # Calculate average daily increase
            time_diff = (recent[-1][0] - recent[0][0]).total_seconds() / 86400  # days
            usage_diff = recent[-1][1] - recent[0][1]
            
            if time_diff == 0:
                return None
            
            daily_increase = usage_diff / time_diff
            
            # Predict days until full (95% threshold)
            space_remaining = 95 - current_usage
            if daily_increase <= 0:
                return None  # Usage is decreasing
            
            days_until_full = space_remaining / daily_increase
            
            # Determine risk level
            if days_until_full < 7:
                risk = 'critical'
            elif days_until_full < 30:
                risk = 'high'
            elif days_until_full < 90:
                risk = 'medium'
            else:
                risk = 'low'
            
            return {
                'predicted_failure_days': days_until_full,
                'current_usage': current_usage,
                'daily_increase': daily_increase,
                'risk_level': risk
            }
            
        except Exception as e:
            logging.error(f"Failed to predict disk failure: {e}")
            return None
    
    def predict_memory_leak(self, process_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Predict potential memory leaks in processes."""
        try:
            # Get all processes or specific process
            if process_name:
                processes = [p for p in psutil.process_iter(['name', 'memory_info']) 
                           if p.info['name'] == process_name]
            else:
                processes = list(psutil.process_iter(['name', 'memory_info']))[:10]  # Top 10
            
            leaky_processes = []
            
            for proc in processes:
                try:
                    proc_name = proc.info['name']
                    memory = proc.info['memory_info'].rss / 1024 / 1024  # MB
                    
                    # Store measurement
                    key = f'proc_{proc.pid}'
                    self.history[key].append((datetime.now(), memory))
                    
                    # Need at least 5 measurements
                    if len(self.history[key]) < 5:
                        continue
                    
                    # Check for consistent growth
                    recent = self.history[key][-10:]
                    if len(recent) < 2:
                        continue
                    
                    # Calculate growth rate
                    growth = recent[-1][1] - recent[0][1]
                    time_diff = (recent[-1][0] - recent[0][0]).total_seconds() / 60  # minutes
                    
                    if time_diff == 0:
                        continue
                    
                    growth_rate = growth / time_diff  # MB per minute
                    
                    # Detect leak (growing > 1MB/min consistently)
                    if growth_rate > 1.0:
                        leaky_processes.append({
                            'name': proc_name,
                            'pid': proc.pid,
                            'memory_mb': memory,
                            'growth_rate': growth_rate
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if leaky_processes:
                # Return most leaky process
                top_leak = max(leaky_processes, key=lambda x: x['growth_rate'])
                return {
                    'risk_level': 'high' if top_leak['growth_rate'] > 5 else 'medium',
                    'process': top_leak,
                    'recommendation': f"Monitor {top_leak['name']} - growing {top_leak['growth_rate']:.1f}MB/min"
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to predict memory leak: {e}")
            return None


class PerformanceOptimizer:
    """
    Analyzes system performance and provides optimization suggestions.
    """
    
    def analyze_performance(self) -> List[Dict[str, Any]]:
        """Analyze system and provide performance suggestions."""
        suggestions = []
        
        try:
            # CPU analysis
            cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
            if cpu_percent > 80:
                suggestions.append({
                    'category': 'cpu',
                    'severity': 'high',
                    'suggestion': 'CPU usage is high. Consider closing unnecessary applications.',
                    'metric': cpu_percent
                })
            
            # Memory analysis
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                suggestions.append({
                    'category': 'memory',
                    'severity': 'high',
                    'suggestion': 'Memory usage is high. Consider closing memory-intensive applications.',
                    'metric': memory.percent
                })
            
            # Disk analysis
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                suggestions.append({
                    'category': 'disk',
                    'severity': 'critical',
                    'suggestion': 'Disk space is critically low. Run disk cleanup or remove unnecessary files.',
                    'metric': disk.percent
                })
            elif disk.percent > 80:
                suggestions.append({
                    'category': 'disk',
                    'severity': 'medium',
                    'suggestion': 'Disk space is running low. Consider cleaning up temporary files.',
                    'metric': disk.percent
                })
            
            # Process count
            process_count = len(psutil.pids())
            if process_count > 200:
                suggestions.append({
                    'category': 'processes',
                    'severity': 'medium',
                    'suggestion': f'High number of processes running ({process_count}). Consider closing unused applications.',
                    'metric': process_count
                })
            
            # Network connections
            try:
                connections = len(psutil.net_connections())
                if connections > 500:
                    suggestions.append({
                        'category': 'network',
                        'severity': 'medium',
                        'suggestion': f'High number of network connections ({connections}). Check for unnecessary network activity.',
                        'metric': connections
                    })
            except psutil.AccessDenied:
                pass  # Need elevated privileges
            
        except Exception as e:
            logging.error(f"Failed to analyze performance: {e}")
        
        return suggestions


class TroubleshootingGuide:
    """
    Provides troubleshooting guides and diagnostic advice.
    """
    
    def __init__(self):
        self.guides = {
            'high_cpu': {
                'symptoms': ['high cpu', 'slow performance', 'fan noise'],
                'solutions': [
                    'Open Task Manager to identify CPU-intensive processes',
                    'Close unnecessary applications',
                    'Check for malware or unwanted software',
                    'Update device drivers',
                    'Reduce startup programs'
                ]
            },
            'high_memory': {
                'symptoms': ['high memory', 'system slowdown', 'out of memory'],
                'solutions': [
                    'Close unused browser tabs',
                    'Restart memory-intensive applications',
                    'Increase virtual memory/page file size',
                    'Add more RAM if consistently high',
                    'Check for memory leaks in applications'
                ]
            },
            'disk_full': {
                'symptoms': ['disk full', 'low disk space', 'storage warning'],
                'solutions': [
                    'Run Disk Cleanup utility',
                    'Delete temporary files',
                    'Uninstall unused applications',
                    'Move large files to external storage',
                    'Empty Recycle Bin'
                ]
            },
            'network_slow': {
                'symptoms': ['slow internet', 'network issues', 'connection problems'],
                'solutions': [
                    'Restart router/modem',
                    'Check network cable connections',
                    'Run network troubleshooter',
                    'Update network drivers',
                    'Check for bandwidth-heavy applications'
                ]
            }
        }
    
    def get_troubleshooting_guide(self, issue_type: str) -> Optional[Dict[str, Any]]:
        """Get troubleshooting guide for an issue."""
        return self.guides.get(issue_type)
    
    def diagnose_issue(self, symptoms: List[str]) -> List[Dict[str, Any]]:
        """Diagnose issue based on symptoms."""
        matches = []
        
        for issue_type, guide in self.guides.items():
            # Calculate match score
            symptom_matches = sum(1 for symptom in symptoms 
                                if any(s in symptom.lower() for s in guide['symptoms']))
            
            if symptom_matches > 0:
                confidence = symptom_matches / len(guide['symptoms'])
                matches.append({
                    'issue_type': issue_type,
                    'confidence': confidence,
                    'solutions': guide['solutions']
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches


# Backward compatibility - export all classes
__all__ = [
    'AnomalyDetector',
    'PredictiveAnalyzer', 
    'PerformanceOptimizer',
    'TroubleshootingGuide'
]