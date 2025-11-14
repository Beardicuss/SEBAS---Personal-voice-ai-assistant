import json
import sounddevice as sd
import numpy as np
import onnxruntime as ort
import logging
import os


class PiperTTS:
    """
    True Piper neural TTS engine with chaos effects.
    """

    def __init__(self, model_path="voices/piper/en_US-lessac-medium.onnx",
                       config_path="voices/piper/en_US-lessac-medium.json"):

        if not os.path.exists(model_path):
            raise FileNotFoundError(model_path)

        if not os.path.exists(config_path):
            raise FileNotFoundError(config_path)

        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.sample_rate = self.config.get("audio", {}).get("sample_rate", 22050)

        logging.info(f"PiperTTS loaded: {model_path}")

    # ----------------------------------------------------
    # SHEOGORATH EFFECT
    # ----------------------------------------------------
    def _apply_sheogorath_magic(self, audio):
        audio = audio.astype(np.float32)

        # Pitch wobble
        wobble = np.sin(np.linspace(0, 20, len(audio))) * 0.015
        audio = audio * (1.0 + wobble)

        # Whisper noise
        noise = (np.random.randn(len(audio)) * 0.002).astype(np.float32)
        audio = audio + noise

        # Light distortion
        audio = np.tanh(audio * 2.0)

        return audio

    # ----------------------------------------------------
    def speak(self, text: str):
        if not text:
            return

        # Encode text as sequence of characters
        encoded = np.array([ord(c) for c in text], dtype=np.int64)[None, :]

        # ONNX inference
        result = self.session.run(None, {"input": encoded})
        audio = np.array(result[0]).astype(np.float32)

        # Apply chaotic Sheogorath effects
        audio = self._apply_sheogorath_magic(audio)

        try:
            sd.play(audio, self.sample_rate)
            sd.wait()
        except Exception as e:
            logging.error(f"Piper audio playback error: {e}")

    # Compatibility with TTSManager
    def list_voices(self):
        return ["piper-default"]

    def set_voice(self, voice_id):
        return True