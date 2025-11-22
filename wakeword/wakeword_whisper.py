"""
Whisper-based Wake Word Detection
Continuous listening for wake word using Faster-Whisper
FIXED: Returns all recognized text for fuzzy matching in detector
"""

import logging
from pathlib import Path
import pyaudio
import numpy as np
import tempfile
import wave
import os
from collections import deque

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    try:
        import whisper
        STANDARD_WHISPER_AVAILABLE = True
    except ImportError:
        STANDARD_WHISPER_AVAILABLE = False
        raise RuntimeError("Neither faster-whisper nor whisper installed")


class WhisperWakeWord:
    """
    Wake word detector using Whisper for accurate transcription.
    Uses VAD (Voice Activity Detection) to minimize processing.
    Returns ALL recognized text to allow fuzzy matching in parent detector.
    """
    
    def __init__(self, keyword="master sebas", model_size="tiny"):
        """
        Initialize Whisper wake word detector.
        
        Args:
            keyword: Wake word to detect (default: "master sebas") - kept for logging
            model_size: Whisper model size - use "tiny" for wake word (fastest)
        """
        self.keyword = keyword.lower()
        self.model_size = model_size
        
        logging.info(f"[WhisperWakeWord] Initializing with model '{model_size}'...")
        
        # Load Whisper model
        if FASTER_WHISPER_AVAILABLE:
            logging.info("[WhisperWakeWord] Using faster-whisper")
            self.model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8"
            )
            self.use_faster = True
        elif STANDARD_WHISPER_AVAILABLE:
            logging.info("[WhisperWakeWord] Using standard whisper")
            self.model = whisper.load_model(model_size, device="cpu")
            self.use_faster = False
        else:
            raise RuntimeError("No Whisper implementation available")
        
        # Audio configuration
        self.RATE = 16000
        self.CHUNK = 4000  # Match Vosk's chunk size for consistency
        self.CHANNELS = 1
        self.FORMAT = pyaudio.paInt16
        
        # VAD settings
        self.SPEECH_THRESHOLD = 500  # Audio level threshold for speech
        self.MIN_SPEECH_CHUNKS = 3   # Minimum chunks with speech before processing
        self.MAX_SILENCE_CHUNKS = 8  # Max silence before processing (2 seconds)
        self.BUFFER_SIZE = 40        # Keep last 10 seconds of audio (40 chunks * 0.25s)
        
        # State tracking
        self.audio_buffer = deque(maxlen=self.BUFFER_SIZE)
        self.last_detection_text = ""
        self.silence_counter = 0
        self.speech_chunks = 0
        self.total_checks = 0
        self.audio_level_checks = 0
        
        # Setup PyAudio
        self.pa = pyaudio.PyAudio()
        
        # List audio devices
        logging.info("[WhisperWakeWord] Available audio input devices:")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            try:
                max_in = int(info.get('maxInputChannels', 0))
            except (TypeError, ValueError):
                max_in = 0
            
            if max_in > 0:
                logging.info(f"  [{i}] {info['name']} - {max_in} channels")
        
        # Open audio stream
        try:
            self.stream = self.pa.open(
                rate=self.RATE,
                channels=self.CHANNELS,
                format=self.FORMAT,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            logging.info("[WhisperWakeWord] Audio stream opened successfully")
        except Exception as e:
            logging.error(f"[WhisperWakeWord] Failed to open audio stream: {e}")
            raise
        
        logging.info(f"[WhisperWakeWord] Ready! Listening for '{keyword}'...")
        logging.info("[WhisperWakeWord] Note: Fuzzy matching will be handled by parent detector")
        logging.info("[WhisperWakeWord] Speak into your microphone to test...")
    
    def detect(self):
        """
        Check if speech is detected and return recognized text.
        
        IMPORTANT: This method NO LONGER checks for wake word match.
        It returns ALL recognized text to the parent detector for fuzzy matching.
        
        Returns:
            dict with 'detected' (bool) and 'text' (str) for any recognized speech,
            False if no speech detected
        """
        try:
            # Read audio chunk
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            self.total_checks += 1
            
            # Calculate audio level (VAD)
            audio_array = np.frombuffer(data, dtype=np.int16)
            audio_level = np.abs(audio_array).mean()
            
            # Periodic audio level logging (every 50 checks = ~12.5 seconds)
            if self.total_checks % 50 == 0:
                self.audio_level_checks += 1
                logging.info(
                    f"[WhisperWakeWord] Audio level check #{self.audio_level_checks}: "
                    f"{audio_level:.1f} (threshold ~{self.SPEECH_THRESHOLD} for speech)"
                )
                if audio_level < 100:
                    logging.warning("[WhisperWakeWord] Audio level very low - check microphone!")
            
            # Voice Activity Detection
            if audio_level > self.SPEECH_THRESHOLD:
                self.speech_chunks += 1
                self.silence_counter = 0
                self.audio_buffer.append(data)
                
                # Log speech detection less frequently
                if self.speech_chunks == 1 or self.speech_chunks % 10 == 0:
                    logging.debug(f"[WhisperWakeWord] Speech detected ({self.speech_chunks} chunks)")
            else:
                self.silence_counter += 1
                
                # Still buffer audio during short pauses
                if self.speech_chunks > 0 and self.silence_counter < self.MAX_SILENCE_CHUNKS:
                    self.audio_buffer.append(data)
            
            # Process when we have enough speech and then silence
            if (self.speech_chunks >= self.MIN_SPEECH_CHUNKS and 
                self.silence_counter >= self.MAX_SILENCE_CHUNKS):
                
                logging.info(f"[WhisperWakeWord] Processing audio ({self.speech_chunks} speech chunks)...")
                
                # Transcribe buffered audio
                text = self._transcribe_buffer()
                
                # Reset state
                self.audio_buffer.clear()
                self.speech_chunks = 0
                self.silence_counter = 0
                
                if text:
                    logging.info(f"[WhisperWakeWord] 🎤 RECOGNIZED: '{text}'")
                    
                    # CHANGED: Return ALL recognized text for fuzzy matching
                    # Don't check for exact keyword match here - let the parent detector handle it
                    if text != self.last_detection_text:
                        logging.info(f"[WhisperWakeWord] → Sending to fuzzy matcher: '{text}'")
                        self.last_detection_text = text
                        # Return dict with detected flag and full text
                        return {'detected': True, 'text': text}
                    else:
                        logging.debug("[WhisperWakeWord] Duplicate detection, ignoring")
                    
                    self.last_detection_text = ""
            
            # Reset after long silence
            if self.silence_counter > self.MAX_SILENCE_CHUNKS * 3:
                if self.speech_chunks > 0:
                    logging.debug("[WhisperWakeWord] Long silence, resetting buffer")
                self.audio_buffer.clear()
                self.speech_chunks = 0
                self.last_detection_text = ""
            
            return False
            
        except Exception as e:
            logging.error(f"[WhisperWakeWord] Detection error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def _transcribe_buffer(self) -> str:
        """
        Transcribe buffered audio using Whisper.
        
        Returns:
            Transcribed text or empty string
        """
        if not self.audio_buffer:
            return ""
        
        temp_path = None
        try:
            # Combine audio chunks
            pcm_bytes = b''.join(self.audio_buffer)
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Write PCM to WAV
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.RATE)
                wf.writeframes(pcm_bytes)
            
            # Transcribe with Whisper
            if self.use_faster:
                # Faster-Whisper
                segments, info = self.model.transcribe(
                    temp_path,
                    language="en",
                    beam_size=1,  # Faster for wake word
                    vad_filter=False  # We already did VAD
                )
                text = " ".join([segment.text for segment in segments]).strip()
            else:
                # Standard Whisper
                result = self.model.transcribe(
                    temp_path,
                    language="en"
                )
                text = result.get('text', '').strip()
            
            return text
            
        except Exception as e:
            logging.error(f"[WhisperWakeWord] Transcription failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return ""
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
    
    def cleanup(self):
        """Clean up audio resources"""
        try:
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'pa') and self.pa:
                self.pa.terminate()
            logging.info("[WhisperWakeWord] Cleaned up")
        except Exception as e:
            logging.error(f"[WhisperWakeWord] Cleanup error: {e}")

    def pause(self):
        try:
            if self.stream and self.stream.is_active():
                self.stream.stop_stream()
                logging.info("[WakeWord] Stream paused")
        except Exception as e:
            logging.error(f"[WakeWord] Pause failed: {e}")

    def resume(self):
        try:
            if self.stream is None or self.stream.is_stopped():
                self.stream = self.pa.open(
                    rate=self.RATE,
                    channels=self.CHANNELS,
                    format=self.FORMAT,
                    input=True,
                    frames_per_buffer=self.CHUNK
                )
                logging.info("[WakeWord] Stream resumed")
        except Exception as e:
            logging.error(f"[WakeWord] Resume failed: {e}")
