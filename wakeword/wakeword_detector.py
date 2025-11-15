"""
Wake Word Detector - Stage 1 Mk.I with Audio Detection and Text Output
"""

import logging
from pathlib import Path
import threading
import time


class WakeWordDetector:
    """
    Wake word detector with audio support.
    Listens for wake word, then triggers callback with recognized text.
    """
    
    def __init__(self, callback, keyword="check"): # აქ არი
        """
        Initialize wake word detector.
        
        Args:
            callback: Function to call when wake word detected
            keyword: Wake word to listen for
        """
        self.callback = callback
        self.keyword = keyword.lower()
        self.running = False
        self.mode = "manual"  # Start with manual, change to audio if successful
        self.detection_thread = None
        self.detector = None
        self.last_recognized_text = ""
                
        # Try to initialize Vosk wake word detection
        try:
            logging.info("[WakeWord] Attempting to initialize Vosk...")
            from .wakeword_vosk import VoskWakeWord
            
            self.detector = VoskWakeWord(keyword=keyword)
            
            # Verify detector was created successfully
            if self.detector is not None:
                self.mode = "audio"
                logging.info(f"[WakeWord] ✓ Successfully initialized in AUDIO mode (keyword: '{keyword}')")
                logging.info("[WakeWord] Will listen for wake word via microphone")
            else:
                logging.error("[WakeWord] Detector initialization returned None")
                self.mode = "manual"
                
        except ImportError as e:
            logging.warning(f"[WakeWord] Cannot import VoskWakeWord: {e}")
            logging.info("[WakeWord] Falling back to MANUAL mode")
            self.mode = "manual"
            self.detector = None
        except Exception as e:
            logging.exception(f"[WakeWord] Audio detection initialization failed: {e}")
            logging.info("[WakeWord] Falling back to MANUAL mode")
            self.mode = "manual"
            self.detector = None
    
    def start(self):
        """Start wake word detection"""
        if self.running:
            logging.warning("[WakeWord] Already running")
            return
        
        self.running = True
        
        # Debug: Log current state
        logging.info(f"[WakeWord] Starting with mode='{self.mode}', detector={'present' if self.detector else 'None'}")
        
        if self.mode == "audio" and self.detector is not None:
            # Start audio detection thread
            logging.info("[WakeWord] ✓ Starting audio detection thread...")
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True,
                name="WakeWordDetection"
            )
            self.detection_thread.start()
            logging.info("[WakeWord] ✓ Audio detection started - listening for wake word...")
            logging.info(f"[WakeWord] Speak '{self.keyword}' to activate")
        else:
            # Debug: Explain why we're in manual mode
            if self.mode != "audio":
                logging.info(f"[WakeWord] In MANUAL mode (mode='{self.mode}')")
            elif self.detector is None:
                logging.info("[WakeWord] In MANUAL mode (detector is None)")
            logging.info("[WakeWord] Use UI console or API to send commands")
    
    def _detection_loop(self):
        """Continuously listen for wake word and capture recognized text"""
        logging.info("[WakeWord] Detection loop started")
        
        # Early exit if no detector available
        if not self.detector:
            logging.error("[WakeWord] No detector available for detection loop")
            return
        
        while self.running:
            try:
                # Get detection result with text
                result = self.detector.detect()
                
                if isinstance(result, dict) and result.get('detected'):
                    # New format: dict with detected flag and text
                    detected_text = result.get('text', '')
                    self.last_recognized_text = detected_text
                    
                    logging.info(f"[WakeWord] ✓ '{self.keyword}' detected in: '{detected_text}'")
                    
                    # Trigger callback with the recognized text
                    if self.callback:
                        try:
                            self.callback(detected_text)
                        except Exception as e:
                            logging.exception(f"[WakeWord] Callback error: {e}")
                    
                    # Small delay to avoid multiple triggers
                    time.sleep(1)
                
                elif result is True:
                    # Old format: just boolean (backward compatibility)
                    logging.info(f"[WakeWord] ✓ '{self.keyword}' detected!")
                    
                    if self.callback:
                        try:
                            self.callback()
                        except Exception as e:
                            logging.exception(f"[WakeWord] Callback error: {e}")
                    
                    time.sleep(1)
                    
            except Exception as e:
                logging.error(f"[WakeWord] Detection error: {e}")
                import traceback
                logging.error(traceback.format_exc())
                time.sleep(0.1)  # Brief pause on error
        
        logging.info("[WakeWord] Detection loop stopped")
    
    def stop(self):
        """Stop wake word detection"""
        self.running = False
        
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2)
        
        if self.detector and hasattr(self.detector, 'cleanup'):
            self.detector.cleanup()
        
        logging.info("[WakeWord] Stopped")
    
    def manual_trigger(self, text="manual trigger"):
        """
        Manually trigger wake word callback with optional text.
        Used in manual mode or for testing.
        
        Args:
            text: Optional text to pass to callback
        """
        if not self.running:
            logging.warning("[WakeWord] Not running - trigger ignored")
            return
        
        logging.info(f"[WakeWord] Manual trigger activated: '{text}'")
        self.last_recognized_text = text
        
        if self.callback:
            try:
                threading.Thread(
                    target=lambda: self.callback(text),
                    daemon=True,
                    name="WakeWordCallback"
                ).start()
            except Exception as e:
                logging.exception(f"[WakeWord] Callback error: {e}")
    
    def get_status(self) -> dict:
        """Get current detector status"""
        return {
            'mode': self.mode,
            'running': self.running,
            'keyword': self.keyword,
            'audio_available': self.mode == "audio",
            'detector_active': self.detection_thread and self.detection_thread.is_alive() if self.detection_thread else False,
            'last_recognized_text': self.last_recognized_text,
            'detector_present': self.detector is not None
        }
    
    def get_last_recognized_text(self) -> str:
        """Get the last recognized text"""
        return self.last_recognized_text