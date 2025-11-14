import logging

from sebas.stt.stt_vosk import VoskRecognizer
from sebas.stt.stt_none import NoSTT


class STTManager:
    def __init__(self, language_manager=None):
        self.language_manager = language_manager

        try:
            self.engine = VoskRecognizer()
            logging.info("STTManager: using VoskRecognizer backend.")
        except Exception:
            logging.warning("Vosk unavailable, using NoSTT.")
            self.engine = NoSTT()

    def listen(self, timeout: int = 5) -> str:
        """Vosk has no timeout — ignoring it."""
        try:
            return self.engine.listen()
        except Exception:
            logging.exception("STTManager.listen failed")
            return ""

    def set_language(self, stt_model: str):
        """Recreate recognizer with new model."""
        try:
            self.engine = VoskRecognizer(stt_model)
            logging.info(f"STTManager: switched model to {stt_model}")
        except Exception:
            logging.exception("STTManager: failed to switch model")
            self.engine = NoSTT()