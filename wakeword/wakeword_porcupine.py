import logging
import pvporcupine
import pyaudio
import struct
import os


class PorcupineWakeWord:
    def __init__(self, keyword="Alfred"):
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")

        if not access_key:
            raise RuntimeError("PICOVOICE_ACCESS_KEY environment variable is not set")

        base_path = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_path, "models", f"{keyword}.ppn")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Wake-word model not found: {model_path}")

        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[model_path]
        )

        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

        logging.info(f"PorcupineWakeWord initialized with custom '{keyword}.ppn'")

    def detect(self):
        pcm = self.stream.read(
            self.porcupine.frame_length,
            exception_on_overflow=False
        )
        pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
        return self.porcupine.process(pcm) >= 0
