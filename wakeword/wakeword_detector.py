"""
Hybrid Wake Word Detector for SEBAS
Supports:
    - Porcupine (fast, classical)
    - OpenWakeWord (modern neural engine)
    - Hybrid modes:
        * hybrid_or   – trigger if ANY detects
        * hybrid_and  – trigger only if BOTH detect
"""

import logging
import numpy as np
import sounddevice as sd
from threading import Thread, Event

# External wake-word engines
try:
    import pvporcupine
except Exception:
    pvporcupine = None

try:
    from openwakeword.model import Model as OWWModel
except Exception:
    OWWModel = None


class WakeWordDetector:
    """
    Main wake-word engine wrapper.
    Modes:
        - porcupine
        - openwakeword
        - hybrid_or
        - hybrid_and
    """

    def __init__(
        self,
        porcupine_keyword: str = "hey computer",
        oww_model_name: str = "hey_sebas",
        mode: str = "hybrid_and",
        sensitivity: float = 0.6,
        callback=None,
    ):
        self.mode = mode
        self.callback = callback
        self.running = False
        self.stop_event = Event()

        # Audio params
        self.sample_rate = 16000
        self.frame_length = 512

        # ---------------------------------------------------------
        # Load Porcupine
        # ---------------------------------------------------------
        self.porcupine = None
        if pvporcupine:
            try:
                self.porcupine = pvporcupine.create(
                    keywords=[porcupine_keyword],
                    sensitivities=[sensitivity],
                )
                logging.info(f"[WakeWord] Porcupine loaded: {porcupine_keyword}")
            except Exception as e:
                logging.error(f"[WakeWord] Porcupine failed: {e}")
        else:
            logging.warning("[WakeWord] Porcupine not installed")

        # ---------------------------------------------------------
        # Load OpenWakeWord
        # ---------------------------------------------------------
        self.oww = None
        self.oww_model_name = oww_model_name

        if OWWModel:
            try:
                self.oww = OWWModel()
                logging.info(f"[WakeWord] OpenWakeWord loaded ({oww_model_name})")
            except Exception as e:
                logging.error(f"[WakeWord] OpenWakeWord failed: {e}")
        else:
            logging.warning("[WakeWord] OpenWakeWord not installed")

        # If neither engine works, warn the user
        if not self.porcupine and not self.oww:
            logging.error("[WakeWord] NO wake-word engines available!")

    # ============================================================
    # Internal listener loop
    # ============================================================
    def _listen_loop(self):
        try:
            stream = sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.frame_length,
                dtype="int16",
            )
        except Exception as e:
            logging.error(f"[WakeWord] Failed to open microphone: {e}")
            return

        with stream:
            logging.info("[WakeWord] Listening thread started")

            while not self.stop_event.is_set():
                try:
                    pcm_bytes, _ = stream.read(self.frame_length)
                    pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
                except Exception as e:
                    logging.error(f"[WakeWord] Audio capture error: {e}")
                    continue

                # Flags
                detected_ppn = False
                detected_oww = False

                # ------------------- Porcupine -------------------
                if self.porcupine:
                    try:
                        res = self.porcupine.process(pcm)
                        if res >= 0:
                            detected_ppn = True
                    except Exception:
                        pass

                # ------------------- OpenWakeWord ----------------
                if self.oww:
                    try:
                        scores = self.oww.predict(pcm)
                        if scores.get(self.oww_model_name, 0.0) > 0.6:
                            detected_oww = True
                    except Exception:
                        pass

                # ------------------- MODE LOGIC ------------------
                fire = False

                if self.mode == "porcupine":
                    fire = detected_ppn

                elif self.mode == "openwakeword":
                    fire = detected_oww

                elif self.mode == "hybrid_or":
                    fire = detected_ppn or detected_oww

                elif self.mode == "hybrid_and":
                    fire = detected_ppn and detected_oww

                # ------------------- FIRE EVENT ------------------
                if fire:
                    self._fire_event(
                        detected_ppn=detected_ppn,
                        detected_oww=detected_oww,
                    )

    # ============================================================
    # Trigger callback
    # ============================================================
    def _fire_event(self, detected_ppn=False, detected_oww=False):
        if self.callback:
            try:
                self.callback(
                    {
                        "porcupine": detected_ppn,
                        "openwakeword": detected_oww,
                        "mode": self.mode,
                    }
                )
            except Exception:
                logging.exception("[WakeWord] Callback failed")

    # ============================================================
    # Public API
    # ============================================================
    def start(self):
        if self.running:
            return

        self.running = True
        self.stop_event.clear()

        t = Thread(
            target=self._listen_loop,
            daemon=True,
            name="WakeWordDetector",
        )
        t.start()
        logging.info("[WakeWord] Detector started")

    def stop(self):
        self.stop_event.set()
        self.running = False
        logging.info("[WakeWord] Detector stopped")