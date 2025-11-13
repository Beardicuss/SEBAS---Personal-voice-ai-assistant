import logging
from typing import Optional, Tuple, Dict, Any

from sebas.nlp.intent_executor import IntentExecutor
from sebas.permissions.permission_manager import PermissionManager


class CommandRouter:
    """Central command router: NLU → permission check → executor."""

    def __init__(self, nlu, context, skill_registry, permission_manager: PermissionManager, speak, listen):
        self.nlu = nlu
        self.context = context
        self.skill_registry = skill_registry
        self.permission_manager = permission_manager
        self.speak = speak
        self.listen = listen
        self.executor = IntentExecutor(skill_registry, speak)

    def process(self, raw_command: str):
        command = (raw_command or "").strip()
        if not command:
            logging.warning("Empty command received")
            return

        logging.info(f"Router received command: {command}")

        # 1. Run NLU
        intent, suggestions = self._run_nlu(command)

        if not intent:
            return self._fallback(command, suggestions)

        # 2. Save to context
        try:
            self.context.add({
                "type": "intent",
                "name": intent.name,
                "slots": intent.slots,
                "confidence": intent.confidence
            })
        except Exception:
            pass

        # 3. Low confidence message
        self._check_confidence(intent)

        # 4. Check permissions
        if not self.permission_manager.has_permission(intent.name):
            logging.warning(f"Permission denied for intent: {intent.name}")
            self.speak("You do not have permission for that command.")
            return

        # 5. Execute intent
        handled = self.executor.execute(intent)
        if handled:
            return

        # 6. Fallback to open <app>
        if self._try_open_app(command):
            return

        # 7. No idea what user said
        return self._fallback(command, suggestions)

    # ----------------------- helpers -----------------------

    def _run_nlu(self, command):
        """Unified NLU handling."""
        intent, suggestions = None, []

        try:
            if hasattr(self.nlu, "get_intent_with_confidence"):
                intent, suggestions = self.nlu.get_intent_with_confidence(command)
            elif hasattr(self.nlu, "parse"):
                parsed = self.nlu.parse(command)
                if parsed:
                    from sebas.nlp.nlu import IntentWithConfidence
                    intent = IntentWithConfidence(parsed.name, parsed.slots, 1.0)
        except Exception as e:
            logging.error(f"NLU error: {e}", exc_info=True)

        return intent, suggestions

    def _check_confidence(self, intent):
        try:
            if intent.confidence < 0.8:
                msg = f"I detected '{intent.name}' with {intent.confidence:.0%} confidence."
                if intent.fuzzy_match:
                    msg += f" Did you mean '{intent.fuzzy_match}'?"
                self.speak(msg)
        except Exception:
            pass

    def _try_open_app(self, command):
        import re
        m = re.search(r"(open|launch)\s+(.+)", command.lower())
        if m:
            app_name = m.group(2).strip('" ')
            from sebas.skills.app_skill import open_application
            open_application(app_name)
            return True
        return False

    def _fallback(self, command, suggestions):
        if suggestions:
            self.speak("Did you mean: " + ", ".join(suggestions))
            return

        self.speak("I did not understand, sir. Try 'help'.")
        logging.warning(f"Unhandled command: {command}")