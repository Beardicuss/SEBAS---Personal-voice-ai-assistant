"""
Workflow Learner - Learn and execute multi-step routines
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional


class WorkflowLearner:
    """Learn and execute multi-step routines"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        logging.info("[WorkflowLearner] Initialized")
    
    def save_workflow(self, name: str, steps: List[Dict[str, Any]], 
                     triggers: Optional[List[str]] = None, 
                     context: Optional[Dict] = None):
        """Save a workflow"""
        workflows = self.mem.get("workflows", {})
        
        workflows[name] = {
            "steps": steps,
            "triggers": triggers or [],
            "context_requirements": context or {},
            "usage_count": 0,
            "last_used": None,
            "created_at": datetime.now().isoformat()
        }
        
        self.mem.update("workflows", workflows)
        logging.info(f"[WorkflowLearner] Saved workflow: {name} ({len(steps)} steps)")
    
    def get_workflow(self, name: str) -> Optional[Dict]:
        """Get a workflow by name"""
        workflows = self.mem.get("workflows", {})
        return workflows.get(name)
    
    def run_workflow(self, name: str, task_manager) -> bool:
        """Execute a workflow"""
        workflow = self.get_workflow(name)
        if not workflow:
            logging.warning(f"[WorkflowLearner] Workflow not found: {name}")
            return False
        
        # Update usage stats
        workflows = self.mem.get("workflows", {})
        workflows[name]["usage_count"] += 1
        workflows[name]["last_used"] = datetime.now().isoformat()
        self.mem.update("workflows", workflows)
        
        # Execute steps
        try:
            return task_manager.run_steps(workflow["steps"])
        except Exception as e:
            logging.error(f"[WorkflowLearner] Failed to run workflow {name}: {e}")
            return False
    
    def list_workflows(self) -> List[str]:
        """List all workflow names"""
        workflows = self.mem.get("workflows", {})
        return list(workflows.keys())
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow"""
        workflows = self.mem.get("workflows", {})
        if name in workflows:
            del workflows[name]
            self.mem.update("workflows", workflows)
            logging.info(f"[WorkflowLearner] Deleted workflow: {name}")
            return True
        return False
