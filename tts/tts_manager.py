
"""
TTS Manager

High-level text-to-speech manager that wraps different engines:
- PiperTTS: primary neural TTS backend
- SystemTTS: OS-level fallback (SAPI / system voices)
- VoiceSelector: helper to pick voices by hint
"""

from sebas.tts.tts_piper import PiperTTS
from sebas.tts.tts_system import SystemTTS
from sebas.tts.tts_selector import VoiceSelector


class TTSManager:
    """Central unified interface for all TTS engines."""

    def __init__(self):
        """
        Initialize primary TTS engine and voice selector.

        Logic:
        - Try PiperTTS as the main engine.
        - If PiperTTS fails, fall back to SystemTTS.
        - VoiceSelector operates on the chosen engine.
        """
        try:
            # Primary neural TTS backend
            self.engine = PiperTTS()
        except Exception:
            # Fallback to system TTS engine
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
            voice_hint: Any hint like 'male', 'british', 'en-gb', specific name, etc.

        Returns:
            True if a matching voice was found and applied, False otherwise.
        """
        return self.selector.set_voice(voice_hint)

    def list_voices(self):
        """
        Return a list of available voices for the current engine.

        This can be used by UI or config panels.
        """
        return self.engine.list_voices()