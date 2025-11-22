# -*- coding: utf-8 -*-
import logging
from typing import List, Callable, Dict, Any, Optional


class TaskManager:
    """Executes multi-step tasks with simple sequencing and error isolation."""

    def __init__(self):
        self._registry: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]):
        self._registry[name] = func

    def run_steps(self, steps: List[Dict[str, Any]]):
        """Each step: { 'action': str, 'args': {...} }"""
        results = []

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                logging.error(f"Invalid step type at index {i}: {type(step)}")
                results.append({"step": i, "ok": False, "error": "invalid_step"})
                continue

            # Be explicit with type hints to silence Pylance
            action: Optional[str] = step.get("action")
            args: Dict[str, Any] = step.get("args", {})

            if action is None or not isinstance(action, str):
                logging.error(f"Invalid or missing action in step {i}: {action}")
                results.append({"step": i, "ok": False, "error": "invalid_action"})
                continue

            fn = self._registry.get(action)
            if not fn:
                logging.error(f"Unknown action in step {i}: {action}")
                results.append({"step": i, "ok": False, "error": "unknown_action"})
                continue

            try:
                out = fn(**args)
                results.append({"step": i, "ok": True, "result": out})
            except Exception:
                logging.exception(f"Task step failed: {action}")
                results.append({"step": i, "ok": False, "error": "exception"})

        return results