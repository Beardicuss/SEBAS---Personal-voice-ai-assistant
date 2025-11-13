"""
Voice Engine Manager — Piper-only (male voices).
"""

import logging
from typing import Optional, List
from abc import ABC, abstractmethod

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except Exception:
    PYTTSX3_AVAILABLE = False

from services.voice_engine_piper import PiperVoiceEngine


class BaseVoiceEngine(ABC):
    @abstractmethod
    def speak(self, text: str, language: str = "en") -> bool: ...
    @abstractmethod
    def get_available_languages(self) -> List[str]: ...


class FallbackVoiceEngine(BaseVoiceEngine):
    def __init__(self):
        if not PYTTSX3_AVAILABLE:
            raise RuntimeError("pyttsx3 not available")
        self.engine = pyttsx3.init()  # type: ignore
        self.engine.setProperty("rate", 150)

    def speak(self, text: str, language: str = "en") -> bool:
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception:
            logging.exception("[Fallback] TTS error")
            return False

    def get_available_languages(self) -> List[str]:
        return ["en"]


class VoiceEngineManager:
    """Primary Piper, optional pyttsx3 fallback."""

    primary: Optional[PiperVoiceEngine]
    fallback: Optional[FallbackVoiceEngine]

    def __init__(self):
        self.primary = PiperVoiceEngine()
        self.fallback = FallbackVoiceEngine() if PYTTSX3_AVAILABLE else None
        logging.info("[Manager] Piper ready. Fallback: %s", bool(self.fallback))

    @property
    def current_engine(self):
        return self.primary or self.fallback

    def speak(self, text: str, language: str = "en") -> bool:
        eng = self.current_engine
        if not eng:
            return False
        ok = eng.speak(text, language)  # type: ignore[attr-defined]
        if not ok and self.fallback and eng is not self.fallback:
            logging.info("[Manager] Switching to fallback TTS.")
            return self.fallback.speak(text, language)
        return ok

    def get_supported_languages(self) -> List[str]:
        eng = self.current_engine
        return eng.get_available_languages() if eng else ["en"]

    # pyttsx3 compatibility shims (safe no-ops if fallback absent)
    def setProperty(self, name: str, value):
        e = getattr(getattr(self, "fallback", None), "engine", None)
        if e and hasattr(e, "setProperty"):
            return e.setProperty(name, value)

    def getProperty(self, name: str):
        e = getattr(getattr(self, "fallback", None), "engine", None)
        if e and hasattr(e, "getProperty"):
            return e.getProperty(name)

    def stop(self):
        e = getattr(getattr(self, "fallback", None), "engine", None)
        if e and hasattr(e, "stop"):
            return e.stop()