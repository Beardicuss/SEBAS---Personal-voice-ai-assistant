"""
Piper Voice Engine — offline TTS for Sebas with male 'butler' voices.
Default: English. Supported: en, ru, de.
Handles both PiperVoice APIs: speak(text, path) and synthesize(...) -> Iterable[AudioChunk].
"""

import logging
import tempfile
import wave
from typing import List, Dict, Optional, Iterable, Any
from piper import PiperVoice

try:
    import winsound as _ws
except Exception:
    _ws = None

# Male voice mapping
DEFAULT_VOICE_MAP: Dict[str, str] = {
    "en": "en_US-lessac-medium",     # male EN
    "ru": "ru_RU-denis-medium",      # male RU (alternatives: dmitri, ruslan)
    "de": "de_DE-thorsten-medium",   # male DE
}

DEFAULT_LANGUAGE = "en"


class PiperVoiceEngine:
    def __init__(self, voice_map: Optional[Dict[str, str]] = None, default_language: str = DEFAULT_LANGUAGE):
        self.voice_map: Dict[str, str] = (voice_map or DEFAULT_VOICE_MAP).copy()
        self.default_language: str = (default_language or DEFAULT_LANGUAGE).lower()
        self._cache: Dict[str, PiperVoice] = {}
        logging.info("[Piper] Voice map: %s | default: %s", self.voice_map, self.default_language)

    def set_default_language(self, language: str) -> None:
        self.default_language = (language or self.default_language).lower()
        logging.info("[Piper] Default language set to: %s", self.default_language)

    def set_voice_for_language(self, language: str, model_name: str) -> None:
        lang = language.lower()
        self.voice_map[lang] = model_name
        self._cache.pop(model_name, None)
        logging.info("[Piper] Voice for '%s' set to '%s'", lang, model_name)

    def get_available_languages(self) -> List[str]:
        return sorted(self.voice_map.keys())

    def _load_voice(self, model: str) -> Optional[PiperVoice]:
        try:
            if model not in self._cache:
                logging.info("[Piper] Loading model: %s", model)
                self._cache[model] = PiperVoice.load(model)
            return self._cache[model]
        except Exception:
            logging.exception("[Piper] Failed to load model: %s", model)
            return None

    def _voice_for_language(self, language: Optional[str]) -> Optional[PiperVoice]:
        lang = (language or self.default_language or "en").lower()
        model = self.voice_map.get(lang, self.voice_map.get("en", "en_US-lessac-medium"))
        return self._load_voice(model)

    # -------- helpers for synthesize(AudioChunk...) -> WAV --------

    @staticmethod
    def _concat_chunks_to_wav(chunks: Iterable[Any], out_path: str) -> None:
        """
        Build a valid WAV file from Piper AudioChunk stream.
        AudioChunk is expected to expose:
          - .audio (bytes-like PCM) or .data (bytes-like) or be bytes itself
          - .sample_rate (int)
          - .num_channels (int)
          - .sample_width (int)  # bytes per sample (usually 2)
        We will read params from the first chunk and assume constant over the stream.
        """
        first_chunk: Optional[Any] = None
        # Peek first chunk
        iterator = iter(chunks)
        try:
            first_chunk = next(iterator)
        except StopIteration:
            raise RuntimeError("Empty audio chunk stream")

        # Extract params from first chunk with defensive defaults
        sr = getattr(first_chunk, "sample_rate", 22050)
        ch = getattr(first_chunk, "num_channels", 1)
        sw = getattr(first_chunk, "sample_width", 2)  # bytes per sample

        # Prepare wave writer
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(int(ch))
            wf.setsampwidth(int(sw))
            wf.setframerate(int(sr))

            def write_piece(x: Any) -> None:
                # Try common attribute names first
                if hasattr(x, "audio"):
                    data = x.audio
                elif hasattr(x, "data"):
                    data = x.data
                else:
                    data = x  # might be bytes/bytearray/memoryview
                # Normalize to bytes
                if isinstance(data, memoryview):
                    data = data.tobytes()
                elif isinstance(data, bytearray):
                    data = bytes(data)
                elif not isinstance(data, (bytes, bytearray)):
                    # Last-ditch attempt
                    try:
                        data = bytes(data)
                    except Exception:
                        raise TypeError(f"Unsupported audio chunk type: {type(x)}")
                wf.writeframesraw(data)

            # write first + rest
            write_piece(first_chunk)
            for chunk in iterator:
                write_piece(chunk)

    # ----------------------------------------------------------------

    def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Synthesize and play speech; supports both Piper APIs."""
        voice = self._voice_for_language(language)
        if not voice:
            return False
        lang = (language or self.default_language or "en").lower()

        try:
            # create temp wav path
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{lang}.wav") as tmp:
                out = tmp.name

            # API variant A: voice.speak(text, path)
            if hasattr(voice, "speak"):
                voice.speak(text, out)  # type: ignore[attr-defined]
            else:
                # API variant B: voice.synthesize(...) -> Iterable[AudioChunk] or bytes-like
                data = voice.synthesize(text)  # type: ignore[attr-defined]
                if isinstance(data, (bytes, bytearray, memoryview)):
                    with open(out, "wb") as f:
                        f.write(bytes(data))
                else:
                    # Iterable[AudioChunk]: assemble to WAV
                    self._concat_chunks_to_wav(data, out)

            # play no matter which branch produced the file
            if _ws:
                _ws.PlaySound(out, _ws.SND_FILENAME)
            return True

        except Exception:
            logging.exception("[Piper] Synthesis/playback error.")
            return False
