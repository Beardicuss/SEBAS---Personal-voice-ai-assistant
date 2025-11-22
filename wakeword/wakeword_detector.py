import logging
from pathlib import Path
import threading
import time
from difflib import SequenceMatcher


class WakeWordDetector:
    """
    Wake word detector with Whisper audio support and fuzzy matching.
    Listens for wake word, then triggers callback with recognized text.
    """

    def __init__(self, callback, keyword="master sebas", model_size="tiny", fuzzy_threshold=0.7, timeout_seconds=10):
        self.callback = callback
        self.keyword = keyword.lower()
        self.model_size = model_size
        self.fuzzy_threshold = fuzzy_threshold
        self.running = False
        self.mode = "manual"
        self.detection_thread = None
        self.detector = None
        self.last_recognized_text = ""
        
        # Listening mode for continuous commands
        self.listening_mode = False
        self.last_command_time = 0
        self.timeout_seconds = timeout_seconds

        self.known_variants = [
            "must it save us", "master sabas", "master sabers", "master supers",
            "master service", "master say buzz", "master sabos", "master cybers",
            "master sebus", "master saber", "master cyber", "master saves",
            "master server", "master sebass", "master savage", "master savas",
            "mister sabas", "mister sebas", "mister sabers", "mister sebus",
            "master see bus", "master sea bass", "master say boss", "master say bus",
            "Must It Save Us", "Master Sabas", "Master Sabers", "Master Supers",
            "Master Service", "Master Say Buzz", "Master Sabos", "Master Cybers",
            "Master Sebus", "Master Saber", "Master Cyber", "Master Saves",
            "Master Server", "Master Sebass", "Master Savage", "Master Savas",
            "Mister Sabas", "Mister Sebas", "Mister Sabers", "Mister Sebus",
            "Master See Bus", "Master Sea Bass", "Master Say Boss", "Master Say Bus"
        ]

        logging.info(f"[WakeWord] Fuzzy matching enabled (threshold: {fuzzy_threshold})")
        logging.info(f"[WakeWord] Target keyword: '{keyword}'")

        try:
            logging.info("[WakeWord] Attempting to initialize Whisper...")
            from .wakeword_whisper import WhisperWakeWord

            self.detector = WhisperWakeWord(
                keyword=keyword,
                model_size=model_size
            )

            if self.detector is not None:
                self.mode = "audio"
                logging.info(f"[WakeWord] ✓ Initialized in AUDIO mode (model='{model_size}')")
            else:
                logging.error("[WakeWord] Detector initialization returned None")
                self.mode = "manual"

        except Exception as e:
            logging.exception(f"[WakeWord] Whisper init failed: {e}")
            self.mode = "manual"
            self.detector = None

    def _fuzzy_match(self, text1, text2):
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _check_fuzzy_wake_word(self, text):
        text_lower = text.lower()

        # 1. Exact match
        if self.keyword in text_lower:
            remaining = text_lower.replace(self.keyword, "", 1).strip()
            return True, 1.0, self.keyword, remaining

        # 2. Known variants
        for variant in self.known_variants:
            variant_lower = variant.lower()
            if variant_lower in text_lower:
                sim = self._fuzzy_match(variant_lower, self.keyword)
                remaining = text_lower.replace(variant_lower, "", 1).strip()
                return True, sim, variant, remaining

        # 3. Fuzzy sliding window
        words = text_lower.split()
        kw_words = self.keyword.split()
        n = len(kw_words)

        best_sim = 0
        best_phrase = ""
        best_index = -1

        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i + n])
            sim = self._fuzzy_match(phrase, self.keyword)
            if sim > best_sim:
                best_sim = sim
                best_phrase = phrase
                best_index = i

        detected = best_sim >= self.fuzzy_threshold

        if detected:
            remaining_words = words[:best_index] + words[best_index + n:]
            return True, best_sim, best_phrase, " ".join(remaining_words).strip()

        return False, best_sim, best_phrase, text_lower

    def start(self):
        if self.running:
            return

        self.running = True

        if self.mode == "audio" and self.detector:
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True
            )
            self.detection_thread.start()

    def _detection_loop(self):
        if not self.detector:
            logging.error("[WakeWord] No detector for audio mode")
            return

        while self.running:
            try:
                result = self.detector.detect()

                if isinstance(result, dict) and result.get("detected"):
                    text = result.get("text", "")
                    self.last_recognized_text = text
                    
                    # Check if we're in listening mode
                    if self.listening_mode:
                        current_time = time.time()
                        
                        # Check if user said wake word again - reset timer
                        ok, sim, phrase, rest = self._check_fuzzy_wake_word(text)
                        if ok:
                            logging.info(f"[WakeWord] Wake word detected during listening mode - resetting timer")
                            self.last_command_time = current_time
                            
                            try:
                                if hasattr(self.detector, "pause"):
                                    self.detector.pause()
                                
                                # Execute command if provided, otherwise just acknowledge
                                self.callback(rest if rest else "")
                                
                                if hasattr(self.detector, "resume"):
                                    self.detector.resume()
                            except Exception as e:
                                logging.exception(e)
                            
                            time.sleep(0.5)
                            continue
                        
                        # Not wake word - treat as command and reset timer
                        logging.info(f"[WakeWord] Command in listening window: '{text}'")
                        self.last_command_time = current_time
                        
                        try:
                            if hasattr(self.detector, "pause"):
                                self.detector.pause()
                            
                            self.callback(text)
                            
                            if hasattr(self.detector, "resume"):
                                self.detector.resume()
                        except Exception as e:
                            logging.exception(e)
                        
                        time.sleep(0.5)
                        continue
                    
                    # Not in listening mode - check for wake word
                    ok, sim, phrase, rest = self._check_fuzzy_wake_word(text)
                    if ok:
                        logging.info(f"[WakeWord] Wake-word detected: '{phrase}' (sim={sim:.2f})")
                        
                        # Enter listening mode
                        self.listening_mode = True
                        self.last_command_time = time.time()
                        logging.info(f"[WakeWord] Entering listening mode for {self.timeout_seconds} seconds")

                        try:
                            if hasattr(self.detector, "pause"):
                                self.detector.pause()

                            # Pass command or empty string to trigger "Yes, sir?"
                            self.callback(rest if rest else "")

                            if hasattr(self.detector, "resume"):
                                self.detector.resume()
                        except Exception as e:
                            logging.exception(e)

                        time.sleep(0.5)
                
                # Check for timeout only when NO speech detected and in listening mode
                elif self.listening_mode:
                    current_time = time.time()
                    if current_time - self.last_command_time >= self.timeout_seconds:
                        # Timeout expired - back to wake word mode
                        self.listening_mode = False
                        logging.info("[WakeWord] Listening timeout expired")
                        
                        # Notify user that timeout expired
                        try:
                            if hasattr(self.detector, "pause"):
                                self.detector.pause()
                            
                            self.callback("__TIMEOUT__")
                            
                            if hasattr(self.detector, "resume"):
                                self.detector.resume()
                        except Exception as e:
                            logging.exception(e)

            except Exception as e:
                logging.error(f"[WakeWord] detect() error: {e}")
                time.sleep(0.5)

    def stop(self):
        self.running = False
        if self.detector and hasattr(self.detector, "cleanup"):
            self.detector.cleanup()

    def manual_trigger(self, text="manual"):
        if self.callback:
            threading.Thread(target=lambda: self.callback(text), daemon=True).start()

    def get_status(self):
        return {
            "running": self.running,
            "mode": self.mode,
            "keyword": self.keyword,
            "last_text": self.last_recognized_text
        }
