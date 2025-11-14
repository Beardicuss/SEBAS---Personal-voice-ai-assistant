import logging
import os
import json
import pyaudio
import wave
import tempfile

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk not installed. Install: pip install vosk")

from sebas.stt.stt_none import NoSTT


class STTManager:
    """
    Speech-to-Text Manager - Stage 1 Mk.I
    Handles microphone input and transcription.
    """
    
    def __init__(self, language_manager=None):
        self.language_manager = language_manager
        self.model = None
        self.recognizer = None
        self.engine = None  # Add explicit engine attribute
        
        # Audio configuration
        self.RATE = 16000
        self.CHUNK = 8000
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        
        self._init_vosk()

    def _init_vosk(self):
        """Initialize Vosk with default or configured model."""
        if not VOSK_AVAILABLE:
            logging.error("Vosk not available - speech recognition disabled")
            self.engine = NoSTT()
            return
        
        # Try to find a model
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
                "No Vosk model found. Download from:\n"
                "https://alphacephei.com/vosk/models\n"
                "Extract to: model/vosk-model-small-en-us-0.15"
            )
            self.engine = NoSTT()
            return
        
        try:
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(True)
            logging.info(f"STTManager: Vosk loaded from {model_path}")
        except Exception as e:
            logging.exception("Failed to load Vosk model")
            self.engine = NoSTT()

    def listen(self, timeout: int = 5) -> str:
        """
        Listen to microphone and transcribe speech.
        
        Args:
            timeout: Maximum seconds to listen (not enforced in this version)
            
        Returns:
            Transcribed text or empty string
        """
        if not self.recognizer:
            logging.warning("No STT engine available")
            return ""
        
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            # Open microphone stream
            stream = audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            logging.info("Listening... (speak now)")
            
            # Listen for speech
            frames = []
            silence_threshold = 3  # seconds of silence
            silence_chunks = int(silence_threshold * self.RATE / self.CHUNK)
            silent_chunks_count = 0
            has_speech = False
            
            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Check if we got speech
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        has_speech = True
                        logging.info(f"Recognized: {text}")
                        return text
                else:
                    # Partial result
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        has_speech = True
                        silent_chunks_count = 0  # Reset silence counter
                    else:
                        silent_chunks_count += 1
                
                # Stop after silence
                if has_speech and silent_chunks_count > silence_chunks:
                    # Get final result
                    final_result = json.loads(self.recognizer.FinalResult())
                    text = final_result.get('text', '').strip()
                    return text
                
                # Timeout after 10 seconds total
                if len(frames) > (10 * self.RATE / self.CHUNK):
                    final_result = json.loads(self.recognizer.FinalResult())
                    text = final_result.get('text', '').strip()
                    return text
                    
        except Exception as e:
            logging.exception("Error during listening")
            return ""
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()

    def set_language(self, model_path: str):
        """Switch to a different Vosk model."""
        if not VOSK_AVAILABLE:
            return
        
        try:
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.RATE)
            self.recognizer.SetWords(True)
            logging.info(f"STTManager: switched to model {model_path}")
        except Exception:
            logging.exception("Failed to switch STT model")