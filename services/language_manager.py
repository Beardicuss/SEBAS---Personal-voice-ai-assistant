import logging
from typing import List


try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    DetectorFactory.seed = 0  # deterministic
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False


class LanguageManager:
    def __init__(self):
        self.current_language: str = 'en'
        self.language_history: List[str] = []
        self.LANGUAGE_NAMES = {
            "en": "English", "ru": "Russian", "es": "Spanish", "fr": "French",
            "de": "German", "it": "Italian", "pt": "Portuguese", "pl": "Polish",
            "hi": "Hindi", "ja": "Japanese", "ko": "Korean", "zh": "Chinese",
            "ar": "Arabic", "tr": "Turkish", "nl": "Dutch", "sv": "Swedish",
            "no": "Norwegian", "ka": "Georgian"
        }

    def detect_language(self, text: str) -> str:
        try:
            if not LANGDETECT_AVAILABLE:
                return self.current_language
            if not text or len(text.strip()) < 3:
                return self.current_language
            code = detect(text)
            if code in self.LANGUAGE_NAMES:
                self.current_language = code
                self.language_history.append(code)
                if len(self.language_history) > 10:
                    self.language_history.pop(0)
                logging.info(f"Detected language: {self.LANGUAGE_NAMES[code]}")
                return code
            return self.current_language
        except LangDetectException:
            return self.current_language
        except Exception:
            logging.exception("Language detection failed")
            return self.current_language

    def set_language(self, code: str) -> bool:
        if code in self.LANGUAGE_NAMES:
            self.current_language = code
            return True
        return False

    def get_current_language_name(self) -> str:
        return self.LANGUAGE_NAMES.get(self.current_language, "Unknown")

    def get_language_name(self, code: str) -> str:
        return self.LANGUAGE_NAMES.get(code, "Unknown")


