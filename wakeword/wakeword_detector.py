"""
Wake Word Detector - Stage 1 Mk.I (FIXED)
Robust, fail-safe wake word detection with fallback modes.
"""

import logging
import threading
import time
import os

# Safe imports with fallback
try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("sounddevice not available - wake word disabled")

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk not available - wake word disabled")


class WakeWordDetector:
    """
    Robust wake word detector with multiple fallback modes.
    
    Modes:
    1. Vosk (primary) - Accurate speech recognition
    2. Keyword match (fallback) - Simple pattern matching
    3. Manual trigger (fallback) - Keyboard/API activation
    """
    
    def __init__(self, callback, keyword="sebas"):
        self.callback = callback
        self.keyword = keyword.lower()
        self.running = False
        self.thread = None
        self.mode = "disabled"
        
        # Audio settings
        self.RATE = 16000
        self.CHUNK_SIZE = 4000
        
        # Detection settings
        self.confidence_threshold = 0.7
        self.cooldown_seconds = 2.0
        self.last_trigger_time = 0
        
        # Initialize best available mode
        self._init_detection_mode()
    
    def _init_detection_mode(self):
        """Initialize the best available detection mode."""
        
        # Try Vosk mode
        if VOSK_AVAILABLE and AUDIO_AVAILABLE:
            success = self._init_vosk_mode()
            if success:
                self.mode = "vosk"
                logging.info(f"[WakeWord] Vosk mode initialized for '{self.keyword}'")
                return
        
        # Fallback to keyboard trigger mode
        self.mode = "manual"
        logging.warning("[WakeWord] Using manual trigger mode (press SPACE to activate)")
    
    def _init_vosk_mode(self) -> bool:
        """Initialize Vosk speech recognition."""
        model_paths = [
            "model/vosk-model-small-en-us-0.15",
            "vosk-model-small-en-us",
            os.path.expanduser("~/vosk-models/vosk-model-small-en-us-0.15"),
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            logging.error(
                "[WakeWord] No Vosk model found. Download from:\n"
                "https://alphacephei.com/vosk/models\n"
                "Extract to: model/vosk-model-small-en-us-0.15"
            )
            return False
        
        try:
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(False)
            return True
        except Exception:
            logging.exception("[WakeWord] Failed to load Vosk model")
            return False
    
    def start(self):
        """Start wake word detection."""
        if self.running:
            logging.warning("[WakeWord] Already running")
            return
        
        self.running = True
        
        if self.mode == "vosk":
            self.thread = threading.Thread(
                target=self._vosk_listen_loop,
                daemon=True,
                name="WakeWordVosk"
            )
            self.thread.start()
            logging.info("[WakeWord] Vosk detection started")
        
        elif self.mode == "manual":
            self.thread = threading.Thread(
                target=self._manual_trigger_loop,
                daemon=True,
                name="WakeWordManual"
            )
            self.thread.start()
            logging.info("[WakeWord] Manual trigger mode active")
    
    def stop(self):
        """Stop wake word detection."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logging.info("[WakeWord] Stopped")
    
    def _vosk_listen_loop(self):
        """Vosk speech recognition loop."""
        try:
            with sd.RawInputStream(
                samplerate=self.RATE,
                blocksize=self.CHUNK_SIZE,
                dtype='int16',
                channels=1,
            ) as stream:
                logging.info(f"[WakeWord] Listening for '{self.keyword}'...")
                
                while self.running:
                    data, overflowed = stream.read(self.CHUNK_SIZE)
                    
                    if overflowed:
                        logging.debug("[WakeWord] Audio buffer overflow")
                    
                    # Process with Vosk
                    audio_bytes = bytes(data)
                    
                    if self.recognizer.AcceptWaveform(audio_bytes):
                        result = self.recognizer.Result()
                        text = self._extract_text(result)
                        
                        if text and self.keyword in text:
                            self._trigger()
                    else:
                        # Check partial results
                        partial = self.recognizer.PartialResult()
                        text = self._extract_text(partial)
                        
                        if text and self.keyword in text:
                            self._trigger()
                            
        except Exception:
            logging.exception("[WakeWord] Error in Vosk listen loop")
            self.running = False
    
    def _manual_trigger_loop(self):
        """Manual trigger mode using keyboard input."""
        logging.info("[WakeWord] Press SPACE to manually trigger wake word")
        
        try:
            # Try to import keyboard library
            import keyboard
            
            while self.running:
                if keyboard.is_pressed('space'):
                    self._trigger()
                    time.sleep(1)  # Debounce
                time.sleep(0.1)
                
        except ImportError:
            logging.warning("[WakeWord] keyboard library not available")
            # Just keep thread alive for API triggers
            while self.running:
                time.sleep(1)
    
    def _trigger(self):
        """Trigger the wake word callback with cooldown."""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_trigger_time < self.cooldown_seconds:
            logging.debug("[WakeWord] Cooldown active, ignoring trigger")
            return
        
        self.last_trigger_time = current_time
        logging.info(f"[WakeWord] TRIGGERED: '{self.keyword}'")
        
        # Execute callback in separate thread to avoid blocking
        try:
            threading.Thread(
                target=self.callback,
                daemon=True,
                name="WakeWordCallback"
            ).start()
        except Exception:
            logging.exception("[WakeWord] Callback execution failed")
    
    def manual_trigger(self):
        """Manually trigger wake word (for API/testing)."""
        self._trigger()
    
    @staticmethod
    def _extract_text(json_result: str) -> str:
        """Extract text from Vosk JSON result."""
        import json
        try:
            data = json.loads(json_result)
            return data.get('text', data.get('partial', '')).lower().strip()
        except Exception:
            return ""
    
    def get_status(self) -> dict:
        """Get current detection status."""
        return {
            'mode': self.mode,
            'running': self.running,
            'keyword': self.keyword,
            'last_trigger': self.last_trigger_time,
            'audio_available': AUDIO_AVAILABLE,
            'vosk_available': VOSK_AVAILABLE
        }