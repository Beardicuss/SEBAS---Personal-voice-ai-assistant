import logging
from sebas.permissions.permission_manager import PermissionManager


class IntentRouter:
    """
    Главная логика:
    intent → permission → skill → legacy → fallback
    """

    def __init__(self, sebas_instance):
        self.sebas = sebas_instance
        self.permissions = PermissionManager()

    def route(self, intent, suggestions):
        """
        Основной метод, вызывается из parse_and_execute.
        """

        # === 1. Permission check ===
        role_ok = self.permissions.has_permission(self.sebas, intent.name)
        if not role_ok:
            logging.warning(f"Permission denied: {intent.name}")
            self.sebas.speak("Permission denied.")
            return True  # обработано, но запрещено

        # === 2. Skills (новая система) ===
        try:
            handled = self.sebas.skill_registry.handle_intent(intent.name, intent.slots)
            if handled:
                logging.info(f"Skill handled: {intent.name}")
                return True
        except Exception:
            logging.exception("Skill handler failed")

        # === 3. Legacy handlers ===
        try:
            handled = self.sebas._handle_intent(intent.name, intent.slots)
            if handled:
                return True
        except Exception:
            pass

        # === 4. Fallback to learned commands ===
        handled = self.sebas._try_handle_learned_command(intent.name)
        if handled:
            return True

        # === 5. Fallback to fallback_skills ===
        handled = self.sebas._handle_fallback_with_skills(intent.name)
        if handled:
            return True

        # === 6. If nothing was handled ===
        if suggestions:
            self.sebas.speak(
                "I did not understand. Maybe you meant: " + ", ".join(suggestions)
            )
        else:
            self.sebas.speak("I could not process that instruction, sir.")

        return True