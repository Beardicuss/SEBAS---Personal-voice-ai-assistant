import pvporcupine
import sounddevice as sd
import numpy as np
import logging
from threading import Thread, Event
from openwakeword.model import Model


class WakeWordDetector:
    """
    Hybrid wake word detector:
      - Porcupine (fast, robust)
      - OpenWakeWord (modern, NN-based)
    Modes:
      - "porcupine": only ppn
      - "openwakeword": only oww
      - "hybrid_and": ppn trigger → oww confirm
      - "hybrid_or": ppn trigger OR oww trigger
    """

    def __init__(self,
                 porcupine_keyword="hey computer",
                 oww_model_name="hey_sebas",
                 mode="hybrid_and",
                 sensitivity=0.6,
                 callback=None):

        self.mode = mode
        self.callback = callback
        self.running = False
        self.stop_event = Event()

        # --------- Porcupine ---------
        try:
            self.porcupine = pvporcupine.create(
                keywords=[porcupine_keyword],
                sensitivities=[sensitivity]
     )
            logging.info("Porcupine loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Porcupine: {e}")
            self.porcupine = None

        # --------- OpenWakeWord ---------
        try:
            self.oww = Model()
            self.oww_model_name = oww_model_name
            logging.info("OpenWakeWord model initialized")
        except Exception as e:
            logging.error(f"Failed to load OpenWakeWord: {e}")
            self.oww = None

        self.sample_rate = 16000
        self.frame_length = 512

    # -------------------------------------------------------
    # Internal detector
    # -------------------------------------------------------
    def _listen_loop(self):
        with sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.frame_length,
            dtype="int16"
        ) as stream:

            logging.info("[WakeWord] Listening thread started")

            while not self.stop_event.is_set():
                data, _ = stream.read(self.frame_length)
                pcm = np.frombuffer(data, dtype=np.int16)

                triggered_ppn = False
                triggered_oww = False

                # ---- Porcupine ----
                if self.porcupine:
                    try:
                        result = self.porcupine.process(pcm)
                        if result >= 0:
                            triggered_ppn = True
                    except Exception:
                        pass

                # ---- OpenWakeWord ----
                if self.oww:
                    try:
                        scores = self.oww.predict(pcm)
                        if scores.get(self.oww_model_name, 0) > 0.6:
                            triggered_oww = True
                    except Exception:
                        pass

                # ---- Decide mode ----
                if self.mode == "porcupine" and triggered_ppn:
                    self._fire()

                elif self.mode == "openwakeword" and triggered_oww:
                    self._fire()

                elif self.mode == "hybrid_or":
                    if triggered_ppn or triggered_oww:
                        self._fire()

                elif self.mode == "hybrid_and":
                    if triggered_ppn and triggered_oww:
                        self._fire()

    def _fire(self):
        if self.callback:
            try:
                self.callback()
            except Exception:
                logging.exception("Wake word callback failed")

    # -------------------------------------------------------
    # Public API
    # -------------------------------------------------------
    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()

        t = Thread(target=self._listen_loop, daemon=True, name="WakeWordDetector")
        t.start()

    def stop(self):
        self.stop_event.set()
        self.running = False