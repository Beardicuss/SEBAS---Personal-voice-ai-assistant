"""
Wake Word Detector - Stage 1 Mk.I (MINIMAL)
Manual trigger only - no audio dependencies
Voice detection comes in Stage 2
"""

import logging
import threading


class WakeWordDetector:
    """
    Stage 1: Manual trigger only (UI/API/Keyboard)
    Stage 2: Add Vosk/Porcupine voice detection
    """
    
    def __init__(self, callback, keyword="sebas"):
        """
        Initialize wake word detector in manual mode.
        
        Args:
            callback: Function to call when triggered
            keyword: Wake word (for future use)
        """
        self.callback = callback
        self.keyword = keyword.lower()
        self.running = False
        self.mode = "manual"
        
        logging.info(f"[WakeWord] Initialized in MANUAL mode (keyword: '{keyword}')")
        logging.info("[WakeWord] Trigger via UI, API, or keyboard")
    
    def start(self):
        """Start wake word detection (manual mode)"""
        if self.running:
            logging.warning("[WakeWord] Already running")
            return
        
        self.running = True
        logging.info("[WakeWord] Started - awaiting manual triggers")
        logging.info("[WakeWord] Use UI console or API to send commands")
    
    def stop(self):
        """Stop wake word detection"""
        self.running = False
        logging.info("[WakeWord] Stopped")
    
    def manual_trigger(self):
        """
        Manually trigger wake word callback.
        Called from UI or API when user sends command.
        """
        if not self.running:
            logging.warning("[WakeWord] Not running - trigger ignored")
            return
        
        logging.info(f"[WakeWord] Manual trigger activated")
        
        if self.callback:
            try:
                # Execute callback in separate thread to avoid blocking
                threading.Thread(
                    target=self.callback,
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
            'audio_available': False,  # Stage 1: no audio
            'vosk_available': False
        }


# Stage 2 will add:
# - VoskWakeWord class with actual audio detection
# - PorcupineWakeWord for custom models
# - Automatic fallback between modes
# - Sensitivity adjustment
# - Noise filtering