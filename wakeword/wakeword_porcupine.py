import logging
import pvporcupine
import pyaudio
import struct
import os


class PorcupineWakeWord:
    def __init__(self, keyword="jarvis"):
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")

        if not access_key:
            raise RuntimeError("PICOVOICE_ACCESS_KEY environment variable is not set!")

        # built-in keyword models: jarvis, computer, pico, bumblebee, ok google
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword]
        )

        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

        logging.info(f"PorcupineWakeWord initialized with keyword '{keyword}'")

    def detect(self):
        pcm = self.stream.read(
            self.porcupine.frame_length,
            exception_on_overflow=False
        )
        pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
        result = self.porcupine.process(pcm)
        return result >= 0