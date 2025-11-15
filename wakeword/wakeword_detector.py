"""
Wake Word Detector - Stage 1 Mk.I with Audio Detection and Text Output
Enhanced with wake word variations support
"""

import logging
from pathlib import Path
import threading
import time


class WakeWordDetector:
    """
    Wake word detector with audio support and variation matching.
    Listens for wake word (and its variations), then triggers callback with recognized text.
    """
    
    def __init__(self, callback, keyword="sebas", variations=None):
        """
        Initialize wake word detector.
        
        Args:
            callback: Function to call when wake word detected
            keyword: Primary wake word to listen for
            variations: List of acceptable variations (optional)
        """
        self.callback = callback
        self.keyword = keyword.lower()
        self.running = False
        self.mode = "manual"  # Start with manual, change to audio if successful
        self.detection_thread = None
        self.detector = None
        self.last_recognized_text = ""
        
        # Setup wake word variations
        if variations is None:
            # Default comprehensive variations for "sebas"
            self.variations = [
                # Direct variations
                "sebas",
                "sebus",
                "sebass",
                "sebbas",
                
                # Phonetic variations
                "see bass",
                "see bus",
                "see boss",
                "sea bass",
                "sea bus",
                "sea boss",
                "c bass",
                "c bus", 
                "c boss",
                
                # "So" variations (common misrecognitions from logs)
                "so bass",
                "so bus",
                "so boss",
                "so bas",
                
                # Common misrecognitions
                "cebas",
                "cebus",
                "seavas",
                "sevas",
                "sabres",
                "sabers",
                
                # With spacing variations
                "se bas",
                "se bus",
                "se boss",
                
                # Partial matches
                "seba",
                "sebba",
                
                # Other phonetic possibilities
                "say bass",
                "say bus",
                "say boss",
                "seabus",
                "seabass",
                "cbass",
            ]
        else:
            self.variations = [v.lower() for v in variations]
        
        # Ensure primary keyword is in variations
        if self.keyword not in self.variations:
            self.variations.insert(0, self.keyword)
        
        logging.info(f"[WakeWord] Configured with {len(self.variations)} variations")
        logging.debug(f"[WakeWord] Variations: {self.variations}")
                
        # Try to initialize Vosk wake word detection
        try:
            logging.info("[WakeWord] Attempting to initialize Vosk...")
            from .wakeword_vosk import VoskWakeWord
            
            self.detector = VoskWakeWord(keyword=keyword)
            
            # Verify detector was created successfully
            if self.detector is not None:
                self.mode = "audio"
                logging.info(f"[WakeWord] ✓ Successfully initialized in AUDIO mode (keyword: '{keyword}')")
                logging.info(f"[WakeWord] Will listen for '{keyword}' and {len(self.variations)} variations")
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
    
    def _check_variations(self, text: str) -> tuple[bool, str]:
        """
        Check if any wake word variation is present in the text.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (detected: bool, matched_variation: str)
        """
        text_lower = text.lower()
        
        for variation in self.variations:
            if variation in text_lower:
                return True, variation
        
        return False, ""
    
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
            logging.info(f"[WakeWord] Speak '{self.keyword}' (or variations) to activate")
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
                    
                    # Check for variations in the detected text
                    is_match, matched_variation = self._check_variations(detected_text)
                    
                    if is_match:
                        logging.info(f"[WakeWord] ✓ Wake word detected! Matched '{matched_variation}' in: '{detected_text}'")
                        
                        # Trigger callback with the recognized text
                        if self.callback:
                            try:
                                self.callback(detected_text)
                            except Exception as e:
                                logging.exception(f"[WakeWord] Callback error: {e}")
                        
                        # Small delay to avoid multiple triggers
                        time.sleep(1)
                    else:
                        # Text was detected but no wake word variation matched
                        logging.debug(f"[WakeWord] Detected text '{detected_text}' - no wake word match")
                
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
            'variations_count': len(self.variations),
            'audio_available': self.mode == "audio",
            'detector_active': self.detection_thread and self.detection_thread.is_alive() if self.detection_thread else False,
            'last_recognized_text': self.last_recognized_text,
            'detector_present': self.detector is not None
        }
    
    def get_last_recognized_text(self) -> str:
        """Get the last recognized text"""
        return self.last_recognized_text
    
    def get_variations(self) -> list:
        """Get list of all wake word variations"""
        return self.variations.copy()
    
    def add_variation(self, variation: str):
        """
        Add a new wake word variation.
        
        Args:
            variation: New variation to add
        """
        variation_lower = variation.lower()
        if variation_lower not in self.variations:
            self.variations.append(variation_lower)
            logging.info(f"[WakeWord] Added new variation: '{variation}'")
        else:
            logging.debug(f"[WakeWord] Variation '{variation}' already exists")
    
    def remove_variation(self, variation: str):
        """
        Remove a wake word variation.
        
        Args:
            variation: Variation to remove
        """
        variation_lower = variation.lower()
        if variation_lower in self.variations and variation_lower != self.keyword:
            self.variations.remove(variation_lower)
            logging.info(f"[WakeWord] Removed variation: '{variation}'")
        elif variation_lower == self.keyword:
            logging.warning(f"[WakeWord] Cannot remove primary keyword '{self.keyword}'")
        else:
            logging.debug(f"[WakeWord] Variation '{variation}' not found")