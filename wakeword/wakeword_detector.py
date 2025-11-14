import logging
import threading
import sounddevice as sd
import numpy as np
import queue
import time
from vosk import Model, KaldiRecognizer

"""
Wake word detector using:
    - live microphone input
    - Vosk speech-to-text
    - keyword matching in recognized text
    
Keyword: "sebas"
"""


class WakeWordDetector:
    def __init__(self, callback, keyword="sebas"):
        self.callback = callback
        self.keyword = keyword.lower()

        # Load tiny Vosk English model for keyword detection
        try:
            self.model = Model("vosk-model-small-en-us")
            self.recognizer = KaldiRecognizer(self.model, 16000)
            logging.info("[WakeWord] Vosk keyword engine loaded.")
        except Exception:
            logging.exception("[WakeWord] Failed to load tiny Vosk model.")
            self.model = None
            self.recognizer = None

        self.running = False
        self.thread = None

    def start(self):
        if not self.model:
            logging.warning("[WakeWord] No model; wake word disabled.")
            return

        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logging.info("[WakeWord] Wake word detector started.")

    def stop(self):
        self.running = False

    # -----------------------------------
    # Listening loop
    # -----------------------------------
    def _listen_loop(self):
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                while self.running:
                    time.sleep(0.1)
        except Exception as e:
            logging.error(f"[WakeWord] Microphone error: {e}")

    # -----------------------------------
    # Audio callback
    # -----------------------------------
    def _audio_callback(self, indata, frames, time_info, status):
        if not self.recognizer:
            return

        try:
            # Convert raw memoryview -> bytes for Vosk
            pcm_bytes = bytes(indata)

            if self.recognizer.AcceptWaveform(pcm_bytes):
                res = self.recognizer.Result()
            else:
                res = self.recognizer.PartialResult()

            text = self._extract_text(res)

            if text and self.keyword in text:
                logging.info("[WakeWord] Triggered!")
                self.callback()

        except Exception as e:
            logging.error(f"[WakeWord] Audio processing error: {e}")

    # -----------------------------------
    @staticmethod
    def _extract_text(res_json):
        import json
        try:
            data = json.loads(res_json)
            if "partial" in data:
                return data["partial"].lower()
            if "text" in data:
                return data["text"].lower()
        except Exception:
            pass
        return ""
