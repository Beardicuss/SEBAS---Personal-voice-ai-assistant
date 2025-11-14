"""
STT Manager

High-level speech-to-text manager that chooses the best available backend.
Current logic:
    - Try VoskRecognizer (offline STT)
    - If it fails, fall back to NoSTT dummy engine

LanguageManager can change STT model by calling set_language().
"""

import logging
from typing import Optional

from sebas.stt.stt_vosk import VoskRecognizer
from sebas.stt.stt_none import NoSTT


class STTManager:
    """Central unified interface for all STT engines."""

    def __init__(self, language_manager=None):
        """
        Initialize the STT engine with the best available backend.

        Args:
            language_manager: Optional reference to LanguageManager
                              for future integration.
        """
        self.language_manager = language_manager

        try:
            # Try to use Vosk-based recognizer (offline, local models)
            self.engine = VoskRecognizer()
            logging.info("STTManager: using VoskRecognizer backend.")
        except Exception:
            # If Vosk is not available, use dummy implementation
            logging.warning("Vosk unavailable, using dummy STT (NoSTT).")
            self.engine = NoSTT()

    def listen(self, timeout: int = 5) -> str:
        """
        Capture audio and return recognized text.

        This delegates to the underlying engine, so different backends
        can implement their own logic.

        Args:
            timeout: Optional timeout for listening operation (if supported).

        Returns:
            Recognized text or empty string.
        """
        # If specific engine supports timeout, you can pass it through here.
        if hasattr(self.engine, "listen"):
            try:
                return self.engine.listen(timeout=timeout)
            except TypeError:
                # Fallback if backend does not support timeout parameter
                return self.engine.listen()
        return ""

    def set_language(self, stt_model: str):
        """
        Switch the internal STT model based on language profile.

        Args:
            stt_model: Model identifier (e.g. 'vosk-en', 'vosk-ru')
        """
        if hasattr(self.engine, "set_model"):
            try:
                self.engine.set_model(stt_model)
                logging.info(f"STTManager: switched model to {stt_model}")
            except Exception:
                logging.exception("Failed to switch STT model.")