
"""
Wake Word Detector
Porcupine-based wake word listener.
"""

import logging
import threading
import time

try:
    import pvporcupine
    import pyaudio
except Exception:
    pvporcupine = None
    pyaudio = None


class WakeWordDetector:
    """Background thread for wake word detection."""

    def __init__(self, callback, keyword="jarvis"):
        self.callback = callback
        self.keyword = keyword
        self._running = False
        self.thread = None

    # ----------------------------------------------------------
    # Start wake word loop
    # ----------------------------------------------------------
    def start(self):
        if self.thread:
            return

        if not pvporcupine:
            logging.warning("Porcupine not installed, wake word disabled.")
            return

        self._running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # ----------------------------------------------------------
    # Wake word loop
    # ----------------------------------------------------------
    def _loop(self):
        """Continuous audio capture for wake word detection."""
        logging.info("WakeWordDetector thread started.")

        if not pvporcupine:
            logging.warning("Porcupine unavailable.")
            return

        try:
            porcupine = pvporcupine.create(keywords=[self.keyword])
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length
            )
        except Exception as e:
            logging.error(f"Wakeword initialization failed: {e}")
            return

        while self._running:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = memoryview(pcm).cast("h")
            result = porcupine.process(pcm)

            if result >= 0:
                self.callback()

        stream.stop_stream()
        stream.close()
        pa.terminate()