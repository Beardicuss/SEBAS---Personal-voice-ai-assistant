import speech_recognition as sr
import logging

class VoskRecognizer:
    def __init__(self, model_name: str = None):
        self.model_name = model_name
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen(self):
        try:
            with self.microphone as src:
                audio = self.recognizer.listen(src)
            return self.recognizer.recognize_vosk(audio)
        except Exception:
            logging.exception("Vosk STT failed")
            return ""