"""
TTS Manager

High-level text-to-speech manager that wraps different engines:
    - PiperTTS: primary neural TTS backend
    - SystemTTS: OS-level fallback (SAPI / system voices)
    - VoiceSelector: helper to pick voices by hint

LanguageManager controls which voice should be used by calling selector.set_voice().
"""

import logging
from typing import Optional

from sebas.tts.tts_piper import PiperTTS
from sebas.tts.tts_system import SystemTTS
from sebas.tts.tts_selector import VoiceSelector


class TTSManager:
    """Central unified interface for all TTS engines."""

    def __init__(self, language_manager=None):
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
            # Primary neural TTS backend
            self.engine = PiperTTS()
            logging.info("TTSManager: using PiperTTS backend.")
        except Exception:
            # Fallback to system TTS engine
            logging.warning("PiperTTS unavailable, falling back to SystemTTS.")
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
        self.engine.speak(text)

    def set_voice(self, voice_hint: str) -> bool:
        """
        Try to select a voice by hint.

        Args:
            voice_hint: Any hint like 'male', 'british', 'en-gb',
                        or a specific voice name.

        Returns:
            True if a matching voice was found and applied, False otherwise.
        """
        return self.selector.set_voice(voice_hint)

    def list_voices(self):
        """
        Return a list of available voices for the current engine.

        This can be used by UI or configuration panels.
        """
        return self.engine.list_voices()

    def set_language(self, voice_hint: str) -> bool:
        """
        Optional helper: treat language change as a voice hint.

        Args:
            voice_hint: Hint that may encode language/voice.

        Returns:
            True if voice was updated, False otherwise.
        """
        return self.set_voice(voice_hint)