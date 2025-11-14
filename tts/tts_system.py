import pyttsx3
import logging


class SystemTTS:
    """Stable Windows voice engine using pyttsx3."""

    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty("voices")
            if voices:
                # Pick first voice, but can be overridden
                self.engine.setProperty("voice", voices[0].id)
            logging.info("SystemTTS initialized.")
        except Exception:
            logging.exception("SystemTTS initialization failed.")
            self.engine = None

    def speak(self, text: str):
        if not self.engine:
            logging.error("SystemTTS engine is not available.")
            return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            logging.exception("SystemTTS speak() failed")

    def list_voices(self):
        if not self.engine:
            return []
        return self.engine.getProperty("voices")

    def set_voice(self, voice_id: str):
        if not self.engine:
            return False
        self.engine.setProperty("voice", voice_id)
        return True
