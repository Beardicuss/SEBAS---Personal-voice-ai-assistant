import logging
from .piper_tts import PiperTTS

class TTSManager:
    """Unified text-to-speech manager using PiperTTS only."""

    def __init__(self, language_manager=None, piper_model_path=None, piper_config_path=None):
        self.language_manager = language_manager
        self.engine: PiperTTS | None = None
        
        logging.info("[TTSManager] Initializing PiperTTS only...")

        try:
            logging.info("[TTSManager] Creating PiperTTS instance...")
            self.engine = PiperTTS(model_path=piper_model_path, config_path=piper_config_path)
            
            # Wait a moment for initialization to complete
            import time
            time.sleep(0.2)
            
            # Check if engine was created (not None) and has voice loaded
            if self.engine is not None:
                if hasattr(self.engine, 'voice') and self.engine.voice is not None:
                    logging.info("[TTSManager] PiperTTS initialized successfully")
                    logging.info(f"[TTSManager] Voice available: {self.engine.voice is not None}")
                else:
                    logging.error("[TTSManager] PiperTTS created but voice is None!")
                    logging.error("[TTSManager] Check model paths and files")
            else:
                logging.error("[TTSManager] PiperTTS instance is None!")
                
        except Exception as e:
            logging.exception(f"[TTSManager] Failed to initialize PiperTTS: {e}")
            self.engine = None

    def speak(self, text: str):
        logging.info(f"[TTSManager] speak() called with text: '{text}'")
        
        if self.engine is None:
            logging.error("[TTSManager] TTS engine is None.")
            return
        
        logging.info(f"[TTSManager] Engine exists: {self.engine is not None}")
        logging.info(f"[TTSManager] Has voice attr: {hasattr(self.engine, 'voice')}")
        if hasattr(self.engine, 'voice'):
            logging.info(f"[TTSManager] Voice is not None: {self.engine.voice is not None}")
        
        logging.info("[TTSManager] Calling self.engine.speak()...")
        try:
            self.engine.speak(text)
            logging.info("[TTSManager] self.engine.speak() completed")
        except Exception as e:
            logging.exception(f"[TTSManager] Error during speak: {e}")

    def set_voice(self, voice_hint: str):
        """Set voice - delegates to PiperTTS."""
        if not self.engine:
            logging.warning("[TTSManager] Cannot set voice, engine is None")
            return False

        return self.engine.set_voice(voice_hint)

    def list_voices(self):
        if not self.engine:
            logging.warning("[TTSManager] Cannot list voices, engine is None")
            return []
        return self.engine.list_voices()

    def stop(self):
        """Stop any ongoing speech."""
        if self.engine:
            self.engine.stop()

    def get_engine_info(self):
        """Get information about current TTS engine."""
        if not self.engine:
            return "No engine"
        return "PiperTTS (Neural)"