import logging
from typing import Optional

from .voice_engine_piper import PiperVoiceEngine
from .voice_manager import VoiceManager


class VoiceSystem:
    """
    High-level voice system wrapper used by Sebas.

    - Uses PiperVoiceEngine (currently pyttsx3 backend) for actual audio
    - Uses VoiceManager to store profiles (rate, volume)
    """

    def __init__(self, base_engine: Optional[object] = None):
        """
        base_engine is kept for backward compatibility and ignored for now.
        """
        self.engine = PiperVoiceEngine()
        self.manager = VoiceManager()
        self.apply_current()

    def speak(self, text: str, language: str = "en") -> bool:
        """
        Main entry point used by Sebas: speak text.
        Returns True on success, False on failure.
        """
        return self.engine.speak(text, language=language)

    def stop(self):
        if hasattr(self.engine, "stop"):
            self.engine.stop()

    def set_profile(self, name: str) -> str:
        """
        Change current profile and apply its parameters.
        Returns the profile name actually set.
        """
        key = self.manager.set_profile(name)
        self.apply_current()
        return key

    def list_profiles(self):
        return self.manager.list_profiles()

    def apply_current(self):
        """
        Apply current VoiceProfile to the TTS backend.
        """
        try:
            profile = self.manager.get_profile()
            self.engine.set_params(rate=profile.rate, volume=profile.volume)
        except Exception:
            logging.exception("Failed to apply current voice profile")

    def adjust(self, rate=None, volume=None, pitch_delta=None):
        """
        Adjust current voice settings (used by Sebas.adjust_voice).
        """
        profile = self.manager.adjust(rate=rate, volume=volume, pitch_delta=pitch_delta)
        try:
            self.engine.set_params(rate=profile.rate, volume=profile.volume)
        except Exception:
            logging.exception("Failed to apply adjusted voice profile")
        return profile
    def get_voices(self):
        """
        Return list of backend voices (pyttsx3 voices or empty list).
        Used by main.py for listing and language selection.
        """
        try:
            backend = getattr(self.engine, "engine", None)
            if backend is None:
                return []
            return backend.getProperty("voices")
        except Exception:
            logging.exception("Failed to get voices from backend")
            return []

    def set_voice_id(self, voice_id: str):
        """
        Set backend voice id directly.
        """
        try:
            backend = getattr(self.engine, "engine", None)
            if backend is None:
                return
            backend.setProperty("voice", voice_id)
        except Exception:
            logging.exception("Failed to set voice id on backend")
