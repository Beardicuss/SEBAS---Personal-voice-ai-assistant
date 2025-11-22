"""
STT Manager - Stage 1 Mk.I (Whisper Edition)
Multi-engine support: Whisper → Vosk → Text fallback
"""

import logging
import os
import json
from pathlib import Path
from typing import Optional, Any

# Try Whisper (preferred)
WhisperEngine = None
WHISPER_TYPE = None

try:
    from sebas.stt.stt_whisper import FasterWhisperRecognizer
    WhisperEngine = FasterWhisperRecognizer
    WHISPER_TYPE = "faster"
    logging.debug("[STT] faster-whisper available")
except ImportError:
    try:
        from sebas.stt.stt_whisper import WhisperRecognizer
        WhisperEngine = WhisperRecognizer
        WHISPER_TYPE = "standard"
        logging.debug("[STT] standard whisper available")
    except ImportError:
        logging.debug("[STT] No Whisper variant available")

# Try Vosk (fallback)
try:
    import vosk
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None
    pyaudio = None

from sebas.stt.stt_none import NoSTT


class STTManager:
    """
    Speech-to-Text Manager with multi-engine support.
    
    Priority:
    1. Whisper (best accuracy)
    2. Vosk (offline, lightweight)
    3. Text input (testing/fallback)
    """
    
    def __init__(self, language_manager=None, engine: str = "auto", model_size: str = "base"):
        """
        Initialize STT Manager.
        
        Args:
            language_manager: Optional LanguageManager instance
            engine: 'whisper', 'vosk', 'text', or 'auto' (default)
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.language_manager = language_manager
        self.requested_engine = engine
        self.model_size = model_size
        
        # State
        self.recognizer: Optional[Any] = None
        self.mode = "none"
        self.current_language = "en"
        
        # Audio configuration
        self.RATE = 16000
        self.CHUNK = 8000
        self.FORMAT: Optional[int] = None
        self.CHANNELS = 1
        self.pa_format: Optional[int] = None
        
        # Initialize best available engine
        self._init_engine()
    
    def _init_engine(self) -> None:
        """Initialize best available STT engine."""
        
        # FORCED ENGINE MODE
        if self.requested_engine == "whisper":
            if self._init_whisper():
                return
            logging.error("[STT] Whisper requested but not available")
            self._init_text_fallback()
            return
            
        elif self.requested_engine == "vosk":
            if self._init_vosk():
                return
            logging.error("[STT] Vosk requested but not available")
            self._init_text_fallback()
            return
            
        elif self.requested_engine == "text":
            self._init_text_fallback()
            return
        
        # AUTO MODE (try engines in priority order)
        if self._init_whisper():
            return
        
        logging.warning("[STT] Whisper not available, trying Vosk...")
        if self._init_vosk():
            return
        
        logging.warning("[STT] No audio engines available, using text input")
        self._init_text_fallback()
    
    def _init_whisper(self) -> bool:
        """Initialize Whisper engine."""
        if not WhisperEngine:
            logging.debug("[STT] Whisper not installed")
            return False
        
        try:
            if pyaudio is None:
                logging.error("[STT] PyAudio not available")
                return False
                
            logging.info(f"[STT] Initializing Whisper ({WHISPER_TYPE}, {self.model_size})...")
            self.recognizer = WhisperEngine(model_name=self.model_size, device="cpu")
            self.mode = f"whisper-{WHISPER_TYPE}"
            
            # Set up PyAudio format for recording
            self.FORMAT = pyaudio.paInt16
            self.pa_format = pyaudio.paInt16
            
            logging.info(f"[STT] ✅ Whisper ready: {WHISPER_TYPE} - {self.model_size}")
            return True
            
        except Exception as e:
            logging.error(f"[STT] Whisper initialization failed: {e}")
            logging.debug("Full traceback:", exc_info=True)
            return False
    
    def _init_vosk(self) -> bool:
        """Initialize Vosk engine."""
        if not VOSK_AVAILABLE or vosk is None or pyaudio is None:
            logging.debug("[STT] Vosk not installed")
            return False
        
        base_dir = Path(__file__).resolve().parent.parent
        
        model_paths = [
            base_dir / "model" / "vosk-model-small-en-us-0.15",
            base_dir / "model" / "vosk-model-small-en-us",
            Path(os.path.expanduser("~/vosk-model-small-en-us-0.15")),
            base_dir / "model" / "vosk-model-small-ru-0.22",
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = str(path)
                break
        
        if not model_path:
            logging.warning(
                "[STT] No Vosk model found\n"
                "      Download from: https://alphacephei.com/vosk/models\n"
                "      Extract to: model/vosk-model-small-en-us-0.15"
            )
            return False
        
        try:
            self.FORMAT = pyaudio.paInt16
            self.pa_format = pyaudio.paInt16
            
            model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(model, self.RATE)
            
            # Type-safe SetWords call
            if hasattr(self.recognizer, 'SetWords'):
                self.recognizer.SetWords(True)
            
            self.mode = "vosk"
            logging.info(f"[STT] ✅ Vosk loaded from {model_path}")
            return True
            
        except Exception as e:
            logging.error(f"[STT] Vosk initialization failed: {e}")
            logging.debug("Full traceback:", exc_info=True)
            return False
    
    def _init_text_fallback(self) -> bool:
        """Initialize text input fallback."""
        self.mode = "text_input"
        self.recognizer = NoSTT()
        logging.info("[STT] ✅ Text input mode active")
        return True
    
    def listen(self, timeout: int = 5) -> str:
        """
        Listen to user input.
        
        Args:
            timeout: Maximum seconds to listen
            
        Returns:
            Transcribed text or empty string
        """
        
        # TEXT INPUT FALLBACK
        if self.mode == "text_input":
            logging.info("[STT] Text input mode - type your command:")
            try:
                text = input("You: ").strip()
                if text:
                    logging.info(f"[STT] Received: {text}")
                return text
            except (EOFError, KeyboardInterrupt):
                return ""
        
        # WHISPER MODE
        if self.mode.startswith("whisper"):
            return self._listen_whisper(timeout)
        
        # VOSK MODE
        if self.mode == "vosk":
            return self._listen_vosk(timeout)
        
        logging.error("[STT] No engine available")
        return ""
    
    def _listen_whisper(self, timeout: int) -> str:
        """Listen using Whisper engine."""
        if pyaudio is None or self.recognizer is None or self.pa_format is None:
            logging.error("[STT] Whisper not properly initialized")
            return ""
            
        import numpy as np
        
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = audio.open(
                format=self.pa_format,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            logging.info("[STT] 🎤 Listening... (speak now)")
            
            frames = []
            silence_threshold = 3  # seconds
            silence_chunks = int(silence_threshold * self.RATE / self.CHUNK)
            silent_chunks_count = 0
            has_speech = False
            max_chunks = int(10 * self.RATE / self.CHUNK)  # 10 sec max
            
            for _ in range(max_chunks):
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Simple VAD (voice activity detection)
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                if volume > 500:  # Speech detected
                    has_speech = True
                    silent_chunks_count = 0
                else:
                    silent_chunks_count += 1
                
                # Stop after silence
                if has_speech and silent_chunks_count > silence_chunks:
                    break
            
            if not has_speech:
                logging.warning("[STT] No speech detected")
                return ""
            
            # Convert frames to PCM bytes
            pcm_bytes = b''.join(frames)
            
            # Transcribe with Whisper
            logging.info("[STT] 🧠 Transcribing...")
            text = self.recognizer.recognize_pcm(pcm_bytes, self.RATE)
            
            if text:
                logging.info(f"[STT] ✅ Recognized: {text}")
            else:
                logging.warning("[STT] Empty transcription")
            
            return text
            
        except Exception as e:
            logging.error(f"[STT] Whisper listening failed: {e}")
            logging.debug("Full traceback:", exc_info=True)
            return ""
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
    
    def _listen_vosk(self, timeout: int) -> str:
        """Listen using Vosk engine."""
        if pyaudio is None or self.recognizer is None or self.pa_format is None:
            logging.error("[STT] Vosk not properly initialized")
            return ""
        
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            stream = audio.open(
                format=self.pa_format,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            logging.info("[STT] 🎤 Listening... (speak now)")
            
            frames = []
            silence_threshold = 3
            silence_chunks = int(silence_threshold * self.RATE / self.CHUNK)
            silent_chunks_count = 0
            has_speech = False
            max_chunks = int(10 * self.RATE / self.CHUNK)
            
            for _ in range(max_chunks):
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        has_speech = True
                        logging.info(f"[STT] ✅ Recognized: {text}")
                        return text
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        has_speech = True
                        silent_chunks_count = 0
                    else:
                        silent_chunks_count += 1
                
                if has_speech and silent_chunks_count > silence_chunks:
                    final = json.loads(self.recognizer.FinalResult())
                    text = final.get('text', '').strip()
                    return text
            
            # Timeout
            final = json.loads(self.recognizer.FinalResult())
            text = final.get('text', '').strip()
            return text
            
        except Exception as e:
            logging.error(f"[STT] Vosk listening failed: {e}")
            logging.debug("Full traceback:", exc_info=True)
            return ""
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
    
    def set_language(self, language_code: str) -> None:
        """Set target language."""
        self.current_language = language_code
        
        if self.recognizer and hasattr(self.recognizer, 'set_language'):
            self.recognizer.set_language(language_code)
        
        logging.info(f"[STT] Language set to: {language_code}")
    
    def get_status(self) -> dict:
        """Get STT status."""
        return {
            'mode': self.mode,
            'whisper_available': WhisperEngine is not None,
            'vosk_available': VOSK_AVAILABLE,
            'language': self.current_language,
            'model_size': self.model_size if self.mode.startswith('whisper') else None
        }
    
    def switch_engine(self, engine: str) -> None:
        """Hot-swap STT engine."""
        logging.info(f"[STT] Switching from {self.mode} to {engine}...")
        self.requested_engine = engine
        self._init_engine()