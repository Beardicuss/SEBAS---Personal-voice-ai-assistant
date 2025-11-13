
"""
STT Manager

High-level speech-to-text manager that chooses the best available backend.
Current logic:
- Try VoskRecognizer (offline STT)
- If it fails, fall back to NoSTT dummy engine
"""

import logging
from sebas.stt.stt_vosk import VoskRecognizer
from sebas.stt.stt_none import NoSTT


class STTManager:
    """Central unified interface for all STT engines."""

    def __init__(self):
        """Initialize the STT engine with the best available backend."""
        try:
            # Try to use Vosk-based recognizer (offline, local models)
            self.engine = VoskRecognizer()
            logging.info("STTManager: using VoskRecognizer backend.")
        except Exception:
            # If Vosk is not available, use dummy implementation
            logging.warning("Vosk unavailable, using dummy STT (NoSTT).")
            self.engine = NoSTT()

    def listen(self):
        """
        Capture audio and return recognized text.

        This delegates to the underlying engine, so different backends
        can implement their own logic.
        """
        return self.engine.listen()