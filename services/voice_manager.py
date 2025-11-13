import logging


class VoiceProfile:
    def __init__(self, rate: int = 160, volume: float = 1.0):
        self.rate = rate      # speaking rate for TTS backend
        self.volume = volume  # 0.0 .. 1.0


DEFAULT_PROFILES = {
    "default": VoiceProfile(rate=160, volume=1.0),
    "calm":    VoiceProfile(rate=150, volume=0.9),
    "fast":    VoiceProfile(rate=190, volume=1.0),
}


class VoiceManager:
    """
    Stores and manages simple voice profiles.
    This does NOT talk to audio directly, it only holds settings.
    """

    def __init__(self, profiles=None):
        self.profiles = profiles or DEFAULT_PROFILES
        self.current = "default"

    def set_profile(self, name: str) -> str:
        if name not in self.profiles:
            raise ValueError(f"Unknown voice profile: {name}")
        self.current = name
        logging.info(f"Voice profile set to '{name}'")
        return name

    def get_profile(self) -> VoiceProfile:
        return self.profiles[self.current]

    def list_profiles(self):
        return list(self.profiles.keys())

    def adjust(self, rate=None, volume=None, pitch_delta=None) -> VoiceProfile:
        """
        Adjust current profile parameters.
        Pitch is ignored for now but kept for API compatibility.
        """
        profile = self.get_profile()
        try:
            if rate is not None:
                profile.rate = int(rate)
            if volume is not None:
                v = float(volume)
                v = max(0.0, min(1.0, v))
                profile.volume = v
        except Exception:
            logging.exception("Failed to adjust voice profile")
        return profile
