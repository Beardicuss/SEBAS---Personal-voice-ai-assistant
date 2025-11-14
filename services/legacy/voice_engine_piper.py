import logging

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    logging.error("pyttsx3 is not installed; TTS will be disabled")


class PiperVoiceEngine:
    """
    Thin wrapper around a local TTS engine.
    Right now it uses pyttsx3, but the class name is kept as PiperVoiceEngine
    so we can later swap it to real Piper / Kokoro / whatever.
    """

    def __init__(self):
        self.engine = None
        if pyttsx3 is None:
            logging.error("PiperVoiceEngine: pyttsx3 backend not available")
            return
        try:
            self.engine = pyttsx3.init()
            # reasonable defaults; will be overridden by profile
            self.engine.setProperty("rate", 160)
            self.engine.setProperty("volume", 1.0)
            logging.info("PiperVoiceEngine initialized with pyttsx3 backend")
        except Exception:
            logging.exception("Failed to initialize pyttsx3 engine")
            self.engine = None

    def set_params(self, rate=None, volume=None):
        if not self.engine:
            return
        try:
            if rate is not None:
                self.engine.setProperty("rate", int(rate))
            if volume is not None:
                v = max(0.0, min(1.0, float(volume)))
                self.engine.setProperty("volume", v)
        except Exception:
            logging.exception("Failed to set TTS parameters")

    def speak(self, text: str, language: str = "en") -> bool:
        """
        Speaks the text synchronously. Returns True on success, False on failure.
        'language' is ignored for now but kept for future multi-voice backends.
        """
        if not self.engine:
            logging.error("PiperVoiceEngine.speak called but engine is not initialized")
            return False
        try:
            if not text:
                return True
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception:
            logging.exception("PiperVoiceEngine.speak failed")
            return False

    def stop(self):
        if not self.engine:
            return
        try:
            self.engine.stop()
        except Exception:
            logging.exception("Failed to stop TTS engine")
