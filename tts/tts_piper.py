import logging
import pyttsx3

class PiperTTS:
    """Wrapper for Piper/Kokoro using pyttsx3 fallback."""

    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text: str):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            logging.exception("PiperTTS failed")

    def list_voices(self):
        return self.engine.getProperty("voices")

    def set_voice(self, voice_id):
        self.engine.setProperty("voice", voice_id)