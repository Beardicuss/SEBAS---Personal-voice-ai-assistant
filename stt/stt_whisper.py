"""
Whisper STT Engine - Stage 1 Mk.I
Thin wrapper for Whisper (matches VoskRecognizer pattern)
"""

import logging
import tempfile
import os
import wave

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("[Whisper] Not installed. Run: pip install openai-whisper")


class WhisperRecognizer:
    """
    Thin wrapper for Whisper engine.
    Matches VoskRecognizer API pattern.
    """
    
    def __init__(self, model_name: str = "base", device: str = "cpu"):
        """
        Initialize Whisper.
        
        Args:
            model_name: Model size (tiny, base, small, medium, large)
            device: 'cpu' or 'cuda'
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not installed")
        
        self.model_name = model_name
        self.device = device
        self.language = "en"  # Default language
        
        logging.info(f"[Whisper] Loading {model_name} model...")
        try:
            self.model = whisper.load_model(model_name, device=device)
            logging.info(f"[Whisper] ✅ {model_name} loaded on {device}")
        except Exception as e:
            logging.exception("[Whisper] Failed to load model")
            raise
    
    def set_language(self, language_code: str):
        """
        Set target language.
        
        Args:
            language_code: ISO language code (en, ru, ja, ka, etc.)
        """
        self.language = language_code
        logging.info(f"[Whisper] Language set to: {language_code}")
    
    def recognize_audio_file(self, audio_path: str) -> str:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to WAV file
            
        Returns:
            Transcribed text
        """
        try:
            result = self.model.transcribe(
                audio_path,
                language=self.language,
                fp16=False,  # CPU compatibility
                verbose=False
            )
            text = result.get('text', '').strip()
            logging.debug(f"[Whisper] Transcribed: {text}")
            return text
        except Exception as e:
            logging.exception("[Whisper] Transcription failed")
            return ""
    
    def recognize_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Process PCM audio bytes → text.
        
        Args:
            pcm_bytes: Raw PCM audio data
            sample_rate: Sample rate (default 16000)
            
        Returns:
            Transcribed text
        """
        temp_path = None
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Write PCM to WAV
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_bytes)
            
            # Transcribe
            text = self.recognize_audio_file(temp_path)
            return text
            
        except Exception as e:
            logging.exception("[Whisper] PCM recognition failed")
            return ""
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass


# ----------------------------------------------------------------------
# Faster-Whisper implementation (optional, 4x faster)
# ----------------------------------------------------------------------

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class FasterWhisperRecognizer:
    """
    Faster-Whisper implementation (4x speedup).
    Install: pip install faster-whisper
    """
    
    def __init__(self, model_name: str = "base", device: str = "cpu"):
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError("faster-whisper not installed")
        
        self.model_name = model_name
        self.device = device
        self.language = "en"
        
        logging.info(f"[FasterWhisper] Loading {model_name} model...")
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type="int8" if device == "cpu" else "float16"
        )
        logging.info(f"[FasterWhisper] ✅ {model_name} loaded")
    
    def set_language(self, language_code: str):
        """Set target language."""
        self.language = language_code
        logging.info(f"[FasterWhisper] Language set to: {language_code}")
    
    def recognize_audio_file(self, audio_path: str) -> str:
        """Transcribe audio file."""
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=self.language,
                beam_size=5,
                vad_filter=True  # Built-in VAD
            )
            text = " ".join([segment.text for segment in segments]).strip()
            logging.debug(f"[FasterWhisper] Transcribed: {text}")
            return text
        except Exception as e:
            logging.exception("[FasterWhisper] Transcription failed")
            return ""
    
    def recognize_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """Process PCM → text."""
        temp_path = None
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Write PCM to WAV
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_bytes)
            
            # Transcribe
            text = self.recognize_audio_file(temp_path)
            return text
            
        except Exception as e:
            logging.exception("[FasterWhisper] PCM recognition failed")
            return ""
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass