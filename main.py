"""
SEBAS CORE MAIN CONTROLLER – Stage 1 Mk.I ENHANCED
Clean, modular, stable architecture for voice assistant.
Unicode-safe logging for Windows.
"""

import logging
import time
import sys
import os

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
from sebas.api.ui_server import start_ui_server, set_command_handler
from sebas.api.api_server import APIServer

# === Events ===
from sebas.events.event_bus import EventBus

# === Permissions ===
from sebas.constants.permissions import Role, is_authorized


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
        logging.info("[SEBAS] Initializing SEBAS Stage 1 Mk.I Enhanced...")

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
        self.user_role = Role.ADMIN_OWNER  # Full access for owner

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
        # Skill System — Auto Loader
        # --------------------------------------------------
        self.skill_registry = SkillRegistry(
            assistant_ref=self,
            skills_dir="skills"
        )

        # --------------------------------------------------
        # Wake Word Detector
        # --------------------------------------------------
        self.wakeword = WakeWordDetector(callback=self._on_wake_word)

        logging.info("[SEBAS] Stage 1 fully initialized")

        # Emit startup event
        self.events.emit("core.started", None)

    # ========================================================
    #                   Speech Output
    # ========================================================
    def speak(self, text: str):
        """Send text to TTS engine and emit events."""
        if not text:
            return

        logging.info(f"[SEBAS] Speaking: {text}")
        self.events.emit("core.before_speak", text)

        self.tts.speak(text)

        self.events.emit("core.after_speak", text)

    # ========================================================
    #                   Listening / STT
    # ========================================================
    def listen(self, timeout: int = 5) -> str:
        """Capture user audio, transcribe, and send events."""
        self.events.emit("core.listen_start", None)
        text = self.stt.listen(timeout=timeout)
        self.events.emit("core.listen_end", text)
        return text

    # ========================================================
    #             Wake Word Callback
    # ========================================================
    def _on_wake_word(self, data=None):
        """Triggered when wake word is detected."""
        logging.info("[WakeWord] Detected!")
        self.events.emit("core.wake_word_detected", None)
        self.speak("Yes, sir?")
        command = self.listen()
        if command:
            self.parse_and_execute(command)

    # ========================================================
    #           Command Parsing + Intent Handling
    # ========================================================
    def parse_and_execute(self, raw_command: str) -> str:
        """
        NLU pipeline with event hooks.
        Returns response message for UI/API.
        """
        if not raw_command:
            return "No command received"

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
                msg = f"Language set to {self.language_manager.get_current_language_name()}"
                self.speak(msg)
                return msg
            else:
                msg = "Unsupported language."
                self.speak(msg)
                return msg

        # -------- Natural Language Understanding --------
        intent, suggestions = self.nlu.get_intent_with_confidence(command)

        if not intent:
            self.events.emit("core.intent_failed", None)
            msg = "I did not understand, sir."
            self.speak(msg)
            return msg

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
        if not is_authorized(self.user_role, intent.name):
            self.events.emit("core.permission_denied", intent)
            msg = "You do not have permission for this action."
            self.speak(msg)
            return msg

        # -------- Dispatch to Skills --------
        handled = self.skill_registry.handle_intent(intent.name, intent.slots)

        if handled:
            self.events.emit("core.intent_handled", intent)
            return f"Command executed: {intent.name}"
        else:
            self.events.emit("core.intent_unhandled", intent)
            msg = "This command is not implemented yet, sir."
            self.speak(msg)
            return msg

    # ========================================================
    #               Startup Routine
    # ========================================================
    def start(self):
        """Start wake word thread and speak greeting."""
        self.speak("SEBAS Stage 1 online and awaiting your orders, sir.")
        self.wakeword.start()
        logging.info("[WakeWord] Detection started")


# ============================================================
#                       ENTRYPOINT
# ============================================================

def main():
    """Main entry point for SEBAS Stage 1."""
    
    # Setup logging with UTF-8 encoding support
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('sebas_stage1.log', encoding='utf-8')
        ]
    )

    logging.info("=" * 60)
    logging.info("[SEBAS] Stage 1 Mk.I Enhanced - STARTING")
    logging.info("=" * 60)

    try:
        # Initialize SEBAS
        assistant = Sebas()

        # Register command handler for UI
        set_command_handler(assistant.parse_and_execute)

        # Start UI server
        logging.info("[UI] Starting server on http://127.0.0.1:5000")
        start_ui_server(host="127.0.0.1", port=5000)

        # Start API server
        logging.info("[API] Starting server on http://127.0.0.1:5002")
        api = APIServer(
            sebas_instance=assistant,
            nlu=assistant.nlu,
            host="127.0.0.1",
            port=5002
        )
        api.start()

        # Start SEBAS core
        assistant.start()

        logging.info("[SEBAS] Stage 1 is RUNNING")
        logging.info("[INFO] Open http://127.0.0.1:5000 in your browser")
        logging.info("[INFO] Say 'SEBAS' followed by your command")
        logging.info("[INFO] Or type commands in the web UI")
        logging.info("Press Ctrl+C to exit")

        # Keep process alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("\n[SEBAS] Shutting down Stage 1...")
    except Exception as e:
        logging.exception("[ERROR] FATAL ERROR in SEBAS Stage 1")
        sys.exit(1)


if __name__ == "__main__":
    main()