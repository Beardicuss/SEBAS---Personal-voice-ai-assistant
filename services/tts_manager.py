"""
Central TTS manager for SEBAS.
Supports multiple engines (pyttsx3, piper, elevenlabs later).
"""

import logging

class TTSManager:
    def __init__(self, engine=None):
        """
        engine — объект, у которого обязательно есть метод:
        speak(text, language="en")
        """
        self.engine = engine

    def set_engine(self, engine):
        """Switch TTS engine at runtime."""
        self.engine = engine

    def speak(self, text, language="en"):
        if not self.engine:
            logging.error("TTSManager: No TTS engine set.")
            return

        try:
            self.engine.speak(text, language=language)
        except Exception:
            logging.exception("TTSManager speak() failed")

    def stop(self):
        if not self.engine:
            return
        if hasattr(self.engine, "stop"):
            try:
                self.engine.stop()
            except Exception:
                pass
