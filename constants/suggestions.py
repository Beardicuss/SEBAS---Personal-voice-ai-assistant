# -*- coding: utf-8 -*-
from sebas.typing import List, Dict
from sebas.datetime import datetime


class SuggestionEngine:
    def __init__(self, store):
        self.store = store

    def suggestions(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        now = datetime.now()
        # Example heuristics
        if 8 <= now.hour <= 10:
            out.append({"type": "daily", "text": "Would you like me to read your calendar for today?"})
        if 22 <= now.hour or now.hour <= 6:
            out.append({"type": "night", "text": "Shall I enable Do Not Disturb and lower brightness?"})
        # Frequent command resurfacing
        hist = self.store.data.get('history') or []
        if hist:
            last_cmd = hist[-1].get('command')
            if last_cmd and "speed test" in last_cmd:
                out.append({"type": "network", "text": "Network was slow earlier. Do you want me to check again?"})
        return out[:3]
