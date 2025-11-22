import re
import os
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

# Safe YAML import
try:
    import yaml
    yaml_safe_load = yaml.safe_load
except ImportError:
    yaml_safe_load = None

# Import simple NLU fallback
try:
    from sebas.services.simple_nlu import SimpleNLU, IntentWithConfidence
except ImportError:
    from sebas.services import SimpleNLU, IntentWithConfidence

# Optional advanced enhancer (won't break if missing)
try:
    from sebas.integrations.nlu_enhancer import ContextManager, LearningSystem, IntentResolver
    ContextManager = ContextManager
    LearningSystem = LearningSystem
    IntentResolver = IntentResolver
except Exception:
    ContextManager = LearningSystem = IntentResolver = None


@dataclass
class EnhancedIntent(IntentWithConfidence):
    source: str = "unknown"


class EnhancedNLU:
    def __init__(self):
        self.simple_nlu = SimpleNLU()
        self.skill_patterns: List[Tuple[str, str, float]] = []
        self.context = ContextManager() if ContextManager else None
        self.learning = LearningSystem() if LearningSystem else None
        self.resolver = IntentResolver() if IntentResolver else None
        self._load_skill_intents()

    def _load_skill_intents(self):
        if yaml_safe_load is None:
            print("[EnhancedNLU] PyYAML not installed - skill intents disabled")
            return

        skills_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../skills"))
        if not os.path.isdir(skills_path):
            print(f"[EnhancedNLU] Skills folder not found: {skills_path}")
            return

        print(f"[EnhancedNLU] Scanning for intent.yaml files in {skills_path}")
        loaded = 0
        for skill_name in os.listdir(skills_path):
            intent_file = os.path.join(skills_path, skill_name, "intent.yaml")
            if not os.path.isfile(intent_file):
                continue
            try:
                with open(intent_file, "r", encoding="utf-8") as f:
                    data = yaml_safe_load(f) or {}
                    intent_name = data.get("intent", skill_name)
                    patterns = data.get("patterns", [])
                    if isinstance(patterns, str):
                        patterns = [{"match": patterns}]

                    for pat in patterns:
                        if isinstance(pat, str):
                            regex = pat
                            conf = 0.95
                        else:
                            regex = pat.get("match", ".*")
                            conf = float(pat.get("confidence", 0.95))
                        self.skill_patterns.append((regex, intent_name, conf))
                        loaded += 1
            except Exception as e:
                print(f"[EnhancedNLU] Failed to load {skill_name}/intent.yaml → {e}")

        print(f"[EnhancedNLU] Successfully loaded {loaded} skill-specific intent patterns")

    def get_intent_with_confidence(self, text: str) -> Tuple[Optional[EnhancedIntent], List[str]]:
        if not text or not text.strip():
            return None, []

        text_lower = text.lower().strip()

        # 1. Skill-specific patterns first
        for pattern, intent_name, confidence in self.skill_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return EnhancedIntent(
                    name=intent_name,
                    slots={},
                    confidence=confidence,
                    source="skill_yaml"
                ), []

        # 2. Fallback to SimpleNLU
        base_intent, suggestions = self.simple_nlu.get_intent_with_confidence(text)
        if base_intent:
            return EnhancedIntent(
                name=base_intent.name,
                slots=base_intent.slots,
                confidence=base_intent.confidence,
                fuzzy_match=base_intent.fuzzy_match,
                source="simple"
            ), suggestions

        return None, []