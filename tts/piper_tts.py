import logging
import wave
import io
import threading
import queue
import time
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
                 config_path: Optional[Union[str, Path]] = None,
                 audio_device: Optional[int] = None,
                 volume: float = 1.0):
        """
        Initialize Piper TTS.
        
        Args:
            model_path: Path to .onnx model file (str or Path)
            config_path: Path to .json config file (str or Path)
            audio_device: Specific audio device ID to use
            volume: Audio volume (0.0 to 1.0)
        """
        self.voice: Optional[PiperVoice] = None
        self._speech_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = False
        self._is_speaking = False
        self._paused = False
        self.audio_device = audio_device
        self.volume = max(0.0, min(1.0, volume))  # Clamp between 0-1
        
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
            
            # Extract language information safely
            language_info = self._get_language_info()
            logging.info(f"[PiperTTS] Language: {language_info}")
            
            # Test audio device
            try:
                test_audio = np.zeros(1000, dtype=np.float32)
                self._play_audio_with_volume(test_audio, self.voice.config.sample_rate)
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
                item = self._speech_queue.get(timeout=0.5)
                
                if item is None:  # Poison pill
                    break
                
                text, stream = item
                if stream:
                    self._stream_speech(text)
                else:
                    self._do_speak(text)
                self._speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception:
                logging.exception("[PiperTTS] Error in speech worker")
        
        logging.info("[PiperTTS] Speech worker stopped")
    
    def _play_audio_with_volume(self, audio_data: np.ndarray, sample_rate: int):
        """Play audio with volume adjustment."""
        if self.volume != 1.0:
            audio_data = audio_data * self.volume
        
        if self.audio_device is not None:
            sd.play(audio_data, sample_rate, device=self.audio_device, blocking=True)
        else:
            sd.play(audio_data, sample_rate, blocking=True)
        sd.wait()
    
    def _do_speak(self, text: str):
        """Synthesize and play speech using the correct Piper API."""
        if not self.voice:
            logging.error("[PiperTTS] Voice not loaded")
            return
        
        try:
            logging.info(f"[PiperTTS] Synthesizing: '{text}'")
            self._is_speaking = True
            self._paused = False
            
            sample_rate = self.voice.config.sample_rate
            
            # The correct way: synthesize() returns a generator of AudioChunk objects
            # Each AudioChunk has a .audio_float_array attribute (numpy array of float32)
            logging.info("[PiperTTS] Calling synthesize()...")
            audio_chunks = []
            
            for audio_chunk in self.voice.synthesize(text):
                if self._paused:
                    sd.stop()
                    return
                # audio_chunk is an AudioChunk object with audio_float_array attribute
                if hasattr(audio_chunk, 'audio_float_array'):
                    audio_chunks.append(audio_chunk.audio_float_array)
                    logging.debug(f"[PiperTTS] Got chunk with {len(audio_chunk.audio_float_array)} samples")
                else:
                    logging.warning(f"[PiperTTS] Unknown chunk type: {type(audio_chunk)}")
            
            if not audio_chunks:
                logging.error("[PiperTTS] No audio chunks received!")
                return
            
            # Concatenate all chunks into a single array
            audio_float = np.concatenate(audio_chunks)
            logging.info(f"[PiperTTS] ✓ Generated {len(audio_float)} samples")
            
            # Ensure it's float32
            if audio_float.dtype != np.float32:
                audio_float = audio_float.astype(np.float32)
            
            # Play the audio with volume control
            logging.info(f"[PiperTTS] Playing audio at {sample_rate} Hz...")
            self._play_audio_with_volume(audio_float, sample_rate)
            logging.info("[PiperTTS] ✓ Speech completed successfully!")
                
        except Exception as e:
            logging.exception(f"[PiperTTS] ❌ Failed to synthesize/play: {e}")
            
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
                self._play_audio_with_volume(audio_float, sample_rate)
                logging.info("[PiperTTS] ✓ Fallback method succeeded!")
                
            except Exception as fallback_error:
                logging.exception(f"[PiperTTS] ❌ Fallback method also failed: {fallback_error}")
        finally:
            self._is_speaking = False
            self._paused = False

    def _stream_speech(self, text: str):
        """Stream audio chunks for lower latency."""
        if not self.voice:
            return
        
        try:
            self._is_speaking = True
            self._paused = False
            sample_rate = self.voice.config.sample_rate
            
            # Stream chunks directly to audio device
            stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=1024,
                device=self.audio_device
            )
            stream.start()
            
            for audio_chunk in self.voice.synthesize(text):
                if self._paused:
                    stream.stop()
                    stream.close()
                    return
                if hasattr(audio_chunk, 'audio_float_array'):
                    chunk_data = audio_chunk.audio_float_array.astype(np.float32)
                    if self.volume != 1.0:
                        chunk_data = chunk_data * self.volume
                    stream.write(chunk_data)
            
            stream.stop()
            stream.close()
            
        except Exception as e:
            logging.exception(f"[PiperTTS] Streaming failed: {e}")
        finally:
            self._is_speaking = False
            self._paused = False
            
    def speak(self, text: str, stream: bool = False):
        """Queue text for speech (thread-safe).
        
        Args:
            text: Text to speak
            stream: If True, use streaming mode for lower latency
        """
        if not self.voice:
            logging.error("[PiperTTS] Voice not available")
            return
        
        if not text or not text.strip():
            logging.warning("[PiperTTS] Empty text, skipping")
            return
        
        logging.info(f"[PiperTTS] Queuing text: '{text}'")
        self._speech_queue.put((text, stream))
    
    def preload_voice(self, model_path: Union[str, Path], config_path: Union[str, Path]) -> bool:
        """Preload a different voice model for quick switching."""
        try:
            new_voice = PiperVoice.load(str(model_path), config_path=str(config_path))
            # Stop current playback and clear queue
            self.stop()
            self._speech_queue.queue.clear()
            self.voice = new_voice
            logging.info(f"[PiperTTS] Successfully preloaded voice from {model_path}")
            return True
        except Exception as e:
            logging.error(f"[PiperTTS] Failed to preload voice: {e}")
            return False
    
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
    
    def pause(self):
        """Pause current speech."""
        try:
            self._paused = True
            sd.stop()
            logging.info("[PiperTTS] Speech paused")
        except Exception as e:
            logging.error(f"[PiperTTS] Failed to pause: {e}")

    def resume(self):
        """Resume paused speech."""
        # Note: For simplicity, we just stop paused speech
        # In a more complex implementation, you'd need to buffer the audio
        logging.warning("[PiperTTS] Resume not fully implemented - stopping paused speech")
        self._paused = False

    def wait_until_done(self, timeout: Optional[float] = None):
        """Wait until all queued speech is completed."""
        try:
            if timeout:
                # Implement timeout by checking queue periodically
                start_time = time.time()
                while not self._speech_queue.empty() or self._is_speaking:
                    if time.time() - start_time > timeout:
                        logging.warning("[PiperTTS] Wait timeout reached")
                        break
                    time.sleep(0.1)
            else:
                # Wait indefinitely
                self._speech_queue.join()
                while self._is_speaking:
                    time.sleep(0.1)
        except Exception as e:
            logging.error(f"[PiperTTS] Wait failed: {e}")
    
    def stop(self):
        """Stop current playback."""
        try:
            self._paused = False
            sd.stop()
            logging.info("[PiperTTS] Playback stopped")
        except Exception as e:
            logging.error(f"[PiperTTS] Failed to stop playback: {e}")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
    
    def speak_ssml(self, ssml_text: str):
        """Speak SSML formatted text (if supported by model)."""
        # Piper might have limited SSML support
        self.speak(ssml_text)

    def speak_with_parameters(self, text: str, rate: float = 1.0, pitch: float = 1.0):
        """Speak with adjusted parameters (if model supports it)."""
        # This would depend on Piper's capabilities
        processed_text = f"<prosody rate={rate} pitch={pitch}>{text}</prosody>"
        self.speak(processed_text)
    
    def get_status(self) -> dict:
        """Get TTS status information."""
        return {
            'initialized': self.voice is not None,
            'speaking': self._is_speaking,
            'paused': self._paused,
            'worker_running': self._worker_thread is not None and self._worker_thread.is_alive(),
            'queue_size': self._speech_queue.qsize(),
            'language': self._get_language_info(),
            'volume': self.volume,
            'audio_device': self.audio_device
        }

    def health_check(self) -> dict:
        """Perform comprehensive health check."""
        status = self.get_status()
        
        # Test audio output
        audio_ok = False
        try:
            test_audio = np.zeros(1000, dtype=np.float32)
            self._play_audio_with_volume(test_audio, 22050)
            audio_ok = True
        except Exception as e:
            status['audio_error'] = str(e)
        
        status.update({
            'audio_output_working': audio_ok,
            'piper_available': PIPER_AVAILABLE,
            'model_loaded': self.voice is not None,
            'worker_alive': self._worker_thread is not None and self._worker_thread.is_alive()
        })
        
        return status
    
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