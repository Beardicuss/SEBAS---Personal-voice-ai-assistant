# -*- coding: utf-8 -*-
"""
Automation Engine
Phase 5.1: Workflow Automation Framework
"""

import logging
import json
import os
from sebas.typing import Dict, List, Optional, Any, Callable
from sebas.datetime import datetime, timedelta
from sebas.enum import Enum
import threading
import time


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep:
    """
    Represents a single step in a workflow.
    """
    
    def __init__(self, name: str, action: str, parameters: Optional[Dict] = None,
                 condition: Optional[str] = None, on_success: Optional[str] = None,
                 on_failure: Optional[str] = None):
        """
        Initialize workflow step.
        
        Args:
            name: Step name
            action: Action to execute
            parameters: Action parameters
            condition: Optional condition to check before execution
            on_success: Optional next step on success
            on_failure: Optional next step on failure
        """
        self.name = name
        self.action = action
        self.parameters = parameters or {}
        self.condition = condition
        self.on_success = on_success
        self.on_failure = on_failure
        self.status = WorkflowStatus.PENDING
        self.result = None
        self.error = None
        self.executed_at = None


class Workflow:
    """
    Represents a workflow with multiple steps.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
        """
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.variables: Dict[str, Any] = {}
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
    
    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps.append(step)
    
    def set_variable(self, name: str, value: Any):
        """Set a workflow variable."""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self.variables.get(name, default)


