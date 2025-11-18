"""
SEBAS CORE MAIN CONTROLLER – Stage 1 Mk.I ENHANCED
Clean, modular, stable architecture for voice assistant.
Unicode-safe logging for Windows.
WITH LEARNING SYSTEM INTEGRATION - ALL PYLANCE ERRORS FIXED
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

# === Learning System ===
from sebas.integrations.learning_system import LearningSystem, LearningNLU
from sebas.integrations.learning_integration import (
    LearningSEBASIntegration,
    VoiceLearningHelper,
    CommandHistory,
    LearningSkill
)


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
        self.tts = TTSManager(
            language_manager=self.language_manager,
            piper_model_path="sebas/voices/piper/en_US-john-medium.onnx",
            piper_config_path="sebas/voices/piper/en_US-john-medium.onnx.json"
        )

        # Bind language manager to voice + recognition systems
        self.language_manager.bind_stt(self.stt)
        self.language_manager.bind_tts(self.tts)

        # --------------------------------------------------
        # Skill System – Auto Loader
        # --------------------------------------------------
        self.skill_registry = SkillRegistry(
            assistant_ref=self,
            skills_dir="skills"
        )

        # --------------------------------------------------
        # Learning System Integration
        # --------------------------------------------------
        try:
            logging.info("[SEBAS] Initializing learning system...")
            self.learning = LearningSystem()
            
            # Wrap existing NLU with learning capabilities
            original_nlu = self.nlu
            self.nlu = LearningNLU(original_nlu, self.learning)
            
            # Create learning integrations
            self.learning_integration = LearningSEBASIntegration(self.learning, self)
            self.voice_learning = VoiceLearningHelper(self.learning)
            self.command_history = CommandHistory(max_history=100)
            
            # Register learning skill for voice commands
            learning_skill = LearningSkill(self.learning_integration)
            # Type ignore because LearningSkill is a duck-typed skill
            self.skill_registry.skills.append(learning_skill)  # type: ignore
            
            logging.info("[SEBAS] Learning system initialized successfully")
        except Exception as e:
            logging.error(f"[SEBAS] Learning system initialization failed: {e}")
            logging.exception("[SEBAS] Full error details:")
            logging.info("[SEBAS] Continuing without learning capabilities")
            # System will work without learning
            self.learning = None
            self.learning_integration = None

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
    def _on_wake_word(self, detected_text=None):
        """
        Triggered when wake word is detected.
        
        Args:
            detected_text: The full text that was recognized (e.g., "sebas open notepad")
        """
        logging.info(f"[WakeWord] Detected! Text: '{detected_text}'")
        self.events.emit("core.wake_word_detected", detected_text)
        
        # Check if command was included in the wake word detection
        if detected_text and isinstance(detected_text, str):
            # Remove the wake word from the text to extract the command
            keyword = self.wakeword.keyword
            detected_lower = detected_text.lower()
            
            if keyword in detected_lower:
                # Extract command after wake word
                # e.g., "sebas open notepad" -> "open notepad"
                parts = detected_lower.split(keyword, 1)
                if len(parts) > 1:
                    command = parts[1].strip()
                    if command:
                        logging.info(f"[WakeWord] Command detected in wake phrase: '{command}'")
                        self.speak("Yes, sir?")
                        # Execute the command directly
                        self.parse_and_execute(command)
                        return
        
        # No command detected, ask for one
        self.speak("Yes, sir?")
        command = self.listen()
        if command:
            self.parse_and_execute(command)

    # ========================================================
    #           Command Parsing + Intent Handling
    # ========================================================
    def parse_and_execute(self, raw_command: str, source: str = 'voice') -> str:
        """
        NLU pipeline with event hooks and learning support.
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

        # -------- Natural Language Understanding (with Learning) --------
        intent = None
        try:
            # Use learning-enhanced NLU if available
            if hasattr(self.nlu, 'parse'):
                # LearningNLU accepts source parameter
                if isinstance(self.nlu, LearningNLU):
                    intent = self.nlu.parse(command, source=source)
                else:
                    # Basic NLU doesn't accept source
                    intent = self.nlu.parse(command)
            elif hasattr(self.nlu, 'get_intent_with_confidence'):
                # Fallback to basic NLU
                intent, suggestions = self.nlu.get_intent_with_confidence(command)
        except Exception as e:
            logging.error(f"[NLU] Error parsing command: {e}")
            logging.exception("[NLU] Full traceback:")
            intent = None

        if not intent or not hasattr(intent, 'name') or not intent.name:
            self.events.emit("core.intent_failed", None)
            
            # Track failed command for learning
            if hasattr(self, 'command_history'):
                self.command_history.add(command, None, source, False)
            
            msg = "I did not understand, sir. You can teach me by saying: 'this means' followed by the intent name."
            self.speak(msg)
            return msg

        self.events.emit("core.intent_detected", intent)

        # -------- Handle Learning Correction --------
        if intent.name == 'learning_correction':
            corrected_intent = intent.slots.get('intent', '')
            if hasattr(self, 'learning_integration') and self.learning_integration:
                success = self.learning_integration.handle_learning_correction(command, corrected_intent)
                return "Learning correction applied" if success else "Learning correction failed"
            return "Learning system not available"

        # Save context
        self.context.add(
            {
                "type": "intent",
                "name": intent.name,
                "slots": intent.slots,
                "confidence": getattr(intent, 'confidence', 1.0),
            }
        )

        # -------- Permission Check --------
        if not is_authorized(self.user_role, intent.name):
            self.events.emit("core.permission_denied", intent)
            msg = "You do not have permission for this action."
            self.speak(msg)
            return msg

        # -------- Dispatch to Skills --------
        try:
            result = self.skill_registry.handle_intent(intent.name, intent.slots)
            
            # Extract boolean success from result
            # Handle both bool and SkillResponse types
            if hasattr(result, 'success'):
                # It's a SkillResponse object
                handled = result.success
            else:
                # It's a boolean
                handled = bool(result)
            
            # Track execution for learning
            if hasattr(self, 'learning_integration') and self.learning_integration:
                self.learning_integration.track_skill_execution(
                    intent.name, 
                    handled,
                    error=None if handled else "Skill execution failed"
                )
            
            # Track in command history
            if hasattr(self, 'command_history'):
                self.command_history.add(command, intent.name, source, handled)
            
            if handled:
                self.events.emit("core.intent_handled", intent)
                return f"Command executed: {intent.name}"
            else:
                self.events.emit("core.intent_unhandled", intent)
                msg = "This command is not implemented yet, sir."
                self.speak(msg)
                return msg
                
        except Exception as e:
            logging.exception(f"[SKILL] Error executing intent {intent.name}")
            if hasattr(self, 'learning_integration') and self.learning_integration:
                self.learning_integration.track_skill_execution(
                    intent.name, 
                    False,
                    error=str(e)
                )
            msg = "An error occurred while executing the command."
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
        level=logging.DEBUG,
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
        
        time.sleep(0.5)

        logging.info("[SEBAS] Stage 1 is RUNNING")
        logging.info("[INFO] Open http://127.0.0.1:5000 in your browser")
        logging.info("[INFO] Say 'SEBAS' followed by your command")
        logging.info("[INFO] Example: 'SEBAS open notepad' or 'SEBAS what time is it'")
        logging.info("[INFO] Or type commands in the web UI")
        
        # Only mention learning if it's active
        if hasattr(assistant, 'learning') and assistant.learning:
            logging.info("[INFO] Learning system is active - teach SEBAS new commands!")
        
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