
"""
Language Manager
Controls:
    - Current system language
    - Auto-detection from text
    - Synchronization with STT and TTS modules
"""

import re

SUPPORTED_LANGS = {
    "en": {
        "name": "English",
        "stt_model": "vosk-en",
        "tts_voice": "en-uk-male",
    },
    "ru": {
        "name": "Russian",
        "stt_model": "vosk-ru",
        "tts_voice": "ru-deep-male",
    },
    "ja": {
        "name": "Japanese",
        "stt_model": "vosk-ja",
        "tts_voice": "ja-soft-female",
    },
    "ka": {
        "name": "Georgian",
        "stt_model": "vosk-ka",
        "tts_voice": "ka-male",
    }
}


class LanguageManager:
    """
    Controls SEBAS language flow:
        - STT → choose model
        - TTS → choose voice
        - NLU → normalize text
    """

    def __init__(self, default_lang="en"):
        self.current_lang = default_lang
        self.stt = None   # will be linked by main.py
        self.tts = None   # will be linked by main.py

    # ------------------------------------------------------------
    # Linking engine managers (called from main.py)
    # ------------------------------------------------------------
    def bind_stt(self, stt_manager):
        self.stt = stt_manager

    def bind_tts(self, tts_manager):
        self.tts = tts_manager

    # ------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------
    def detect_language(self, text: str):
        """Primitive detection. Replace with fastText later."""
        t = text.lower()

        if re.search(r"[а-яё]", t):
            return self.set_language("ru")
        if re.search(r"[ぁ-ゔァ-ヴ]", t):
            return self.set_language("ja")
        if re.search(r"მ|ქ|წ|ჭ|ღ", t):
            return self.set_language("ka")

        return self.set_language("en")

    # ------------------------------------------------------------
    # Set new language (full pipeline: STT+TTS switch)
    # ------------------------------------------------------------
    def set_language(self, lang_code: str) -> bool:
        if lang_code not in SUPPORTED_LANGS:
            return False

        self.current_lang = lang_code
        profile = SUPPORTED_LANGS[lang_code]

        # Switch STT model
        if self.stt:
            self.stt.set_language(profile["stt_model"])

        # Switch TTS voice
        if self.tts:
            self.tts.selector.set_voice(profile["tts_voice"])

        return True

    # ------------------------------------------------------------
    def get_current_language(self):
        return self.current_lang

    def get_current_language_name(self):
        return SUPPORTED_LANGS[self.current_lang]["name"]