"""
SEBAS CORE MAIN CONTROLLER – Stage 2 Mk.II with Self-Learning & Personality
Ultra-advanced local learning system + personality engine integrated
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

# === Preferences ===
from sebas.constants.preferences import PreferenceStore

# === Self-Learning System ===
from sebas.learning.memory_store import MemoryStore
from sebas.learning.learning_manager import LearningManager


# ============================================================
#                       SEBAS CORE
# ============================================================

class Sebas:
    """
    Central brain of the assistant.
    Handles the flow:
        WakeWord → STT → NLU → Skills → TTS.
    Now with self-learning and personality engine!
    """

    def __init__(self):
        logging.info("[SEBAS] Initializing SEBAS Stage 2 Mk.II with Self-Learning & Personality...")

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
        self.tts = TTSManager(
            language_manager=self.language_manager,
            piper_model_path="sebas/voices/piper/en_US-john-medium.onnx",
            piper_config_path="sebas/voices/piper/en_US-john-medium.onnx.json"
        )

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
        # Wake Word Detector (with 10-second timeout)
        # --------------------------------------------------
        self.wakeword = WakeWordDetector(
            callback=self._on_wake_word,
            timeout_seconds=10
        )

        # --------------------------------------------------
        # Self-Learning System 🧠
        # --------------------------------------------------
        try:
            self.memory = MemoryStore(path="sebas/data/learning_memory.json")
            self.learning = LearningManager(
                nlu=self.nlu,
                prefs=None,
                memory_store=self.memory,
                assistant_ref=self
            )
            logging.info("[SEBAS] ✓ Self-learning system initialized")
        except Exception as e:
            logging.error(f"[SEBAS] Failed to initialize self-learning: {e}")
            self.learning = None

        # --------------------------------------------------
        # Personality Engine 🎭
        # --------------------------------------------------
        try:
            from sebas.personality.persona_core import PersonalityEngine
            self.persona = PersonalityEngine()
            self.persona.set_mode("default")
            logging.info("[SEBAS] ✓ Personality engine initialized")
        except Exception as e:
            logging.error(f"[SEBAS] Failed to initialize personality engine: {e}")
            self.persona = None

        logging.info("[SEBAS] Stage 2 fully initialized with self-learning & personality")

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
    def _on_wake_word(self, detected_text=None):
        """
        Triggered when wake word is detected.
        Handles both initial wake word and commands during listening window.
        """
        logging.info(f"[WakeWord] Callback triggered with: '{detected_text}'")
        self.events.emit("core.wake_word_detected", detected_text)

        # Special timeout message
        if detected_text == "__TIMEOUT__":
            self.speak("Speak, fool.")
            return

        # Empty string means just wake word, no command yet
        if detected_text == "":
            self.speak("Yes, sir? I'm listening.")
            return
        
        # If we got a command, execute it
        if detected_text and isinstance(detected_text, str) and detected_text.strip():
            command = detected_text.strip()
            self.parse_and_execute(command)
            return
        
        # Fallback: ask for command (shouldn't reach here normally)
        self.speak("Yes, sir?")
        command = self.listen()
        if command:
            self.parse_and_execute(command)

    # ========================================================
    #           Command Parsing + Intent Handling
    # ========================================================
    def parse_and_execute(self, raw_command: str) -> str:
        """
        NLU pipeline with event hooks and self-learning.
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

        # -------- Learn from this interaction 🧠 --------
        if self.learning:
            try:
                self.learning.save_after_interaction(
                    text=command,
                    intent=intent.name,
                    slots=intent.slots,
                    success=handled,
                    confidence=intent.confidence
                )
            except Exception as e:
                logging.error(f"[SEBAS] Learning error: {e}")

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
        self.speak("MASTER SEBAS is online with self-learning enabled, sir.")
        self.wakeword.start()
        logging.info("[WakeWord] Detection started")


# ============================================================
#                       ENTRYPOINT
# ============================================================

def main():
    """Main entry point for SEBAS Stage 2."""
    
    # Setup logging with UTF-8 encoding support
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('sebas_stage2.log', encoding='utf-8')
        ]
    )

    logging.info("=" * 60)
    logging.info("[SEBAS] Stage 2 Mk.II with Self-Learning & Personality - STARTING")
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
        
        time.sleep(0.5)

        # Print status
        status = assistant.skill_registry.get_skill_status()
        logging.info("[SEBAS] Stage 2 is RUNNING with SELF-LEARNING")
        logging.info(f"[INFO] Skills Loaded: {status['loaded']}")
        logging.info(f"[INFO] Total Intents: {status['total_intents']}")
        
       # Learning stats
        if assistant.learning:
            stats = assistant.learning.get_stats_summary()
            logging.info(f"[LEARNING] Total interactions: {stats.get('total_interactions', 0)}")
            logging.info(f"[LEARNING] Corrections learned: {stats.get('corrections_learned', 0)}")
            logging.info(f"[LEARNING] Custom patterns: {stats.get('custom_patterns', 0)}")
            logging.info(f"[LEARNING] Workflows: {stats.get('workflows', 0)}")
            logging.info(f"[LEARNING] Semantic clusters: {stats.get('semantic_clusters', 0)}")
            
            # Show most used intents
            most_used = stats.get('most_used_intents', [])
            if most_used:
                logging.info(f"[LEARNING] Most used intents: {', '.join(most_used)}")
        
        logging.info("[INFO] Open http://127.0.0.1:5000 in your browser")
        logging.info("[INFO] Say 'Master SEBAS' once, then give commands for 10 seconds")
        logging.info("Press Ctrl+C to exit")

        # Keep process alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("\n[SEBAS] Shutting down Stage 2...")
    except Exception as e:
        logging.exception("[ERROR] FATAL ERROR in SEBAS Stage 2")
        sys.exit(1)


if __name__ == "__main__":
    main()