import logging
from pathlib import Path
import vosk
import pyaudio
import json
import numpy as np

class VoskWakeWord:
    def __init__(self, keyword="sebas"):
        self.keyword = keyword.lower()
        
        logging.info("[VoskWakeWord] Initializing...")
        
        base_dir = Path(__file__).resolve().parent.parent
        model_path = base_dir / "model" / "vosk-model-small-en-us-0.15"
        
        # Convert Path to string for Vosk
        model_path_str = str(model_path)
        
        logging.info(f"[VoskWakeWord] Loading model from: {model_path_str}")
        self.model = vosk.Model(model_path_str)
        self.recog = vosk.KaldiRecognizer(self.model, 16000)
        self.recog.SetWords(True)
        
        # List available audio devices
        self.pa = pyaudio.PyAudio()
        logging.info("[VoskWakeWord] Available audio input devices:")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)

            # приводим maxInputChannels к числу
            try:
                max_in = int(info.get('maxInputChannels', 0))
            except (TypeError, ValueError):
                max_in = 0

            if max_in > 0:
                logging.info(f"  [{i}] {info['name']} - {max_in} channels")

        
        # Open audio stream
        try:
            self.stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=4000
            )
            logging.info("[VoskWakeWord] Audio stream opened successfully")
        except Exception as e:
            logging.error(f"[VoskWakeWord] Failed to open audio stream: {e}")
            raise
        
        # Track state
        self.last_detection_text = ""
        self.silence_counter = 0
        self.total_checks = 0
        self.audio_level_checks = 0
        
        logging.info(f"[VoskWakeWord] Ready! Listening for '{keyword}'...")
        logging.info("[VoskWakeWord] Speak into your microphone to test...")

    def detect(self):
        """
        Check if wake word is detected.
        
        Returns:
            dict with 'detected' (bool) and 'text' (str) keys if wake word found,
            False otherwise
        """
        try:
            # Read audio data
            data = self.stream.read(4000, exception_on_overflow=False)
            
            # Calculate audio level for debugging
            self.total_checks += 1
            audio_array = np.frombuffer(data, dtype=np.int16)
            audio_level = np.abs(audio_array).mean()
            
            # Log audio level periodically (every 50 checks = ~5 seconds)
            if self.total_checks % 50 == 0:
                self.audio_level_checks += 1
                logging.info(f"[VoskWakeWord] Audio level check #{self.audio_level_checks}: {audio_level:.1f} "
                           f"(threshold ~500 for speech)")
                if audio_level < 100:
                    logging.warning("[VoskWakeWord] Audio level very low - check microphone!")
            
            # Process with Vosk
            if self.recog.AcceptWaveform(data):
                result = json.loads(self.recog.Result())
                text = result.get("text", "").lower()
                
                if text:
                    logging.info(f"[VoskWakeWord] 🎤 RECOGNIZED: '{text}'")
                    
                    # Check for wake word
                    if self.keyword in text:
                        if text != self.last_detection_text:
                            logging.info(f"[VoskWakeWord] ✓ WAKE WORD DETECTED: '{text}'")
                            self.last_detection_text = text
                            self.silence_counter = 0
                            # Return dict with detected flag and full text
                            return {'detected': True, 'text': text}
                        else:
                            logging.debug("[VoskWakeWord] Duplicate detection, ignoring")
                    
                    self.silence_counter = 0
            else:
                # Check partial results
                partial = json.loads(self.recog.PartialResult())
                partial_text = partial.get("partial", "").lower()
                
                if partial_text:
                    # Log partial results less frequently to avoid spam
                    if self.total_checks % 10 == 0:
                        logging.debug(f"[VoskWakeWord] Partial: '{partial_text}'")
                    
                    self.silence_counter = 0
                else:
                    self.silence_counter += 1
                    
                    # Reset after ~2 seconds of silence
                    if self.silence_counter > 50:
                        if self.last_detection_text:
                            logging.debug("[VoskWakeWord] Silence detected, resetting state")
                        self.last_detection_text = ""
                        self.silence_counter = 0
            
            return False
            
        except Exception as e:
            logging.error(f"[VoskWakeWord] Detection error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def cleanup(self):
        """Clean up audio resources"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pa:
                self.pa.terminate()
            logging.info("[VoskWakeWord] Cleaned up")
        except Exception as e:
            logging.error(f"[VoskWakeWord] Cleanup error: {e}")