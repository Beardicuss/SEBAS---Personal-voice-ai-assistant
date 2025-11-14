import os
import logging
import numpy as np
import sounddevice as sd
import onnxruntime as ort
import json


class PiperRealTTS:
    """ONNX-based Piper/Kokoro TTS engine"""

    def __init__(self, model_path: str, config: dict):
        self.model_path = model_path
        self.config = config

        try:
            self.session = ort.InferenceSession(model_path)
        except Exception as e:
            logging.error(f"[PiperReal] Failed to load ONNX model: {e}")
            raise

    # ------------------------------------------------------------

    def speak(self, text: str):
        """Convert text → audio → play"""
        if not text:
            return

        try:
            audio = self._synthesize(text)
            self._play(audio)
        except Exception:
            logging.exception("[PiperReal] TTS failure")

    # ------------------------------------------------------------

    def _synthesize(self, text: str):
        """Run ONNX inference"""
        tokens = self._text_to_tokens(text)
        input_data = np.array(tokens, dtype=np.int64)

        outputs = self.session.run(None, {"input": input_data})
        audio = outputs[0].flatten()

        return audio

    # ------------------------------------------------------------

    def _text_to_tokens(self, text: str):
        """Basic tokenizer"""
        mapping = self.config.get("phoneme_id_map", {})

        tokens = []
        for char in text.lower():
            tokens.append(mapping.get(char, mapping.get(" ", 0)))

        return tokens

    # ------------------------------------------------------------

    def _play(self, audio):
        """Play audio via sounddevice"""
        sd.play(audio, 24000)
        sd.wait()
