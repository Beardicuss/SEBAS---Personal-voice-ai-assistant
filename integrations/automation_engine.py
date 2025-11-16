# -*- coding: utf-8 -*-
"""
Automation Skill - STAGE 1 VERSION
Simplified for core functionality only
"""

from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, Any
import logging
import platform
from sebas.datetime import datetime, timedelta


class AutomationSkill(BaseSkill):
    """
    Stage 1: Basic automation - workflows, scripts, scheduled tasks
    Advanced features (email, calendar, enterprise) moved to Stage 2
    """

    def __init__(self, assistant):
        super().__init__(assistant)
        
        # Stage 1: Core automation only
        self.intents = [
            'create_workflow',
            'execute_workflow',
            'list_workflows',
            'delete_workflow',
            'execute_powershell',
            'execute_batch',
            'execute_python',
            'create_scheduled_task',
            'list_scheduled_tasks',
            'run_scheduled_task',
            'delete_scheduled_task',
        ]
        
        self.automation_engine = None
        self.script_executor = None
        self.task_scheduler = None
        self._init_managers()

    def _init_managers(self):
        """Initialize automation managers with error handling"""
        try:
            from sebas.integrations.automation_engine import AutomationEngine
            self.automation_engine = AutomationEngine()
        except ImportError:
            logging.warning("[AutomationSkill] AutomationEngine not available")
            self.automation_engine = None
        except Exception as e:
            logging.exception(f"[AutomationSkill] Failed to init AutomationEngine: {e}")
            self.automation_engine = None

        try:
            from sebas.integrations.script_executor import ScriptExecutor
            self.script_executor = ScriptExecutor()
        except ImportError:
            logging.warning("[AutomationSkill] ScriptExecutor not available")
            self.script_executor = None
        except Exception as e:
            logging.exception(f"[AutomationSkill] Failed to init ScriptExecutor: {e}")
            self.script_executor = None

        if platform.system() == 'Windows':
            try:
                from sebas.integrations.task_scheduler import TaskScheduler
                self.task_scheduler = TaskScheduler()
            except ImportError:
                logging.warning("[AutomationSkill] TaskScheduler not available")
                self.task_scheduler = None
            except Exception as e:
                logging.exception(f"[AutomationSkill] Failed to init TaskScheduler: {e}")
                self.task_scheduler = None

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def get_intents(self) -> list:
        return self.intents

    def handle(self, intent: str, slots: dict) -> bool:
        # Workflow management
        if intent == 'create_workflow':
            return self._handle_create_workflow(slots)
        elif intent == 'execute_workflow':
            return self._handle_execute_workflow(slots)
        elif intent == 'list_workflows':
            return self._handle_list_workflows()
        elif intent == 'delete_workflow':
            return self._handle_delete_workflow(slots)
        
        # Script execution
        elif intent == 'execute_powershell':
            return self._handle_execute_powershell(slots)
        elif intent == 'execute_batch':
            return self._handle_execute_batch(slots)
        elif intent == 'execute_python':
            return self._handle_execute_python(slots)
        
        # Scheduled tasks
        elif intent == 'create_scheduled_task':
            return self._handle_create_scheduled_task(slots)
        elif intent == 'list_scheduled_tasks':
            return self._handle_list_scheduled_tasks()
        elif intent == 'run_scheduled_task':
            return self._handle_run_scheduled_task(slots)
        elif intent == 'delete_scheduled_task':
            return self._handle_delete_scheduled_task(slots)
        
        return False

    # Implementation methods remain the same but without email/calendar/enterprise features
    
    def _handle_create_workflow(self, slots: dict) -> bool:
        if not self.automation_engine:
            self.assistant.speak("Automation engine not available")
            return False
        
        workflow_name = slots.get('name')
        if not workflow_name:
            self.assistant.speak("Please specify a workflow name")
            return False

        try:
            self.automation_engine.create_workflow(workflow_name)
            self.assistant.speak(f"Workflow {workflow_name} created")
            return True
        except Exception:
            logging.exception("Failed to create workflow")
            self.assistant.speak("Failed to create workflow")
            return False

    # ... rest of core automation methods (no email/calendar/enterprise code)
