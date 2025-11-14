import os
import logging
import pvporcupine
import pyaudio
import struct
import threading


class WakeWordDetector:
    """
    Ultra-minimal wake-word detector for SEBAS.
    Pure Porcupine + custom .ppn keyword.
    No fallbacks, no hybrid logic, no sounddevice, no bullshit.
    """

    def __init__(self, callback, keyword="Alfred"):
        self.callback = callback
        self.running = False

        # Load access key
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        if not access_key:
            raise RuntimeError("PICOVOICE_ACCESS_KEY environment variable is not set!")

        # Build path to PPN model
        base = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base, "models", f"{keyword}.ppn")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Wake-word model not found: {model_path}\n"
                "Place your Alfred.ppn in sebas/wakeword/models/"
            )

        # Init Porcupine
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[model_path]
        )

        # Init PyAudio stream
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

        logging.info(f"[WakeWord] Loaded keyword: {keyword}.ppn")

    def start(self):
        if self.running:
            return

        self.running = True
        thread = threading.Thread(target=self._run, daemon=True, name="WakeWord")
        thread.start()
        logging.info("[WakeWord] Detector started")

    def _run(self):
        logging.info("[WakeWord] Listening thread started")

        while self.running:
            try:
                pcm_bytes = self.stream.read(
                    self.porcupine.frame_length,
                    exception_on_overflow=False
                )
                pcm = struct.unpack_from(
                    "h" * self.porcupine.frame_length,
                    pcm_bytes
                )

                if self.porcupine.process(pcm) >= 0:
                    logging.info("[WakeWord] Triggered!")
                    if self.callback:
                        self.callback()

            except Exception as e:
                logging.error(f"[WakeWord] Error: {e}")
                break

    def stop(self):
        self.running = False

        try:
            self.stream.stop_stream()
            self.stream.close()
        except:
            pass

        try:
            self.pa.terminate()
        except:
            pass

        try:
            self.porcupine.delete()
        except:
            pass

        logging.info("[WakeWord] Detector stopped")