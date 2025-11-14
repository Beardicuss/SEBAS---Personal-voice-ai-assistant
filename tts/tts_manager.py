"""
TTS Manager

High-level text-to-speech manager that wraps different engines:
    - PiperTTS: primary neural TTS backend (currently pyttsx3-based wrapper)
    - SystemTTS: OS-level fallback (SAPI / system voices)
    - VoiceSelector: helper to pick voices by hint

LanguageManager controls which voice should be used by calling set_voice().
"""

import logging
from typing import Optional

from sebas.tts.tts_piper import PiperTTS
from sebas.tts.tts_system import SystemTTS
from sebas.tts.tts_selector import VoiceSelector


class TTSManager:
    """Central unified interface for all TTS engines."""

    def __init__(self, language_manager: Optional[object] = None):
        """
        Initialize primary TTS engine and voice selector.

        Logic:
            - Try PiperTTS as the main engine.
            - If PiperTTS fails, fall back to SystemTTS.
            - VoiceSelector operates on the chosen engine.

        Args:
            language_manager: Optional reference to LanguageManager
                              for future integration.
        """
        self.language_manager = language_manager

        try:
            # Primary backend (currently pyttsx3-based wrapper)
            self.engine = PiperTTS()
            logging.info("TTSManager: using PiperTTS backend.")
        except Exception:
            # Fallback to system TTS engine
            logging.exception("PiperTTS unavailable, falling back to SystemTTS.")
            self.engine = SystemTTS()

        # Voice selector uses the currently active engine
        self.selector = VoiceSelector(self.engine)

    def speak(self, text: str):
        """
        Speak a text string using the active TTS engine.

        Args:
            text: Text to be spoken aloud.
        """
        if not text:
            return
        try:
            self.engine.speak(text)
        except Exception:
            logging.exception("TTSManager.speak failed")

    def set_voice(self, voice_hint: str) -> bool:
        """
        Try to select a voice by hint.

        Args:
            voice_hint: Any hint like 'male', 'british', 'en-gb',
                        or a specific voice name.

        Returns:
            True if a matching voice was found and applied, False otherwise.
        """
        try:
            return self.selector.set_voice(voice_hint)
        except Exception:
            logging.exception("TTSManager.set_voice failed")
            return False

    def list_voices(self):
        """
        Return a list of available voices for the current engine.

        This can be used by UI or configuration panels.
        """
        try:
            return self.engine.list_voices()
        except Exception:
            logging.exception("TTSManager.list_voices failed")
            return []

    def set_language(self, voice_hint: str) -> bool:
        """
        Optional helper: treat language change as a voice hint.

        Args:
            voice_hint: Hint that may encode language/voice.

        Returns:
            True if voice was updated, False otherwise.
        """
        return self.set_voice(voice_hint)