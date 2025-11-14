import logging
from .tts_system import SystemTTS


class TTSManager:
    """Unified text-to-speech manager (SystemTTS only for now)."""

    def __init__(self, language_manager=None):
        self.language_manager = language_manager

        # Only SystemTTS is used now
        try:
            self.engine = SystemTTS()
            logging.info("TTSManager: using SystemTTS backend.")
        except Exception:
            logging.exception("Failed to initialize SystemTTS")
            self.engine = None

    def speak(self, text: str):
        if not text:
            return
        if not self.engine:
            logging.error("No TTS engine available.")
            return
        self.engine.speak(text)

    def set_voice(self, voice_hint: str):
        """Matches a voice by partial name."""
        if not self.engine:
            return False

        available = self.engine.list_voices()

        for v in available:
            if voice_hint.lower() in v.name.lower():
                self.engine.set_voice(v.id)
                return True

        return False

    def list_voices(self):
        if not self.engine:
            return []
        return self.engine.list_voices()