import json
import os
import vosk


class VoskRecognizer:
    """Thin wrapper for VOSK engine"""

    def __init__(self, model_path: str):
        if not model_path:
            raise ValueError("Vosk model path cannot be None")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Vosk STT model missing: {model_path}")

        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)

    # ------------------------------------------------------------

    def set_model(self, model_path: str):
        """Reload STT model"""
        self.__init__(model_path)

    # ------------------------------------------------------------

    def recognize(self, pcm_bytes: bytes):
        """Process PCM → text"""
        if self.recognizer.AcceptWaveform(pcm_bytes):
            data = json.loads(self.recognizer.Result())
            return data.get("text", "")
        return ""