class AutomationEngine:
    """
    Automation engine for workflow execution and management.
    """
    
    def __init__(self):
        """Initialize Automation Engine."""
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[Dict] = []
        self.action_handlers: Dict[str, Callable] = {}
        self.running_workflows: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        
        # Register default action handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default action handlers."""
        # Placeholder - handlers will be registered by the main application
        pass
    
    def register_action_handler(self, action_name: str, handler: Callable):
        """
        Register an action handler.
        
        Args:
            action_name: Name of the action
            handler: Handler function that takes (parameters, workflow) and returns (success, result)
        """
        self.action_handlers[action_name] = handler
    
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            
        Returns:
            Created workflow
        """
        workflow = Workflow(name, description)
        with self.lock:
            self.workflows[name] = workflow
        return workflow
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        with self.lock:
            if name in self.workflows:
                del self.workflows[name]
                return True
            return False
    
    def list_workflows(self) -> List[str]:
        """List all workflow names."""
        return list(self.workflows.keys())
    
    def execute_workflow(self, workflow_name: str, variables: Optional[Dict] = None,
                        async_execution: bool = False) -> Optional[Workflow]:
        """
        Execute a workflow.
        
        Args:
            workflow_name: Name of workflow to execute
            variables: Optional variables to set before execution
            async_execution: If True, execute in background thread
            
        Returns:
            Workflow instance (if sync) or None (if async)
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            logging.error(f"Workflow {workflow_name} not found")
            return None
        
        # Clone workflow for execution
        execution_workflow = Workflow(workflow.name, workflow.description)
        execution_workflow.steps = [step for step in workflow.steps]
        execution_workflow.variables = workflow.variables.copy()
        
        if variables:
            execution_workflow.variables.update(variables)
        
        if async_execution:
            thread = threading.Thread(
                target=self._execute_workflow_sync,
                args=(execution_workflow,),
                daemon=True
            )
            with self.lock:
                self.running_workflows[workflow_name] = thread
            thread.start()
            return None
        else:
            return self._execute_workflow_sync(execution_workflow)
    
    def _execute_workflow_sync(self, workflow: Workflow) -> Workflow:
        """Execute workflow synchronously."""
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        
        try:
            current_step_index = 0
            
            while current_step_index < len(workflow.steps):
                step = workflow.steps[current_step_index]
                
                # Check condition if present
                if step.condition and not self._evaluate_condition(step.condition, workflow):
                    logging.info(f"Skipping step {step.name} due to condition")
                    current_step_index += 1
                    continue
                
                # Execute step
                step.status = WorkflowStatus.RUNNING
                step.executed_at = datetime.now()
                
                success, result = self._execute_step(step, workflow)
                
                if success:
                    step.status = WorkflowStatus.COMPLETED
                    step.result = result
                    
                    # Determine next step
                    if step.on_success:
                        next_index = self._find_step_index(workflow, step.on_success)
                        if next_index is not None:
                            current_step_index = next_index
                        else:
                            current_step_index += 1
                    else:
                        current_step_index += 1
                else:
                    step.status = WorkflowStatus.FAILED
                    step.error = result
                    
                    # Determine next step on failure
                    if step.on_failure:
                        next_index = self._find_step_index(workflow, step.on_failure)
                        if next_index is not None:
                            current_step_index = next_index
                        else:
                            workflow.status = WorkflowStatus.FAILED
                            workflow.error = f"Step {step.name} failed: {result}"
                            break
                    else:
                        workflow.status = WorkflowStatus.FAILED
                        workflow.error = f"Step {step.name} failed: {result}"
                        break
            
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
            
        except Exception as e:
            logging.exception(f"Error executing workflow {workflow.name}")
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
        
        # Record execution history
        with self.lock:
            self.execution_history.append({
                'workflow_name': workflow.name,
                'status': workflow.status.value,
                'started_at': workflow.started_at.isoformat() if workflow.started_at else None,
                'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None,
                'error': workflow.error
            })
        
        return workflow
    
    def _execute_step(self, step: WorkflowStep, workflow: Workflow) -> tuple[bool, Any]:
        """Execute a workflow step."""
        handler = self.action_handlers.get(step.action)
        if not handler:
            return False, f"Action handler not found: {step.action}"
        
        try:
            # Substitute variables in parameters
            parameters = self._substitute_variables(step.parameters, workflow)
            return handler(parameters, workflow)
        except Exception as e:
            logging.exception(f"Error executing step {step.name}")
            return False, str(e)
    
    def _substitute_variables(self, parameters: Dict, workflow: Workflow) -> Dict:
        """Substitute workflow variables in parameters."""
        result = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                result[key] = workflow.get_variable(var_name, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_variables(value, workflow)
            elif isinstance(value, list):
                result[key] = [
                    self._substitute_variables({'item': item}, workflow)['item']
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    def _evaluate_condition(self, condition: str, workflow: Workflow) -> bool:
        """Evaluate a condition expression."""
        try:
            # Simple condition evaluation
            # Support for ${variable} substitution and basic comparisons
            condition = condition.strip()
            
            # Replace variables
            for var_name, var_value in workflow.variables.items():
                condition = condition.replace(f'${{{var_name}}}', str(var_value))
            
            # Evaluate simple expressions
            # This is a simplified evaluator - in production, use a proper expression parser
            if '==' in condition:
                parts = condition.split('==')
                if len(parts) == 2:
                    return parts[0].strip() == parts[1].strip()
            elif '!=' in condition:
                parts = condition.split('!=')
                if len(parts) == 2:
                    return parts[0].strip() != parts[1].strip()
            elif '>' in condition:
                parts = condition.split('>')
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) > float(parts[1].strip())
                    except ValueError:
                        pass
            elif '<' in condition:
                parts = condition.split('<')
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) < float(parts[1].strip())
                    except ValueError:
                        pass
            
            # Default: treat as boolean
            return condition.lower() in ('true', '1', 'yes')
            
        except Exception:
            logging.exception(f"Error evaluating condition: {condition}")
            return False
    
    def _find_step_index(self, workflow: Workflow, step_name: str) -> Optional[int]:
        """Find step index by name."""
        for i, step in enumerate(workflow.steps):
            if step.name == step_name:
                return i
        return None
    
    def get_execution_history(self, workflow_name: Optional[str] = None,
                             limit: int = 100) -> List[Dict]:
        """Get execution history."""
        with self.lock:
            history = self.execution_history.copy()
        
        if workflow_name:
            history = [h for h in history if h.get('workflow_name') == workflow_name]
        
        return history[-limit:]
    
    def save_workflow(self, workflow: Workflow, file_path: str):
        """Save workflow to file."""
        try:
            workflow_data = {
                'name': workflow.name,
                'description': workflow.description,
                'variables': workflow.variables,
                'steps': [
                    {
                        'name': step.name,
                        'action': step.action,
                        'parameters': step.parameters,
                        'condition': step.condition,
                        'on_success': step.on_success,
                        'on_failure': step.on_failure
                    }
                    for step in workflow.steps
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2)
                
        except Exception:
            logging.exception(f"Failed to save workflow to {file_path}")
    
    def load_workflow(self, file_path: str) -> Optional[Workflow]:
        """Load workflow from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            workflow = Workflow(workflow_data['name'], workflow_data.get('description', ''))
            workflow.variables = workflow_data.get('variables', {})
            
            for step_data in workflow_data.get('steps', []):
                step = WorkflowStep(
                    name=step_data['name'],
                    action=step_data['action'],
                    parameters=step_data.get('parameters', {}),
                    condition=step_data.get('condition'),
                    on_success=step_data.get('on_success'),
                    on_failure=step_data.get('on_failure')
                )
                workflow.add_step(step)
            
            with self.lock:
                self.workflows[workflow.name] = workflow
            
            return workflow
            
        except Exception:
            logging.exception(f"Failed to load workflow from {file_path}")
            return None