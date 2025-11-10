# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Intent:
    name: str
    slots: Dict[str, Any]


class SimpleNLU:
    """Lightweight pattern/rule-based NLU for local use.
    Provides: intent classification + slot extraction.
    """

    def __init__(self):
        self.patterns = [
            (r"set voice to (?P<profile>\w+)", "set_voice"),
            (r"adjust voice rate to (?P<rate>\d+)", "adjust_voice_rate"),
            (r"adjust voice volume to (?P<volume>\d+)%?", "adjust_voice_volume"),
            (r"adjust voice pitch to (?P<pitch>-?\d+)", "adjust_voice_pitch"),
            (r"schedule (?:an )?event (?P<title>.+) at (?P<time>.+)", "schedule_event"),
            (r"turn (?P<device>.+) (?P<state>on|off)", "smarthome_toggle"),
            (r"send email to (?P<to>.+) subject (?P<subject>.+) body (?P<body>.+)", "send_email"),
            # Phase 4.2: Compliance intents
            (r"log activity for user (?P<user>\w+) action (?P<action>.+) resource (?P<resource>.+)", "log_activity"),
            (r"get activity log(?: for user (?P<user>\w+))?(?: action (?P<action>.+))?(?: last (?P<days>\d+) days)?", "get_activity_log"),
            (r"get audit events(?: type (?P<event_type>\d+))?(?: category (?P<category>\w+))?(?: severity (?P<severity>\w+))?(?: last (?P<days>\d+) days)?", "get_audit_events"),
            (r"generate compliance report(?: last (?P<days>\d+) days)?", "generate_compliance_report"),
            (r"verify security policy", "verify_security_policy"),
        ]

    def parse(self, text: str) -> Optional[Intent]:
        t = (text or "").strip().lower()
        for pat, name in self.patterns:
            m = re.search(pat, t)
            if m:
                slots = {k: (v or "").strip() for k, v in m.groupdict().items()}
                return Intent(name=name, slots=slots)
        return None


class ContextManager:
    def __init__(self, max_history: int = 20):
        self.history = []
        self.max_history = max_history

    def add(self, entry: Dict[str, Any]):
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def last_intent(self) -> Optional[Dict[str, Any]]:
        for item in reversed(self.history):
            if item.get("type") == "intent":
                return item
        return None