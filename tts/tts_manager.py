"""
TTS Manager - Unified text-to-speech management
"""

import logging
import time
from typing import Optional
from pathlib import Path


class TTSManager:
    """Unified text-to-speech manager using PiperTTS."""

    def __init__(self, language_manager=None, piper_model_path=None, piper_config_path=None):
        """
        Initialize TTS Manager with PiperTTS.
        
        Args:
            language_manager: Optional language manager instance
            piper_model_path: Path to Piper .onnx model file
            piper_config_path: Path to Piper .json config file
        """
        self.language_manager = language_manager
        self.engine: Optional['PiperTTS'] = None
        
        logging.info("[TTSManager] Initializing PiperTTS...")

        try:
            from .piper_tts import PiperTTS
            
            # Set default paths if not provided
            if piper_model_path is None:
                piper_model_path = "sebas/voices/piper/en_US-john-medium.onnx"
            if piper_config_path is None:
                piper_config_path = "sebas/voices/piper/en_US-john-medium.onnx.json"
            
            logging.info("[TTSManager] Creating PiperTTS instance...")
            logging.info(f"[TTSManager] Model: {piper_model_path}")
            logging.info(f"[TTSManager] Config: {piper_config_path}")
            
            self.engine = PiperTTS(
                model_path=piper_model_path, 
                config_path=piper_config_path
            )
            
            # Wait a moment for initialization to complete
            time.sleep(0.2)
            
            # Validate initialization
            if self.engine is not None:
                if hasattr(self.engine, 'voice') and self.engine.voice is not None:
                    logging.info("[TTSManager] ✅ PiperTTS initialized successfully")
                    status = self.engine.get_status()
                    logging.info(f"[TTSManager] Status: {status}")
                else:
                    logging.error("[TTSManager] ❌ PiperTTS created but voice is None!")
                    logging.error("[TTSManager] Check model paths and files:")
                    if piper_model_path:
                        logging.error(f"  Model: {piper_model_path}")
                    if piper_config_path:
                        logging.error(f"  Config: {piper_config_path}")
                    self.engine = None
            else:
                logging.error("[TTSManager] ❌ PiperTTS instance is None!")
                
        except ImportError as e:
            logging.error(f"[TTSManager] Cannot import PiperTTS: {e}")
            logging.error("[TTSManager] Install with: pip install piper-tts sounddevice")
            self.engine = None
        except Exception as e:
            logging.exception(f"[TTSManager] Failed to initialize PiperTTS: {e}")
            self.engine = None

    def speak(self, text: str) -> bool:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logging.warning("[TTSManager] Empty text, skipping")
            return False
        
        logging.info(f"[TTSManager] Speaking: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        if self.engine is None:
            logging.error("[TTSManager] TTS engine is None - cannot speak")
            return False
        
        if not hasattr(self.engine, 'voice') or self.engine.voice is None:
            logging.error("[TTSManager] TTS engine has no voice loaded")
            return False
        
        try:
            self.engine.speak(text)
            return True
        except Exception as e:
            logging.exception(f"[TTSManager] Error during speak: {e}")
            return False

    def set_voice(self, voice_hint: str) -> bool:
        """
        Set voice by hint.
        
        Args:
            voice_hint: Voice identifier or hint
            
        Returns:
            True if successful, False otherwise
        """
        if not self.engine:
            logging.warning("[TTSManager] Cannot set voice, engine is None")
            return False

        try:
            return self.engine.set_voice(voice_hint)
        except Exception as e:
            logging.error(f"[TTSManager] Error setting voice: {e}")
            return False

    def list_voices(self) -> list:
        """
        List available voices.
        
        Returns:
            List of voice info objects
        """
        if not self.engine:
            logging.warning("[TTSManager] Cannot list voices, engine is None")
            return []
        
        try:
            return self.engine.list_voices()
        except Exception as e:
            logging.error(f"[TTSManager] Error listing voices: {e}")
            return []

    def stop(self) -> None:
        """Stop any ongoing speech."""
        if self.engine:
            try:
                self.engine.stop()
                logging.info("[TTSManager] Speech stopped")
            except Exception as e:
                logging.error(f"[TTSManager] Error stopping speech: {e}")

    def is_speaking(self) -> bool:
        """
        Check if currently speaking.
        
        Returns:
            True if speaking, False otherwise
        """
        if not self.engine:
            return False
        
        try:
            return self.engine.is_speaking()
        except Exception as e:
            logging.error(f"[TTSManager] Error checking speaking status: {e}")
            return False

    def get_engine_info(self) -> str:
        """
        Get information about current TTS engine.
        
        Returns:
            Engine description string
        """
        if not self.engine:
            return "No engine loaded"
        
        try:
            status = self.engine.get_status()
            return f"PiperTTS (Neural) - {status.get('language', 'Unknown')}"
        except Exception as e:
            logging.error(f"[TTSManager] Error getting engine info: {e}")
            return "PiperTTS (Neural)"
    
    def get_status(self) -> dict:
        """
        Get detailed TTS status.
        
        Returns:
            Status dictionary
        """
        if not self.engine:
            return {
                'initialized': False,
                'engine': 'none',
                'speaking': False
            }
        
        try:
            engine_status = self.engine.get_status()
            return {
                'initialized': engine_status.get('initialized', False),
                'engine': 'piper',
                'speaking': engine_status.get('speaking', False),
                'worker_running': engine_status.get('worker_running', False),
                'queue_size': engine_status.get('queue_size', 0),
                'language': engine_status.get('language', 'Unknown')
            }
        except Exception as e:
            logging.error(f"[TTSManager] Error getting status: {e}")
            return {
                'initialized': False,
                'engine': 'piper',
                'speaking': False,
                'error': str(e)
            }