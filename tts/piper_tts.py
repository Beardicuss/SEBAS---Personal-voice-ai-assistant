import logging
import wave
import io
import threading
import queue
from pathlib import Path
from typing import Optional, Union
import numpy as np

try:
    from piper import PiperVoice
    import sounddevice as sd
    import numpy as np
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False
    logging.warning("Piper TTS not available. Install with: pip install piper-tts sounddevice")


class PiperTTS:
    """Neural TTS using Piper models with enhanced error handling."""

    def __init__(self, 
                 model_path: Optional[Union[str, Path]] = None, 
                 config_path: Optional[Union[str, Path]] = None):
        """
        Initialize Piper TTS.
        
        Args:
            model_path: Path to .onnx model file (str or Path)
            config_path: Path to .json config file (str or Path)
        """
        self.voice: Optional[PiperVoice] = None
        self._speech_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = False
        self._is_speaking = False
        self._initialization_failed = False
        self._last_error = None
        
        logging.info("[PiperTTS] Initializing...")
        
        if not PIPER_AVAILABLE:
            logging.error("[PiperTTS] piper-tts not installed!")
            logging.error("[PiperTTS] Install with: pip install piper-tts sounddevice")
            self._initialization_failed = True
            return
        
        # Convert to Path objects and set default paths
        model_path = Path(model_path) if model_path else Path("sebas/voices/piper/en_US-john-medium.onnx")
        config_path = Path(config_path) if config_path else Path("sebas/voices/piper/en_US-john-medium.onnx.json")
        
        try:
            # Check if files exist
            if not model_path.exists():
                logging.error(f"[PiperTTS] Model not found at {model_path}")
                logging.error(f"[PiperTTS] Please download Piper models to: {model_path.parent}")
                self._initialization_failed = True
                return
            
            if not config_path.exists():
                logging.error(f"[PiperTTS] Config not found at {config_path}")
                self._initialization_failed = True
                return
            
            logging.info(f"[PiperTTS] Loading model from {model_path}")
            
            # Load Piper voice - try different loading methods
            try:
                # Try with config_path parameter
                self.voice = PiperVoice.load(str(model_path), config_path=str(config_path))
                logging.info("[PiperTTS] Loaded with config_path parameter")
            except TypeError:
                try:
                    # Try without config_path parameter
                    self.voice = PiperVoice.load(str(model_path))
                    logging.info("[PiperTTS] Loaded without config_path parameter")
                except Exception as e:
                    logging.error(f"[PiperTTS] Failed to load voice: {e}")
                    self._initialization_failed = True
                    return
            
            if not self.voice:
                logging.error("[PiperTTS] Voice object is None after loading")
                self._initialization_failed = True
                return
            
            logging.info(f"[PiperTTS] ✅ Voice loaded successfully")
            logging.info(f"[PiperTTS] Sample rate: {self.voice.config.sample_rate} Hz")
            
            # Extract language information safely
            language_info = self._get_language_info()
            logging.info(f"[PiperTTS] Language: {language_info}")
            
            # Test audio device
            try:
                test_audio = np.zeros(1000, dtype=np.float32)
                sd.play(test_audio, self.voice.config.sample_rate, blocking=False)
                sd.stop()
                logging.info("[PiperTTS] ✅ Audio device test passed")
            except Exception as e:
                logging.error(f"[PiperTTS] ❌ Audio device test failed: {e}")
                logging.error("[PiperTTS] Check if audio output is available and not muted")
            
            # Test synthesis before starting worker
            try:
                logging.info("[PiperTTS] Testing synthesis...")
                test_chunks = list(self.voice.synthesize("test"))
                if not test_chunks:
                    raise Exception("Synthesis returned no audio chunks")
                logging.info(f"[PiperTTS] ✅ Synthesis test passed ({len(test_chunks)} chunks)")
            except Exception as e:
                logging.error(f"[PiperTTS] ❌ Synthesis test failed: {e}")
                self._initialization_failed = True
                self._last_error = str(e)
                return
            
            # Start worker thread
            self._start_worker_thread()
            logging.info("[PiperTTS] ✅ Initialization complete")
            
        except Exception as e:
            logging.exception(f"[PiperTTS] Initialization failed: {e}")
            self.voice = None
            self._initialization_failed = True
            self._last_error = str(e)

    def _get_language_info(self) -> str:
        """Extract language information from Piper config safely."""
        if not self.voice:
            return "Unknown"
        
        try:
            config = self.voice.config
            
            # Try different possible attributes for language
            language_attrs = ['language', 'lang', 'language_code', 'code']
            
            for attr in language_attrs:
                if hasattr(config, attr):
                    value = getattr(config, attr)
                    if value:
                        return str(value)
            
            return "en_US"  # Default assumption
            
        except Exception as e:
            logging.warning(f"[PiperTTS] Could not determine language: {e}")
            return "Unknown"
    
    def _start_worker_thread(self):
        """Start background thread to process speech queue."""
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()
        logging.info("[PiperTTS] Worker thread started")
    
    def _speech_worker(self):
        """Worker thread that processes queued speech requests."""
        logging.info("[PiperTTS] Speech worker running")
        
        while not self._stop_worker:
            try:
                text = self._speech_queue.get(timeout=0.5)
                
                if text is None:  # Poison pill
                    break
                
                logging.info(f"[PiperTTS] Worker processing: '{text[:50]}...'")
                self._do_speak(text)
                self._speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.exception(f"[PiperTTS] ❌ Error in speech worker: {e}")
                self._last_error = str(e)
                # Continue running despite error
        
        logging.info("[PiperTTS] Speech worker stopped")
    
    def _do_speak(self, text: str):
        """Synthesize and play speech using the correct Piper API."""
        if not self.voice:
            error_msg = "Voice not loaded"
            logging.error(f"[PiperTTS] {error_msg}")
            self._last_error = error_msg
            return
        
        try:
            logging.info(f"[PiperTTS] 🎤 Synthesizing: '{text}'")
            self._is_speaking = True
            
            sample_rate = self.voice.config.sample_rate
            
            # Synthesize audio chunks
            audio_chunks = []
            
            logging.info("[PiperTTS] Calling voice.synthesize()...")
            for i, audio_chunk in enumerate(self.voice.synthesize(text)):
                logging.debug(f"[PiperTTS] Received chunk {i+1}, type: {type(audio_chunk)}")
                
                if hasattr(audio_chunk, 'audio_float_array'):
                    audio_chunks.append(audio_chunk.audio_float_array)
                elif isinstance(audio_chunk, np.ndarray):
                    # Sometimes it might return ndarray directly
                    audio_chunks.append(audio_chunk)
                else:
                    logging.warning(f"[PiperTTS] Unknown chunk type: {type(audio_chunk)}")
            
            if not audio_chunks:
                error_msg = "No audio chunks received from synthesis!"
                logging.error(f"[PiperTTS] {error_msg}")
                self._last_error = error_msg
                return
            
            # Concatenate all chunks into a single array
            audio_float = np.concatenate(audio_chunks)
            logging.info(f"[PiperTTS] Generated {len(audio_float)} samples ({len(audio_float)/sample_rate:.2f}s)")
            
            # Ensure it's float32
            if audio_float.dtype != np.float32:
                audio_float = audio_float.astype(np.float32)
            
            # Validate audio data
            if len(audio_float) == 0:
                error_msg = "Audio array is empty!"
                logging.error(f"[PiperTTS] {error_msg}")
                self._last_error = error_msg
                return
            
            # Play the audio
            logging.info(f"[PiperTTS] 🔊 Playing audio at {sample_rate} Hz...")
            sd.play(audio_float, sample_rate, blocking=True)
            sd.wait()
            logging.info("[PiperTTS] ✅ Speech completed!")
            self._last_error = None  # Clear error on success
                
        except Exception as e:
            error_msg = f"Synthesis/playback failed: {e}"
            logging.exception(f"[PiperTTS] ❌ {error_msg}")
            self._last_error = error_msg
            
            # Try fallback method: write to WAV and read back
            try:
                logging.info("[PiperTTS] Trying fallback: WAV file method...")
                wav_buffer = io.BytesIO()
                
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    
                    # Generate audio chunks and write as int16
                    for audio_chunk in self.voice.synthesize(text):
                        if hasattr(audio_chunk, 'audio_float_array'):
                            # Convert float32 to int16
                            audio_int16 = (audio_chunk.audio_float_array * 32767).astype(np.int16)
                            wav_file.writeframes(audio_int16.tobytes())
                
                # Read back from buffer
                wav_buffer.seek(0)
                with wave.open(wav_buffer, 'rb') as wav_file:
                    audio_data = wav_file.readframes(wav_file.getnframes())
                
                # Convert back to float32 for playback
                audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
                audio_float = audio_int16.astype(np.float32) / 32767.0
                
                logging.info(f"[PiperTTS] Fallback: Playing {len(audio_float)} samples...")
                sd.play(audio_float, sample_rate, blocking=True)
                sd.wait()
                logging.info("[PiperTTS] ✅ Fallback method succeeded!")
                self._last_error = None  # Clear error on success
                
            except Exception as fallback_error:
                fallback_msg = f"Fallback method also failed: {fallback_error}"
                logging.exception(f"[PiperTTS] ❌ {fallback_msg}")
                self._last_error = fallback_msg
        finally:
            self._is_speaking = False
            
    def speak(self, text: str):
        """Queue text for speech (thread-safe)."""
        if self._initialization_failed:
            logging.error("[PiperTTS] Cannot speak - initialization failed")
            if self._last_error:
                logging.error(f"[PiperTTS] Last error: {self._last_error}")
            return
        
        if not self.voice:
            logging.error("[PiperTTS] Voice not available")
            return
        
        if not text or not text.strip():
            logging.warning("[PiperTTS] Empty text, skipping")
            return
        
        # Check if worker thread is alive
        if not self._worker_thread or not self._worker_thread.is_alive():
            logging.error("[PiperTTS] Worker thread is not running!")
            logging.info("[PiperTTS] Attempting to restart worker thread...")
            self._start_worker_thread()
        
        logging.info(f"[PiperTTS] Queuing text for speech (queue size: {self._speech_queue.qsize()})")
        self._speech_queue.put(text)
    
    def list_voices(self):
        """List available voices (returns current voice info)."""
        if not self.voice:
            return []
        
        class VoiceInfo:
            def __init__(self, name: str, id: str, languages: list):
                self.name = name
                self.id = id
                self.languages = languages
        
        language_info = self._get_language_info()
        
        return [VoiceInfo(
            name=f"Piper John ({language_info})",
            id="piper_john",
            languages=[language_info]
        )]
    
    def set_voice(self, voice_hint: str) -> bool:
        """Set voice by hint - provides better feedback."""
        if not self.voice:
            logging.warning("[PiperTTS] Cannot set voice, no voice loaded")
            return False
        
        logging.info(f"[PiperTTS] Voice switch requested to '{voice_hint}'")
        
        current_language = self._get_language_info().lower()
        
        if voice_hint.lower() in current_language:
            logging.info(f"[PiperTTS] Already using {current_language} voice")
            return True
        
        logging.warning(f"[PiperTTS] Cannot switch to '{voice_hint}' - only one voice model loaded")
        return False
    
    def stop(self):
        """Stop current playback."""
        try:
            sd.stop()
            logging.info("[PiperTTS] Playback stopped")
        except Exception as e:
            logging.error(f"[PiperTTS] Failed to stop playback: {e}")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
    
    def get_status(self) -> dict:
        """Get TTS status information."""
        return {
            'initialized': self.voice is not None and not self._initialization_failed,
            'speaking': self._is_speaking,
            'worker_running': self._worker_thread is not None and self._worker_thread.is_alive(),
            'queue_size': self._speech_queue.qsize(),
            'language': self._get_language_info(),
            'last_error': self._last_error
        }
    
    def __del__(self):
        """Cleanup."""
        try:
            self._stop_worker = True
            if self._speech_queue:
                try:
                    self._speech_queue.put(None)
                except:
                    pass
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2)
            self.stop()
        except:
            pass  # Ignore errors during cleanup