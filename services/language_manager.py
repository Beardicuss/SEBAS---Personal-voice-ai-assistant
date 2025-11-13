"""
Language Manager for Sebas
Responsible for detecting, switching and tracking active language.
"""

import logging
from typing import Optional
from langdetect import detect, LangDetectException


class LanguageManager:
    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang.lower().strip()
        self.supported_languages = {
            "en": "English",
            "ru": "Russian",
            "uk": "Ukrainian",
            "ge": "Georgian",
            "de": "German",
            "fr": "French",
            "es": "Spanish"
        }

    # --------------------------------------
    # Detect language from text
    # --------------------------------------
    def detect_language(self, text: str) -> str:
        try:
            lang = detect(text)
            if lang in self.supported_languages:
                self.current_lang = lang
                logging.info(f"Language detected: {lang}")
            else:
                logging.info(f"Language '{lang}' detected but unsupported")
            return lang
        except LangDetectException:
            logging.warning("Could not detect language; using current")
            return self.current_lang

    # --------------------------------------
    # Set manually
    # --------------------------------------
    def set_language(self, lang_code: str) -> bool:
        code = (lang_code or "").lower().strip()

        if code in self.supported_languages:
            self.current_lang = code
            logging.info(f"Language manually set to: {code}")
            return True

        logging.warning(f"Unsupported language code: {lang_code}")
        return False

    # --------------------------------------
    # Getters
    # --------------------------------------
    def get_current_language(self) -> str:
        return self.current_lang

    def get_current_language_name(self) -> str:
        return self.supported_languages.get(self.current_lang, "Unknown")