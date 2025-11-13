import logging
from threading import Thread

from sebas.wakeword.wakeword_porcupine import PorcupineWakeWord
from sebas.wakeword.wakeword_vosk import VoskWakeWord
from sebas.wakeword.wakeword_dummy import DummyWakeWord


class WakeWordManager:
    """Hybrid wake-word engine with layered fallback."""

    def __init__(self, callback, keyword="sebas"):
        self.callback = callback
        self.keyword = keyword.lower()
        self.engine = None
        self.thread = None
        self.running = False

        # Try Porcupine → then Vosk → Fallback
        try:
            self.engine = PorcupineWakeWord(self.keyword)
            logging.info("WakeWord: Porcupine initialized.")
        except Exception:
            logging.warning("Porcupine unavailable, switching to Vosk.")
            try:
                self.engine = VoskWakeWord(self.keyword)
                logging.info("WakeWord: Vosk initialized.")
            except Exception:
                logging.warning("WakeWord: No engine available. Using Dummy.")
                self.engine = DummyWakeWord()

    def start(self):
        if self.running:
            return
        self.running = True

        def loop():
            while self.running:
                if self.engine.detect():
                    self.callback()  # call main handler

        self.thread = Thread(target=loop, name="WakeWord", daemon=True)
        self.thread.start()
        logging.info("WakeWordDetector thread started")

    def stop(self):
        self.running = False