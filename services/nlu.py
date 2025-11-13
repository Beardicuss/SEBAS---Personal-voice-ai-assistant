import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class IntentBase:
    name: str
    slots: Dict[str, Any]


@dataclass
class IntentWithConfidence(IntentBase):
    confidence: float = 1.0
    fuzzy_match: Optional[str] = None


class SimpleNLU:
    """
    Простой rule-based NLU:
    - parse(text) → старый интерфейс
    - get_intent_with_confidence(text) → новый интерфейс
    """

    def __init__(self):
        self.patterns: List[Tuple[str, str]] = [
            (r"set voice to (?P<profile>\w+)", "set_voice"),
            (r"adjust voice rate to (?P<rate>\d+)", "adjust_voice_rate"),
            (r"adjust voice volume to (?P<volume>\d+)%?", "adjust_voice_volume"),
            (r"adjust voice pitch to (?P<pitch>-?\d+)", "adjust_voice_pitch"),
            (r"schedule (?:an )?event (?P<title>.+) at (?P<time>.+)", "schedule_event"),
            (r"turn (?P<device>.+) (?P<state>on|off)", "smarthome_toggle"),
            (r"send email to (?P<to>.+) subject (?P<subject>.+) body (?P<body>.+)", "send_email"),
            (r"battery status", "get_battery_status"),
            (r"list printers", "list_printers"),
            (r"set default printer to (?P<printer_name>.+)", "set_default_printer"),
            (r"print test page", "print_test_page"),
            (r"list user sessions", "list_user_sessions"),
        ]

    def parse(self, text: str) -> Optional[IntentBase]:
        t = (text or "").strip().lower()
        for pat, name in self.patterns:
            m = re.search(pat, t)
            if m:
                slots = {k: (v or "").strip() for k, v in m.groupdict().items()}
                return IntentBase(name=name, slots=slots)
        return None

    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[IntentWithConfidence], List[str]]:
        """
        Совместимость с кодом main.py:
        возвращает (intent, suggestions)
        """
        base = self.parse(text)
        if not base:
            return None, []
        intent = IntentWithConfidence(
            name=base.name,
            slots=base.slots,
            confidence=1.0,
            fuzzy_match=None
        )
        return intent, []


class ContextManager:
    def __init__(self, max_history: int = 20):
        self.history: List[Dict[str, Any]] = []
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
