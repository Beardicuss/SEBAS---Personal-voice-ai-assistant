import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
import pyaudio

# try:
#     from elevenlabs import generate, set_api_key, voices
#     from elevenlabs import ElevenLabsError  # type: ignore
#     ELEVENLABS_AVAILABLE = True
# except Exception:
#     ELEVENLABS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except Exception:
    PYTTSX3_AVAILABLE = False


class BaseVoiceEngine(ABC):
    @abstractmethod
    def speak(self, text: str, language: str = "en") -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_available_languages(self) -> List[str]:
        raise NotImplementedError


# class ElevenLabsVoiceEngine(BaseVoiceEngine):
#     def __init__(self):
#         if not ELEVENLABS_AVAILABLE:
#             raise RuntimeError("ElevenLabs not installed")
#         self.api_key = os.getenv("ELEVEN_API_KEY")
#         if not self.api_key:
#             raise ValueError("ELEVEN_API_KEY environment variable not set")
#         set_api_key(self.api_key)
#         # Use turbo model optimized for low latency streaming by default
#         self.model = os.getenv("ELEVEN_MODEL", "eleven_turbo_v2")
#         # Simple default mapping (user can customize in ElevenLabs dashboard)
#         self.VOICE_MAP = {
#             # Default calm male British
#             "en": os.getenv("ELEVEN_VOICE_EN", "Adam"),
#             "es": os.getenv("ELEVEN_VOICE_ES", "Gigi"),
#             "fr": os.getenv("ELEVEN_VOICE_FR", "Charlotte"),
#             "de": os.getenv("ELEVEN_VOICE_DE", "Bernd"),
#             "it": os.getenv("ELEVEN_VOICE_IT", "Giovanni"),
#             "pt": os.getenv("ELEVEN_VOICE_PT", "Cristiano"),
#             "pl": os.getenv("ELEVEN_VOICE_PL", "Krzysztof"),
#             "hi": os.getenv("ELEVEN_VOICE_HI", "Aria"),
#             "ja": os.getenv("ELEVEN_VOICE_JA", "Takumi"),
#             "ko": os.getenv("ELEVEN_VOICE_KO", "Soojin"),
#             "zh": os.getenv("ELEVEN_VOICE_ZH", "Li"),
#             "ar": os.getenv("ELEVEN_VOICE_AR", "Omar"),
#             "tr": os.getenv("ELEVEN_VOICE_TR", "Yigit"),
#             "nl": os.getenv("ELEVEN_VOICE_NL", "Daan"),
#             "sv": os.getenv("ELEVEN_VOICE_SV", "Erik"),
#             "no": os.getenv("ELEVEN_VOICE_NO", "Kari"),
#             "ru": os.getenv("ELEVEN_VOICE_RU", "Artem"),
#             "ka": os.getenv("ELEVEN_VOICE_KA", "Natia"),
#         }
#         self._warn_missing_voices()

#     def _warn_missing_voices(self):
#         try:
#             available = [v.name for v in voices()]
#             for lang, name in self.VOICE_MAP.items():
#                 if name and name not in available:
#                     logging.debug(f"Voice '{name}' for {lang} not found in ElevenLabs account")
#         except Exception:
#             pass

#     def speak(self, text: str, language: str = "en") -> bool:
#         try:
#             voice_name = self.VOICE_MAP.get(language, self.VOICE_MAP.get("en", "Antoni"))
#             # Streaming for lower latency response
#             from elevenlabs import stream as el_stream  # type: ignore
#             try:
#                 opt = int(os.getenv('ELEVEN_STREAM_OPT', '2'))
#             except Exception:
#                 opt = 2
#             audio_stream = generate(
#                 text=text,
#                 voice=voice_name,
#                 model=self.model,
#                 stream=True,
#                 optimize_streaming_latency=opt
#             )
#             el_stream(audio_stream)
#             return True
#         except ElevenLabsError as e:  # type: ignore
#             logging.error(f"ElevenLabs error: {e}")
#             return False
#         except Exception:
#             logging.exception("ElevenLabs playback failed")
#             return False

#     def get_available_languages(self) -> List[str]:
#         return list(self.VOICE_MAP.keys())


class FallbackVoiceEngine(BaseVoiceEngine):
    def __init__(self):
        if not PYTTSX3_AVAILABLE:
            raise RuntimeError("pyttsx3 not available for fallback")
        self.engine = pyttsx3.init()  # type: ignore
        self.engine.setProperty('rate', 150)

    def speak(self, text: str, language: str = "en") -> bool:
        try:
            voices = self.engine.getProperty('voices')
            if not isinstance(voices, (list, tuple)):
                voices = [voices] if voices else []

            for v in voices:
                name = (getattr(v, 'name', '') or '').lower()
                vid = (getattr(v, 'id', '') or '').lower()
                if language.lower() in name or language.lower() in vid:
                    self.engine.setProperty('voice', getattr(v, 'id', ''))
                    break

            self.engine.say(text)
            self.engine.runAndWait()
            return True

        except Exception:
            logging.exception("Fallback TTS failed")
            return False


    def get_available_languages(self) -> List[str]:
        return ["en"]


class VoiceEngineManager:
    def __init__(self):
        self.eleven = None
        self.fallback = None
        self.use_eleven = False
        # if ELEVENLABS_AVAILABLE and os.getenv("ELEVEN_API_KEY"):
        #     try:
        #         self.eleven = ElevenLabsVoiceEngine()
        #         self.use_eleven = True
        #         logging.info("ElevenLabs engine initialized")
        #     except Exception as e:
        #         logging.warning(f"ElevenLabs init failed: {e}")
        if PYTTSX3_AVAILABLE:
            try:
                self.fallback = FallbackVoiceEngine()
                if not self.use_eleven:
                    logging.info("Using fallback TTS engine")
            except Exception:
                logging.exception("Fallback engine init failed")

    @property
    def current_engine(self) -> Optional[BaseVoiceEngine]:
        if self.use_eleven and self.eleven:
            return self.eleven
        return self.fallback

    def speak(self, text: str, language: str = "en") -> bool:
        eng = self.current_engine
        if not eng:
            return False
        ok = eng.speak(text, language)
        if not ok and self.use_eleven and self.fallback:
            logging.info("TTS falling back to local engine")
            return self.fallback.speak(text, language)
        return ok

    def toggle_engine(self) -> str:
        if self.eleven and self.fallback:
            self.use_eleven = not self.use_eleven
            return f"Switched to {'ElevenLabs' if self.use_eleven else 'Fallback'} engine"
        return "Only one engine available"

    def get_supported_languages(self) -> List[str]:
        eng = self.current_engine
        return eng.get_available_languages() if eng else ["en"]

