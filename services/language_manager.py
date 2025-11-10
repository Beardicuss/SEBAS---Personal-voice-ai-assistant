# -*- coding: utf-8 -*-
"""
Language Detection Manager
Phase 1.3: Language recognition and management
"""

import logging
from typing import List
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Set deterministic seed for consistent results
DetectorFactory.seed = 0
LANGDETECT_AVAILABLE = True


class LanguageManager:
    """Manages language detection and selection."""

    def __init__(self):
        self.current_language: str = 'en'
        self.language_history: List[str] = []
        self.LANGUAGE_NAMES = {
            "en": "English",
            "ru": "Russian",
            "de": "German"
        }

    def detect_language(self, text: str) -> str:
        """Detect the language of given text."""
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
        """Manually set active language."""
        if code in self.LANGUAGE_NAMES:
            self.current_language = code
            return True
        return False

    def get_current_language_name(self) -> str:
        """Return current language name."""
        return self.LANGUAGE_NAMES.get(self.current_language, "Unknown")

    def get_language_name(self, code: str) -> str:
        """Return human-readable name for a language code."""
        return self.LANGUAGE_NAMES.get(code, "Unknown")

    def current_languagee(self) -> str:
        """Legacy alias for current language getter."""
        return self.current_language
