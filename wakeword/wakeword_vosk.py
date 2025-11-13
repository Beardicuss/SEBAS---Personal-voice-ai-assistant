import logging
import vosk
import pyaudio
import json

class VoskWakeWord:
    def __init__(self, keyword="sebas"):
        self.keyword = keyword.lower()
        self.model = vosk.Model("model/vosk-small")
        self.recog = vosk.KaldiRecognizer(self.model, 16000)
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=4000
        )

    def detect(self):
        data = self.stream.read(4000, exception_on_overflow=False)
        if self.recog.AcceptWaveform(data):
            res = json.loads(self.recog.Result())
            text = res.get("text", "").lower()
            return self.keyword in text
        return False