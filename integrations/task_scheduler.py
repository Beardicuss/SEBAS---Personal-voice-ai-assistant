# -*- coding: utf-8 -*-
"""
Task Scheduler
Phase 5.1: Scheduled task creation and management
"""

import logging
import subprocess
import platform
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum


class TaskTriggerType(Enum):
    """Task trigger types"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_LOGON = "on_logon"
    ON_START = "on_start"
    ON_IDLE = "on_idle"
    ON_EVENT = "on_event"


class TaskScheduler:
    """
    Manages Windows scheduled tasks.
    """
    
    def __init__(self):
        """Initialize Task Scheduler."""
        if platform.system() != 'Windows':
            raise RuntimeError("TaskScheduler only works on Windows")
    
    def create_task(self, task_name: str, command: str, arguments: Optional[str] = None,
                   trigger_type: TaskTriggerType = TaskTriggerType.DAILY,
                   start_time: Optional[str] = None,
                   run_as_user: Optional[str] = None,
                   enabled: bool = True) -> Tuple[bool, str]:
        """
        Create a scheduled task.
        
        Args:
            task_name: Name of the task
            command: Command or program to run
            arguments: Optional command arguments
            trigger_type: Type of trigger
            start_time: Start time (HH:mm format for daily/weekly)
            run_as_user: User to run task as (defaults to SYSTEM)
            enabled: Whether task is enabled
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use schtasks command
            cmd = ["schtasks", "/Create", "/TN", task_name, "/TR", command]
            
            if arguments:
                cmd.extend(["/TR", f"{command} {arguments}"])
            
            # Set trigger
            if trigger_type == TaskTriggerType.DAILY:
                cmd.extend(["/SC", "DAILY"])
                if start_time:
                    cmd.extend(["/ST", start_time])
            elif trigger_type == TaskTriggerType.WEEKLY:
                cmd.extend(["/SC", "WEEKLY"])
                if start_time:
                    cmd.extend(["/ST", start_time])
            elif trigger_type == TaskTriggerType.MONTHLY:
                cmd.extend(["/SC", "MONTHLY"])
                if start_time:
                    cmd.extend(["/ST", start_time])
            elif trigger_type == TaskTriggerType.ONCE:
                cmd.extend(["/SC", "ONCE"])
                if start_time:
                    cmd.extend(["/ST", start_time])
            elif trigger_type == TaskTriggerType.ON_LOGON:
                cmd.extend(["/SC", "ONLOGON"])
            elif trigger_type == TaskTriggerType.ON_START:
                cmd.extend(["/SC", "ONSTART"])
            elif trigger_type == TaskTriggerType.ON_IDLE:
                cmd.extend(["/SC", "ONIDLE"])
            
            # Set user
            if run_as_user:
                cmd.extend(["/RU", run_as_user])
            else:
                cmd.extend(["/RU", "SYSTEM"])
            
            # Set enabled/disabled
            if not enabled:
                cmd.extend(["/DISABLE"])
            
            # Run with highest privileges
            cmd.extend(["/F"])  # Force creation
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, f"Task {task_name} created successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to create task {task_name}")
            return False, "Failed to create task"
    
    def delete_task(self, task_name: str) -> Tuple[bool, str]:
        """
        Delete a scheduled task.
        
        Args:
            task_name: Name of the task to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", task_name, "/F"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Task {task_name} deleted successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to delete task {task_name}")
            return False, "Failed to delete task"
    
    def list_tasks(self, task_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List scheduled tasks.
        
        Args:
            task_name: Optional task name filter
            
        Returns:
            List of task information dicts
        """
        try:
            cmd = ["schtasks", "/Query", "/FO", "LIST", "/V"]
            if task_name:
                cmd.extend(["/TN", task_name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return []
            
            tasks = []
            current_task = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_task:
                        tasks.append(current_task)
                        current_task = {}
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    current_task[key] = value
            
            if current_task:
                tasks.append(current_task)
            
            return tasks
            
        except Exception:
            logging.exception("Failed to list tasks")
            return []
    
    def run_task(self, task_name: str) -> Tuple[bool, str]:
        """
        Run a scheduled task immediately.
        
        Args:
            task_name: Name of the task to run
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["schtasks", "/Run", "/TN", task_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Task {task_name} started"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to run task {task_name}")
            return False, "Failed to run task"
    
    def enable_task(self, task_name: str) -> Tuple[bool, str]:
        """Enable a scheduled task."""
        try:
            result = subprocess.run(
                ["schtasks", "/Change", "/TN", task_name, "/ENABLE"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Task {task_name} enabled"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to enable task {task_name}")
            return False, "Failed to enable task"
    
    def disable_task(self, task_name: str) -> Tuple[bool, str]:
        """Disable a scheduled task."""
        try:
            result = subprocess.run(
                ["schtasks", "/Change", "/TN", task_name, "/DISABLE"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Task {task_name} disabled"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to disable task {task_name}")
            return False, "Failed to disable task"

