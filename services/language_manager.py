"""
Language Manager - Stage 1 Mk.I (Whisper Edition)
Controls STT/TTS language switching for Whisper-based system
"""

import re
import logging

# Whisper supports 99 languages out of the box
SUPPORTED_LANGS = {
    "en": {
        "name": "English",
        "whisper_code": "en",
        "tts_voice": "english",
    },
    "ru": {
        "name": "Russian",
        "whisper_code": "ru",
        "tts_voice": "russian",
    },
    "ja": {
        "name": "Japanese",
        "whisper_code": "ja",
        "tts_voice": "japanese",
    },
    "ka": {
        "name": "Georgian",
        "whisper_code": "ka",
        "tts_voice": "georgian",
    },
    "es": {
        "name": "Spanish",
        "whisper_code": "es",
        "tts_voice": "spanish",
    },
    "fr": {
        "name": "French",
        "whisper_code": "fr",
        "tts_voice": "french",
    },
    "de": {
        "name": "German",
        "whisper_code": "de",
        "tts_voice": "german",
    },
    "it": {
        "name": "Italian",
        "whisper_code": "it",
        "tts_voice": "italian",
    },
    "pt": {
        "name": "Portuguese",
        "whisper_code": "pt",
        "tts_voice": "portuguese",
    },
    "zh": {
        "name": "Chinese",
        "whisper_code": "zh",
        "tts_voice": "chinese",
    },
    "ko": {
        "name": "Korean",
        "whisper_code": "ko",
        "tts_voice": "korean",
    },
    "ar": {
        "name": "Arabic",
        "whisper_code": "ar",
        "tts_voice": "arabic",
    },
}


class LanguageManager:
    """
    Controls SEBAS language flow:
        - STT → Whisper language
        - TTS → Voice selection
        - NLU → Text normalization
    """

    def __init__(self, default_lang: str = "en"):
        """
        Initialize Language Manager.
        
        Args:
            default_lang: Default language code (ISO 639-1)
        """
        self.current_lang = default_lang
        self.stt = None  # Will be linked by main.py
        self.tts = None  # Will be linked by main.py
        
        logging.info(f"[LanguageManager] Initialized with default language: {default_lang}")

    # ============================================================
    # Binding STT/TTS Managers
    # ============================================================
    
    def bind_stt(self, stt_manager):
        """
        Bind STT manager.
        
        Args:
            stt_manager: STTManager instance
        """
        self.stt = stt_manager
        logging.info("[LanguageManager] STT manager bound")
        
        # Set initial language
        if self.stt:
            self._update_stt_language()

    def bind_tts(self, tts_manager):
        """
        Bind TTS manager.
        
        Args:
            tts_manager: TTSManager instance
        """
        self.tts = tts_manager
        logging.info("[LanguageManager] TTS manager bound")
        
        # Set initial voice
        if self.tts:
            self._update_tts_voice()

    # ============================================================
    # Language Detection
    # ============================================================
    
    def detect_language(self, text: str) -> str:
        """
        Auto-detect language from text.
        Uses simple character-based detection.
        
        Args:
            text: Input text
            
        Returns:
            Detected language code
        """
        if not text or not text.strip():
            return self.current_lang
        
        t = text.lower()
        
        # Cyrillic → Russian
        if re.search(r"[а-яё]", t):
            self.set_language("ru")
            return "ru"
        
        # Japanese Hiragana/Katakana
        if re.search(r"[ぁ-ゔァ-ヴ]", t):
            self.set_language("ja")
            return "ja"
        
        # Georgian
        if re.search(r"[ა-ჰ]", t):
            self.set_language("ka")
            return "ka"
        
        # Chinese characters
        if re.search(r"[\u4e00-\u9fff]", t):
            self.set_language("zh")
            return "zh"
        
        # Korean Hangul
        if re.search(r"[가-힣]", t):
            self.set_language("ko")
            return "ko"
        
        # Arabic
        if re.search(r"[\u0600-\u06ff]", t):
            self.set_language("ar")
            return "ar"
        
        # Default: English
        return self.current_lang

    # ============================================================
    # Language Switching
    # ============================================================
    
    def set_language(self, lang_code: str) -> bool:
        """
        Set system language (affects STT and TTS).
        
        Args:
            lang_code: Language code (en, ru, ja, ka, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if lang_code not in SUPPORTED_LANGS:
            logging.warning(f"[LanguageManager] Unsupported language: {lang_code}")
            return False
        
        old_lang = self.current_lang
        self.current_lang = lang_code
        
        logging.info(f"[LanguageManager] Switching language: {old_lang} → {lang_code}")
        
        # Update STT
        self._update_stt_language()
        
        # Update TTS
        self._update_tts_voice()
        
        return True
    
    def _update_stt_language(self):
        """Update STT manager with current language."""
        if not self.stt:
            return
        
        profile = SUPPORTED_LANGS[self.current_lang]
        whisper_code = profile["whisper_code"]
        
        try:
            self.stt.set_language(whisper_code)
            logging.info(f"[LanguageManager] STT language set to: {whisper_code}")
        except Exception as e:
            logging.exception(f"[LanguageManager] Failed to set STT language: {e}")
    
    def _update_tts_voice(self):
        """Update TTS manager with current language voice."""
        if not self.tts:
            return
        
        profile = SUPPORTED_LANGS[self.current_lang]
        voice_hint = profile["tts_voice"]
        
        try:
            success = self.tts.set_voice(voice_hint)
            if success:
                logging.info(f"[LanguageManager] TTS voice set to: {voice_hint}")
            else:
                logging.warning(f"[LanguageManager] Failed to set TTS voice: {voice_hint}")
        except Exception as e:
            logging.exception(f"[LanguageManager] Error setting TTS voice: {e}")

    # ============================================================
    # Getters
    # ============================================================
    
    def get_current_language(self) -> str:
        """Get current language code."""
        return self.current_lang

    def get_current_language_name(self) -> str:
        """Get current language full name."""
        return SUPPORTED_LANGS[self.current_lang]["name"]
    
    def get_supported_languages(self) -> list:
        """
        Get list of supported languages.
        
        Returns:
            List of dicts with language info
        """
        return [
            {
                'code': code,
                'name': profile['name'],
                'stt_available': True,  # Whisper supports all
                'tts_available': True,  # Assume TTS works
            }
            for code, profile in SUPPORTED_LANGS.items()
        ]
    
    def is_language_supported(self, lang_code: str) -> bool:
        """
        Check if language is supported.
        
        Args:
            lang_code: Language code
            
        Returns:
            True if supported
        """
        return lang_code in SUPPORTED_LANGS