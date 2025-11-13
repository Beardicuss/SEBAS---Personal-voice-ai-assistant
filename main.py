
"""
SEBAS CORE MAIN CONTROLLER
Clean, modular, scalable architecture for Jarvis-like assistant.
This is the NEW main.py skeleton that replaces the old 3000-line monster.
"""

import logging
import threading
import time
import requests

# === Core Services ===
from sebas.permissions.permission_manager import PermissionManager
from sebas.services.language_manager import LanguageManager
from sebas.services.skill_registry import SkillRegistry
from sebas.services.nlu import SimpleNLU, ContextManager

# === Audio Modules (mock placeholders for now) ===
from sebas.stt.stt_manager import STTManager
from sebas.tts.tts_manager import TTSManager

# === Wake Word Module ===
from sebas.audio.wake_word import WakeWordDetector

# === UI & API ===
from sebas.api.ui_server import start_ui_server
from sebas.api.api_server import create_api_server

# ============================================================
#                       SEBAS CORE
# ============================================================

class Sebas:
    """Central brain of the assistant. Handles flow between STT → NLU → Skills → TTS."""

    def __init__(self):
        logging.info("Initializing Sebas assistant...")

        # ----------------------------------------------
        # Language Manager
        # ----------------------------------------------
        self.language_manager = LanguageManager(default_lang="en")

        # ----------------------------------------------
        # Permissions / Roles
        # ----------------------------------------------
        self.permission_manager = PermissionManager()
        self.user_role = "owner"   # hybrid role (admin + owner)

        # ----------------------------------------------
        # NLU + Context
        # ----------------------------------------------
        self.nlu = SimpleNLU()
        self.context = ContextManager()

        # ----------------------------------------------
        # STT & TTS Managers
        # ----------------------------------------------
        self.stt = STTManager(language_manager=self.language_manager)
        self.tts = TTSManager(language_manager=self.language_manager)

        # ----------------------------------------------
        # Skill System
        # ----------------------------------------------
        self.skill_registry = SkillRegistry()
        self.skill_registry.load_skills()

        # ----------------------------------------------
        # Wake Word Detector (Porcupine for now)
        # ----------------------------------------------
        self.wakeword = WakeWordDetector(callback=self._on_wake_word)

        logging.info("Sebas fully initialized.")

    # ========================================================
    #                   Speech Output
    # ========================================================
    def speak(self, text: str):
        """Send text to TTS engine."""
        logging.info(f"Sebas speaking: {text}")
        self.tts.speak(text)

    # ========================================================
    #                   Listening / STT
    # ========================================================
    def listen(self, timeout=5):
        """Capture user audio and transcribe."""
        return self.stt.listen(timeout=timeout)

    # ========================================================
    #             Wake Word Callback
    # ========================================================
    def _on_wake_word(self, text=None):
        """Trigger when wake word detected."""
        self.speak("Yes, sir?")
        command = self.listen()
        if command:
            self.parse_and_execute(command)

    # ========================================================
    #           Command Parsing + Intent Handling
    # ========================================================
    def parse_and_execute(self, raw_command):
        """NLU pipeline: preprocess → detect language → get intent → run skill."""

        if not raw_command:
            return

        # Auto language detection
        self.language_manager.detect_language(raw_command)

        command = raw_command.lower()

        # Manual language switching
        if command.startswith("language ") or command.startswith("set language"):
            lang = command.replace("set language", "").replace("language", "").strip()
            if self.language_manager.set_language(lang):
                self.speak(f"Language set to {self.language_manager.get_current_language_name()}")
            else:
                self.speak("Unsupported language.")
            return

        # Run NLU
        intent, suggestions = self.nlu.get_intent_with_confidence(command)

        if not intent:
            self.speak("I did not understand, sir.")
            return

        # Save context
        self.context.add({
            "type": "intent",
            "name": intent.name,
            "slots": intent.slots,
            "confidence": intent.confidence
        })

        # Check permissions
        if not self.permission_manager.has_permission(self.user_role, intent.name):
            self.speak("You do not have permission for this action.")
            return

        # Dispatch skill
        handled = self.skill_registry.handle_intent(intent.name, intent.slots)

        if not handled:
            self.speak("This command is not implemented yet, sir.")

    # ========================================================
    #               Startup Routine
    # ========================================================
    def start(self):
        """Start wake word thread + speak greeting."""
        self.speak("Sebas online and awaiting your orders, sir.")
        self.wakeword.start()


# ============================================================
#                       ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    assistant = Sebas()

    # Start UI server
    start_ui_server()

    # Start API server
    api = create_api_server(sebas_instance=assistant, host="127.0.0.1", port=5002)
    api.start()

    # Start assistant core loop
    assistant.start()

    # Keep alive
    while True:
        time.sleep(1)