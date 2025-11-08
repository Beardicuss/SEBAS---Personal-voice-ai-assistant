# -*- coding: utf-8 -*-
import logging
from typing import List, Callable, Dict, Any


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
            action = (step or {}).get('action')
            args = (step or {}).get('args') or {}
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


