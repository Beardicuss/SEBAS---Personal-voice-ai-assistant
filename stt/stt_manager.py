"""
STT Manager - Stage 1 Mk.I (FIXED)
With graceful fallback if Vosk not available
"""

import logging
import os
from pathlib import Path

# Try to import Vosk
try:
    import vosk
    import pyaudio
    import json
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("[STT] Vosk not available - using text input fallback")

from sebas.stt.stt_none import NoSTT


class STTManager:
    """
    Speech-to-Text Manager - Stage 1 Mk.I
    
    Mode 1: Vosk (if model exists)
    Mode 2: Text input fallback (for testing)
    """
    
    def __init__(self, language_manager=None):
        print("[STT DEBUG] STTManager.__init__() called")  # Use print, not logging
        self.language_manager = language_manager
        self.model = None
        self.recognizer = None
        self.engine = None
        self.mode = "none"
        
        # Audio configuration
        self.RATE = 16000
        self.CHUNK = 8000
        self.FORMAT = None
        self.CHANNELS = 1
        self.pa_format = None
        
        print("[STT DEBUG] About to call _init_vosk()")
        self._init_vosk()
        print(f"[STT DEBUG] After _init_vosk(), mode={self.mode}")
    
    def _init_vosk(self):
        """Try to initialize Vosk, fallback gracefully"""
        print(f"[STT DEBUG] _init_vosk() called, VOSK_AVAILABLE={VOSK_AVAILABLE}")
        
        if not VOSK_AVAILABLE:
            print("[STT DEBUG] Vosk not installed")
            logging.warning("[STT] Vosk not installed - using text input")
            self.mode = "text_input"
            self.engine = NoSTT()
            return
        
        base_dir = Path(__file__).resolve().parent.parent

        model_paths = [
            # English models
            base_dir / "model" / "vosk-model-small-en-us-0.15",
            base_dir / "model" / "vosk-model-small-en-us",
            Path(os.path.expanduser("~/vosk-model-small-en-us-0.15")),

            # Russian models
            base_dir / "model" / "vosk-model-small-ru-0.22",
            Path(os.path.expanduser("~/vosk-model-small-ru-0.22")),
        ]
   
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            logging.warning(
                "[STT] No Vosk model found - using text input fallback\n"
                "      Download model from: https://alphacephei.com/vosk/models\n"
                "      Extract to: model/vosk-model-small-en-us-0.15"
            )
            self.mode = "text_input"
            self.engine = NoSTT()
            return
        
        try:
            import pyaudio
            self.FORMAT = pyaudio.paInt16
            self.pa_format = pyaudio.paInt16
            
            # FIX: Convert WindowsPath to string
            model_path_str = str(model_path)
            self.model = vosk.Model(model_path_str)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(True)
            self.mode = "vosk"
            logging.info(f"[STT] Vosk initialized from {model_path}")
            
        except Exception as e:
            logging.exception(f"[STT] Failed to load Vosk: {e}")  # This should show in logs
            logging.warning("[STT] Falling back to text input")
            self.mode = "text_input"
            self.engine = NoSTT()

    def listen(self, timeout: int = 5) -> str:
        """
        Listen to user input (audio or text fallback)
        
        Args:
            timeout: Maximum seconds to listen (Vosk mode)
            
        Returns:
            Transcribed text or empty string
        """
        
        # TEXT INPUT FALLBACK MODE
        if self.mode == "text_input":
            logging.info("[STT] Text input mode - type your command:")
            try:
                text = input("You: ").strip()
                if text:
                    logging.info(f"[STT] Received: {text}")
                return text
            except (EOFError, KeyboardInterrupt):
                return ""
        
        # VOSK AUDIO MODE
        if self.mode == "vosk" and self.recognizer:
            return self._listen_vosk(timeout)
        
        # NO STT AVAILABLE
        logging.error("[STT] No speech recognition available")
        return ""
    
    def _listen_vosk(self, timeout: int) -> str:
        """Listen using Vosk (original implementation)"""
        # Type guard - ensure recognizer is available
        if not self.recognizer:
            logging.error("[STT] Vosk recognizer not initialized")
            return ""
        
        import pyaudio
        
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            # Use stored format (guaranteed to be set if we got here)
            audio_format = self.pa_format if self.pa_format is not None else pyaudio.paInt16
            
            stream = audio.open(
                format=audio_format,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            logging.info("[STT] Listening... (speak now)")
            
            frames = []
            silence_threshold = 3
            silence_chunks = int(silence_threshold * self.RATE / self.CHUNK)
            silent_chunks_count = 0
            has_speech = False
            
            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        has_speech = True
                        logging.info(f"[STT] Recognized: {text}")
                        return text
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        has_speech = True
                        silent_chunks_count = 0
                    else:
                        silent_chunks_count += 1
                
                # Stop after silence
                if has_speech and silent_chunks_count > silence_chunks:
                    final_result = json.loads(self.recognizer.FinalResult())
                    text = final_result.get('text', '').strip()
                    return text
                
                # Timeout after 10 seconds
                if len(frames) > (10 * self.RATE / self.CHUNK):
                    final_result = json.loads(self.recognizer.FinalResult())
                    text = final_result.get('text', '').strip()
                    return text
        
        except Exception as e:
            logging.exception(f"[STT] Error during listening: {e}")
            return ""
        
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
    
    def set_language(self, model_path: str):
        """Switch to a different Vosk model"""
        if self.mode != "vosk":
            logging.warning("[STT] Cannot change language in text input mode")
            return
        
        try:
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(True)
            logging.info(f"[STT] Switched to model: {model_path}")
        except Exception as e:
            logging.exception(f"[STT] Failed to switch model: {e}")
    
    def get_status(self) -> dict:
        """Get STT status"""
        return {
            'mode': self.mode,
            'vosk_available': VOSK_AVAILABLE,
            'model_loaded': self.model is not None,
            'fallback_active': self.mode == 'text_input'
        }


# Stage 2 will add:
# - Multiple STT engines (Whisper, Azure, etc.)
# - Real-time streaming recognition
# - Language auto-detection
# - Noise cancellation
# - Voice activity detection
