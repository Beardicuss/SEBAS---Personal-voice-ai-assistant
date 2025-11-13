import logging
import pvporcupine
import pyaudio
import struct

class PorcupineWakeWord:
    def __init__(self, keyword="sebas"):
        self.porcupine = pvporcupine.create(keywords=[keyword])
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

    def detect(self):
        pcm = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
        result = self.porcupine.process(pcm)
        return result >= 0