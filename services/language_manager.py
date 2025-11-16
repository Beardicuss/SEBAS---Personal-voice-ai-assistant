"""
Language Manager - FIXED
Controls:
    - Current system language
    - Auto-detection from text
    - Synchronization with STT and TTS modules
"""

from pathlib import Path
import re
import logging

# FIXED: Use actual available models and voices
SUPPORTED_LANGS = {
    "en": {
        "name": "English",
        "stt_model": "vosk-model-small-en-us-0.15",  # Actual model folder name
        "tts_voice": "english",  # Generic voice hint that should match available voices
    },
    "ru": {
        "name": "Russian", 
        "stt_model": None,  # No Russian model available
        "tts_voice": "russian",  # Voice hint
    },
    "ja": {
        "name": "Japanese",
        "stt_model": None,  # No Japanese model available  
        "tts_voice": "japanese",  # Voice hint
    },
    "ka": {
        "name": "Georgian",
        "stt_model": None,  # No Georgian model available
        "tts_voice": "georgian",  # Voice hint
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
        self.available_stt_models = {}  # Track which STT models are actually available

    # ------------------------------------------------------------
    # Linking engine managers (called from main.py)
    # ------------------------------------------------------------
    def bind_stt(self, stt_manager):
        self.stt = stt_manager
        self._discover_available_stt_models()

    def bind_tts(self, tts_manager):
        self.tts = tts_manager

    def _discover_available_stt_models(self):
        """Discover which STT models are actually available"""
        if not self.stt or self.stt.mode != "vosk":
            return
            
        base_dir = Path(__file__).resolve().parent.parent
        
        # Check for common Vosk model patterns
        model_patterns = {
            "en": ["vosk-model-small-en-us-0.15", "vosk-model-small-en-us", "vosk-model-en-us-0.22"],
            "ru": ["vosk-model-small-ru-0.22", "vosk-model-ru-0.22"],
            "ja": ["vosk-model-small-ja-0.22", "vosk-model-ja-0.22"],
            "ka": ["vosk-model-small-ka-0.22", "vosk-model-ka-0.22"],
        }
        
        for lang_code, patterns in model_patterns.items():
            for pattern in patterns:
                model_path = base_dir / "model" / pattern
                if model_path.exists():
                    self.available_stt_models[lang_code] = str(model_path)
                    logging.info(f"LanguageManager: Found STT model for {lang_code}: {pattern}")
                    break

    # ------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------
    def detect_language(self, text: str):
        """Primitive detection. Replace with fastText later."""
        if not text or not text.strip():
            return self.set_language("en")
            
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
            logging.warning(f"LanguageManager: Unsupported language code: {lang_code}")
            return False

        old_lang = self.current_lang
        self.current_lang = lang_code
        profile = SUPPORTED_LANGS[lang_code]

        logging.info(f"LanguageManager: Switching from {old_lang} to {lang_code}")

        # Switch STT model only if available
        if self.stt and profile["stt_model"]:
            # Check if this model is actually available
            stt_model_path = self.available_stt_models.get(lang_code)
            if stt_model_path:
                try:
                    self.stt.set_language(stt_model_path)
                    logging.info(f"LanguageManager: STT switched to {lang_code}")
                except Exception as e:
                    logging.warning(f"LanguageManager: Failed to switch STT to {lang_code}: {e}")
            else:
                logging.warning(f"LanguageManager: No STT model available for {lang_code}")

        # Switch TTS voice
        if self.tts:
            try:
                success = self.tts.set_voice(profile["tts_voice"])
                if success:
                    logging.info(f"LanguageManager: TTS voice switched to {profile['tts_voice']}")
                else:
                    logging.warning(f"LanguageManager: Failed to switch TTS voice to {profile['tts_voice']}")
            except Exception as e:
                logging.warning(f"LanguageManager: Error switching TTS voice: {e}")

        return True

    # ------------------------------------------------------------
    def get_current_language(self):
        return self.current_lang

    def get_current_language_name(self):
        return SUPPORTED_LANGS[self.current_lang]["name"]
    
    def get_available_languages(self):
        """Get list of languages that have both STT and TTS support"""
        available = []
        for lang_code, profile in SUPPORTED_LANGS.items():
            has_stt = lang_code in self.available_stt_models
            # For TTS, we assume voice switching might work with hints
            available.append({
                'code': lang_code,
                'name': profile['name'],
                'stt_available': has_stt,
                'tts_available': True  # We'll try anyway
            })
        return available
