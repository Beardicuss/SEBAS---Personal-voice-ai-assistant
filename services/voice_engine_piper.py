"""
Piper Voice Engine — offline TTS for Sebas with male 'butler' voices.
Default: English. Supported: en, ru, de.
Handles both PiperVoice APIs: speak(text, path) and synthesize(...) -> Iterable[AudioChunk].
"""

import os
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
        # Clear any old cached instance for that model
        if model_name in self._cache:
            self._cache.pop(model_name, None)
        logging.info("[Piper] Voice for '%s' set to '%s'", lang, model_name)

    def get_available_languages(self) -> List[str]:
        return sorted(self.voice_map.keys())

    def _load_voice(self, model: str) -> Optional[PiperVoice]:
        """
        Safe load Piper model from sebas/voices/<model>.json + <model>.onnx
        Automatically fixes model names like:
          en_US-lessac-medium.json
          en_US-lessac-medium.onnx
          en_US-lessac-medium.json.json
        """

        try:
            # ---------------------------
            # FIX: Normalize model name
            # ---------------------------
            model = model.strip()

            # Remove garbage extensions
            for ext in (".json", ".onnx"):
                if model.endswith(ext):
                    model = model[:-len(ext)]

            # Remove double-extension mutation (json.json)
            while model.endswith(".json"):
                model = model[:-5]

            # Cache check
            if model in self._cache:
                return self._cache[model]

            logging.info("[Piper] Loading model: %s", model)

            # Build voices dir
            voices_dir = os.path.join(os.path.dirname(__file__), "..", "voices")
            voices_dir = os.path.abspath(voices_dir)

            # Build paths
            json_path = os.path.join(voices_dir, f"{model}.json")
            onnx_path = os.path.join(voices_dir, f"{model}.onnx")

            # Validation
            if not os.path.exists(json_path):
                raise FileNotFoundError(f"[Piper] Missing JSON config: {json_path}")
            if not os.path.exists(onnx_path):
                raise FileNotFoundError(f"[Piper] Missing ONNX model: {onnx_path}")

            # Load Piper model
            voice = PiperVoice.load(json_path)

            # Store in cache
            self._cache[model] = voice
            return voice

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
        iterator = iter(chunks)
        try:
            first_chunk = next(iterator)
        except StopIteration:
            raise RuntimeError("Empty audio chunk stream")

        sr = getattr(first_chunk, "sample_rate", 22050)
        ch = getattr(first_chunk, "num_channels", 1)
        sw = getattr(first_chunk, "sample_width", 2)

        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(int(ch))
            wf.setsampwidth(int(sw))
            wf.setframerate(int(sr))

            def write_piece(x: Any) -> None:
                if hasattr(x, "audio"):
                    data = x.audio
                elif hasattr(x, "data"):
                    data = x.data
                else:
                    data = x
                if isinstance(data, memoryview):
                    data = data.tobytes()
                elif isinstance(data, bytearray):
                    data = bytes(data)
                elif not isinstance(data, (bytes, bytearray)):
                    try:
                        data = bytes(data)
                    except Exception:
                        raise TypeError(f"Unsupported audio chunk type: {type(x)}")
                wf.writeframesraw(data)

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
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{lang}.wav") as tmp:
                out = tmp.name

            if hasattr(voice, "speak"):
                voice.speak(text, out)  # type: ignore[attr-defined]
            else:
                data = voice.synthesize(text)  # type: ignore[attr-defined]
                if isinstance(data, (bytes, bytearray, memoryview)):
                    with open(out, "wb") as f:
                        f.write(bytes(data))
                else:
                    self._concat_chunks_to_wav(data, out)

            if _ws:
                _ws.PlaySound(out, _ws.SND_FILENAME)
            return True

        except Exception:
            logging.exception("[Piper] Synthesis/playback error.")
            return False
