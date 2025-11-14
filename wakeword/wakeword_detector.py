import logging
import threading
import sounddevice as sd
import numpy as np
import time
import os

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk not installed - wake word disabled")

"""
Wake word detector using:
    - live microphone input
    - Vosk speech-to-text
    - keyword matching in recognized text
    
Keyword: "sebas" (configurable)
"""


class WakeWordDetector:
    """
    Continuous wake word listener using Vosk.
    Runs in background thread, triggers callback when keyword detected.
    """
    
    def __init__(self, callback, keyword="sebas"):
        self.callback = callback
        self.keyword = keyword.lower()
        self.running = False
        self.thread = None
        self.model = None
        self.recognizer = None
        
        # Audio settings
        self.RATE = 16000
        self.CHUNK_SIZE = 4000
        
        self._init_model()

    def _init_model(self):
        """Initialize Vosk model for wake word detection."""
        if not VOSK_AVAILABLE:
            logging.error("[WakeWord] Vosk not available")
            return
        
        # Try to find model
        model_paths = [
            "model/vosk-model-small-en-us-0.15",
            "vosk-model-small-en-us",
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            logging.error("[WakeWord] No Vosk model found. Run: python setup_stage1.py")
            return
        
        try:
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(False)  # Don't need word timing for wake word
            logging.info(f"[WakeWord] Vosk model loaded from {model_path}")
        except Exception as e:
            logging.exception("[WakeWord] Failed to load model")

    def start(self):
        """Start wake word detection in background thread."""
        if not self.model or not self.recognizer:
            logging.warning("[WakeWord] No model loaded - wake word disabled")
            return
        
        if self.running:
            logging.warning("[WakeWord] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWord")
        self.thread.start()
        logging.info("[WakeWord] Wake word detector started")

    def stop(self):
        """Stop wake word detection."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _listen_loop(self):
        """Main listening loop - captures audio and processes it."""
        try:
            with sd.RawInputStream(
                samplerate=self.RATE,
                blocksize=self.CHUNK_SIZE,
                dtype='int16',
                channels=1,
            ) as stream:
                logging.info(f"[WakeWord] Listening for keyword '{self.keyword}'...")
                
                # Buffer for accumulating audio
                audio_buffer = []
                buffer_duration = 2.0  # Keep 2 seconds of audio
                max_buffer_size = int(buffer_duration * self.RATE / self.CHUNK_SIZE)
                
                while self.running:
                    # Read audio chunk
                    data, overflowed = stream.read(self.CHUNK_SIZE)
                    
                    if overflowed:
                        logging.debug("[WakeWord] Audio buffer overflowed")
                    
                    # Add to buffer
                    audio_buffer.append(data)
                    if len(audio_buffer) > max_buffer_size:
                        audio_buffer.pop(0)
                    
                    # Convert to bytes for Vosk
                    audio_bytes = bytes(data)
                    
                    # Process with Vosk
                    if self.recognizer.AcceptWaveform(audio_bytes):
                        result = self.recognizer.Result()
                        text = self._extract_text(result)
                        
                        if text:
                            logging.debug(f"[WakeWord] Full result: {text}")
                            if self.keyword in text:
                                logging.info(f"[WakeWord] DETECTED: {text}")
                                self._trigger_callback()
                    else:
                        # Check partial results too
                        partial = self.recognizer.PartialResult()
                        text = self._extract_text(partial)
                        
                        if text:
                            logging.debug(f"[WakeWord] Partial: {text}")
                            if self.keyword in text:
                                logging.info(f"[WakeWord] DETECTED (partial): {text}")
                                self._trigger_callback()
                            
        except Exception as e:
            logging.exception("[WakeWord] Error in listen loop")
            self.running = False

    def _trigger_callback(self):
        """Execute callback in separate thread to avoid blocking audio."""
        try:
            # Reset recognizer to avoid echo detection
            if self.model:
                self.recognizer = KaldiRecognizer(self.model, self.RATE)
                self.recognizer.SetWords(False)
            
            # Run callback in thread
            threading.Thread(
                target=self.callback, 
                daemon=True, 
                name="WakeWordCallback"
            ).start()
            
        except Exception as e:
            logging.exception("[WakeWord] Callback error")

    @staticmethod
    def _extract_text(json_result: str) -> str:
        """Extract text from Vosk JSON result."""
        import json
        try:
            data = json.loads(json_result)
            
            # Try 'text' first (full result)
            if 'text' in data:
                return data['text'].lower().strip()
            
            # Try 'partial' (partial result)
            if 'partial' in data:
                return data['partial'].lower().strip()
                
        except Exception:
            pass
        
        return ""