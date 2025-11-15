import logging
import wave
import io
import threading
import queue
from pathlib import Path
from typing import Optional, Union

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
        
        logging.info("[PiperTTS] Initializing...")
        
        if not PIPER_AVAILABLE:
            logging.error("[PiperTTS] piper-tts not installed!")
            logging.error("[PiperTTS] Install with: pip install piper-tts sounddevice")
            return
        
        # Convert to Path objects and set default paths
        model_path = Path(model_path) if model_path else Path("sebas/voices/piper/en_US-lessac-medium.onnx")
        config_path = Path(config_path) if config_path else Path("sebas/voices/piper/en_US-lessac-medium.json")
        
        try:
            # Check if files exist
            if not model_path.exists():
                logging.error(f"[PiperTTS] Model not found at {model_path}")
                logging.error(f"[PiperTTS] Please download Piper models to: {model_path.parent}")
                return
            
            if not config_path.exists():
                logging.error(f"[PiperTTS] Config not found at {config_path}")
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
                    return
            
            if not self.voice:
                logging.error("[PiperTTS] Voice object is None after loading")
                return
            
            logging.info(f"[PiperTTS] Voice loaded successfully")
            logging.info(f"[PiperTTS] Sample rate: {self.voice.config.sample_rate} Hz")
            
            # Log available methods for debugging
            methods = [m for m in dir(self.voice) if not m.startswith('_') and callable(getattr(self.voice, m))]
            logging.info(f"[PiperTTS] Available methods: {', '.join(methods)}")
            
            # Extract language information safely
            language_info = self._get_language_info()
            logging.info(f"[PiperTTS] Language: {language_info}")
            
            # Test audio device
            try:
                test_audio = np.zeros(1000, dtype=np.float32)
                sd.play(test_audio, self.voice.config.sample_rate, blocking=False)
                sd.stop()
                logging.info("[PiperTTS] Audio device test passed")
            except Exception as e:
                logging.error(f"[PiperTTS] Audio device test failed: {e}")
                logging.error("[PiperTTS] Check if audio output is available and not muted")
            
            # Start worker thread
            self._start_worker_thread()
            
        except Exception as e:
            logging.exception(f"[PiperTTS] Initialization failed: {e}")
            self.voice = None

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
                
                self._do_speak(text)
                self._speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception:
                logging.exception("[PiperTTS] Error in speech worker")
        
        logging.info("[PiperTTS] Speech worker stopped")
    
    def _do_speak(self, text: str):
        """Synthesize and play speech using multiple fallback methods."""
        if not self.voice:
            logging.error("[PiperTTS] Voice not loaded")
            return
        
        try:
            logging.info(f"[PiperTTS] Synthesizing: '{text}'")
            self._is_speaking = True
            
            sample_rate = self.voice.config.sample_rate
            audio_np = None
            
            # ==== METHOD 1: Direct generator with AudioChunk objects (newest API) ====
            if audio_np is None:
                try:
                    logging.info("[PiperTTS] Method 1: Trying direct generator...")
                    result = self.voice.synthesize(text)
                    
                    # Check if result is iterable (generator)
                    if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                        audio_chunks = []
                        for chunk in result:
                            # Handle AudioChunk objects (modern Piper API)
                            if hasattr(chunk, 'audio_float_array'):
                                # Extract float32 audio data directly
                                audio_chunks.append(chunk.audio_float_array)
                                logging.debug(f"[PiperTTS] Got AudioChunk with {len(chunk.audio_float_array)} samples")
                            # Handle raw numpy arrays
                            elif isinstance(chunk, np.ndarray):
                                audio_chunks.append(chunk)
                            # Handle raw bytes
                            elif isinstance(chunk, bytes):
                                chunk_array = np.frombuffer(chunk, dtype=np.int16)
                                audio_chunks.append(chunk_array)
                        
                        if audio_chunks:
                            # Concatenate all chunks
                            audio_float = np.concatenate(audio_chunks)
                            
                            # Check if already float or needs conversion
                            if audio_float.dtype == np.float32:
                                logging.info(f"[PiperTTS] Method 1 SUCCESS: {len(audio_float)} float32 samples")
                            else:
                                # Convert int16 to float32
                                audio_float = audio_float.astype(np.float32) / 32768.0
                                logging.info(f"[PiperTTS] Method 1 SUCCESS: {len(audio_float)} samples (converted)")
                            
                            # Store as audio_np for playback (will be converted again below, so convert back)
                            audio_np = (audio_float * 32768.0).astype(np.int16)
                except Exception as e:
                    logging.debug(f"[PiperTTS] Method 1 failed: {e}")
                    import traceback
                    logging.debug(traceback.format_exc())
            
            # ==== METHOD 2: Write to WAV file directly ====
            if audio_np is None:
                try:
                    logging.info("[PiperTTS] Method 2: Trying direct file write...")
                    temp_file = Path("temp_piper_output.wav")
                    
                    # Use synthesize with file path as string
                    with wave.open(str(temp_file), 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        
                        # Try passing the wave file object
                        try:
                            self.voice.synthesize(text, wav_file)
                        except TypeError:
                            # Maybe it wants just the filename
                            pass
                    
                    # If file was created and has data, read it
                    if temp_file.exists() and temp_file.stat().st_size > 44:
                        with wave.open(str(temp_file), 'rb') as wav_file:
                            audio_data = wav_file.readframes(wav_file.getnframes())
                        
                        audio_np = np.frombuffer(audio_data, dtype=np.int16)
                        logging.info(f"[PiperTTS] Method 2 SUCCESS: {len(audio_np)} samples")
                        
                        # Clean up
                        try:
                            temp_file.unlink()
                        except:
                            pass
                    else:
                        raise ValueError("File synthesis produced no data")
                        
                except Exception as e:
                    logging.debug(f"[PiperTTS] Method 2 failed: {e}")
            
            # ==== METHOD 3: Use PiperVoice internal synthesize to file method ====
            if audio_np is None:
                try:
                    logging.info("[PiperTTS] Method 3: Trying synthesize_to_file if available...")
                    temp_file = Path("temp_piper_output.wav")
                    
                    if hasattr(self.voice, 'synthesize_to_file'):
                        self.voice.synthesize_to_file(text, str(temp_file))
                        
                        if temp_file.exists() and temp_file.stat().st_size > 44:
                            with wave.open(str(temp_file), 'rb') as wav_file:
                                audio_data = wav_file.readframes(wav_file.getnframes())
                            
                            audio_np = np.frombuffer(audio_data, dtype=np.int16)
                            logging.info(f"[PiperTTS] Method 3 SUCCESS: {len(audio_np)} samples")
                            
                            try:
                                temp_file.unlink()
                            except:
                                pass
                    else:
                        raise AttributeError("synthesize_to_file not available")
                        
                except Exception as e:
                    logging.debug(f"[PiperTTS] Method 3 failed: {e}")
            
            # ==== METHOD 4: Try using onnx directly (last resort) ====
            if audio_np is None:
                try:
                    logging.info("[PiperTTS] Method 4: Trying direct ONNX inference...")
                    
                    # This is a more direct approach using Piper's internal methods
                    if hasattr(self.voice, 'phonemize'):
                        phonemes = self.voice.phonemize(text)
                        if hasattr(self.voice, 'phonemes_to_ids'):
                            phoneme_ids = self.voice.phonemes_to_ids(phonemes)
                            if hasattr(self.voice, 'synthesize_ids_to_audio'):
                                audio_np = self.voice.synthesize_ids_to_audio(phoneme_ids)
                                logging.info(f"[PiperTTS] Method 4 SUCCESS: {len(audio_np)} samples")
                    else:
                        raise AttributeError("Direct ONNX methods not available")
                        
                except Exception as e:
                    logging.debug(f"[PiperTTS] Method 4 failed: {e}")
            
            # ==== FINAL CHECK ====
            if audio_np is None or len(audio_np) == 0:
                logging.error("[PiperTTS] ❌ ALL METHODS FAILED - No audio produced!")
                logging.error("[PiperTTS] This may indicate:")
                logging.error("[PiperTTS]   1. Incompatible Piper version")
                logging.error("[PiperTTS]   2. Corrupted model files")
                logging.error("[PiperTTS]   3. Missing dependencies")
                logging.error("[PiperTTS] Try: pip install --upgrade piper-tts")
                return
            
            # Convert to float32 for playback if not already
            if audio_np.dtype == np.float32:
                audio_float = audio_np
            else:
                audio_float = audio_np.astype(np.float32) / 32768.0
            
            # Play the audio
            logging.info(f"[PiperTTS] ✓ Playing {len(audio_float)} samples at {sample_rate} Hz")
            sd.play(audio_float, sample_rate, blocking=True)
            sd.wait()
            logging.info("[PiperTTS] ✓ Speech completed successfully!")
                
        except Exception as e:
            logging.exception(f"[PiperTTS] ❌ Failed to synthesize/play: {e}")
        finally:
            self._is_speaking = False
            
    def speak(self, text: str):
        """Queue text for speech (thread-safe)."""
        if not self.voice:
            logging.error("[PiperTTS] Voice not available")
            return
        
        if not text or not text.strip():
            logging.warning("[PiperTTS] Empty text, skipping")
            return
        
        logging.info(f"[PiperTTS] Queuing text: '{text}'")
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
            name=f"Piper {language_info}",
            id="piper_default",
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
            'initialized': self.voice is not None,
            'speaking': self._is_speaking,
            'worker_running': self._worker_thread is not None and self._worker_thread.is_alive(),
            'queue_size': self._speech_queue.qsize(),
            'language': self._get_language_info()
        }
    
    def __del__(self):
        """Cleanup."""
        try:
            logging.info("[PiperTTS] Cleaning up...")
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