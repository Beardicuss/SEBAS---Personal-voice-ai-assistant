"""
SEBAS CORE MAIN CONTROLLER – EventBus Integrated
Clean, modular, scalable architecture for assistant.
"""

import logging
import time

# === Core Services ===
from sebas.permissions.permission_manager import PermissionManager
from sebas.services.language_manager import LanguageManager
from sebas.services.skill_registry import SkillRegistry
from sebas.services.nlu import SimpleNLU, ContextManager

# === Audio Modules ===
from sebas.stt.stt_manager import STTManager
from sebas.tts.tts_manager import TTSManager

# === Wake Word Module ===
from sebas.wakeword.wakeword_detector import WakeWordDetector

# === UI & API ===
from sebas.api.ui_server import start_ui_server
from sebas.api.api_server import create_api_server

# === Events ===
from sebas.events.event_bus import EventBus


# ============================================================
#                       SEBAS CORE
# ============================================================

class Sebas:
    """
    Central brain of the assistant.
    Handles the flow:
        WakeWord → STT → NLU → Skills → TTS.
    """

    def __init__(self):
        logging.info("Initializing Sebas assistant...")

        # --------------------------------------------------
        # Global Event Bus
        # --------------------------------------------------
        self.events = EventBus()

        # --------------------------------------------------
        # Language Manager
        # --------------------------------------------------
        self.language_manager = LanguageManager(default_lang="en")

        # --------------------------------------------------
        # Permissions / Roles
        # --------------------------------------------------
        self.permission_manager = PermissionManager()
        self.user_role = "owner"  # full access

        # --------------------------------------------------
        # NLU + Context Memory
        # --------------------------------------------------
        self.nlu = SimpleNLU()
        self.context = ContextManager()

        # --------------------------------------------------
        # STT & TTS Managers
        # --------------------------------------------------
        self.stt = STTManager(language_manager=self.language_manager)
        self.tts = TTSManager(language_manager=self.language_manager)

        # Bind language manager to voice + recognition systems
        self.language_manager.bind_stt(self.stt)
        self.language_manager.bind_tts(self.tts)

        # --------------------------------------------------
        # Skill System — Auto Loader Mk.III + EventBus
        # --------------------------------------------------
        self.skill_registry = SkillRegistry(event_bus=self.events)
        self.skill_registry.load_skills()

        # --------------------------------------------------
        # Wake Word Detector
        # --------------------------------------------------
        self.wakeword = WakeWordDetector(callback=self._on_wake_word)

        logging.info("Sebas fully initialized.")

        # Emit startup event
        self.events.emit("core.started")

    # ========================================================
    #                   Speech Output
    # ========================================================
    def speak(self, text: str):
        """Send text to TTS engine and emit events."""
        if not text:
            return

        logging.info(f"Sebas speaking: {text}")
        self.events.emit("core.before_speak", text)

        self.tts.speak(text)

        self.events.emit("core.after_speak", text)

    # ========================================================
    #                   Listening / STT
    # ========================================================
    def listen(self, timeout: int = 5):
        """Capture user audio, transcribe, and send events."""
        self.events.emit("core.listen_start")
        text = self.stt.listen(timeout=timeout)
        self.events.emit("core.listen_end", text)
        return text

    # ========================================================
    #             Wake Word Callback
    # ========================================================
    def _on_wake_word(self, text=None):
        """Triggered when wake word is detected."""
        self.events.emit("core.wake_word_detected")
        self.speak("Yes, sir?")
        command = self.listen()
        if command:
            self.parse_and_execute(command)

    # ========================================================
    #           Command Parsing + Intent Handling
    # ========================================================
    def parse_and_execute(self, raw_command: str):
        """NLU pipeline with event hooks."""
        if not raw_command:
            return

        self.events.emit("core.command_received", raw_command)

        # Detect language BEFORE lowercasing
        self.language_manager.detect_language(raw_command)
        command = raw_command.lower().strip()

        # -------- Manual language switching --------
        if command.startswith("language ") or command.startswith("set language"):
            lang = (
                command.replace("set language", "")
                .replace("language", "")
                .strip()
            )
            if self.language_manager.set_language(lang):
                self.speak(
                    f"Language set to {self.language_manager.get_current_language_name()}"
                )
            else:
                self.speak("Unsupported language.")
            return

        # -------- Natural Language Understanding --------
        intent, suggestions = self.nlu.get_intent_with_confidence(command)

        if not intent:
            self.events.emit("core.intent_failed")
            self.speak("I did not understand, sir.")
            return

        self.events.emit("core.intent_detected", intent)

        # Save context
        self.context.add(
            {
                "type": "intent",
                "name": intent.name,
                "slots": intent.slots,
                "confidence": intent.confidence,
            }
        )

        # -------- Permission Check --------
        if not self.permission_manager.has_permission(self.user_role, intent.name):
            self.events.emit("core.permission_denied", intent)
            self.speak("You do not have permission for this action.")
            return

        # -------- Dispatch to Skills --------
        handled = self.skill_registry.handle_intent(intent.name, intent.slots, self)

        if handled:
            self.events.emit("core.intent_handled", intent)
        else:
            self.events.emit("core.intent_unhandled", intent)
            self.speak("This command is not implemented yet, sir.")

    # ========================================================
    #               Startup Routine
    # ========================================================
    def start(self):
        """Start wake word thread and speak greeting."""
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
    api = create_api_server(
        sebas_instance=assistant,
        host="127.0.0.1",
        port=5002
    )
    api.start()

    # Start Sebas core
    assistant.start()

    # Keep process alive
    while True:
        time.sleep(1)