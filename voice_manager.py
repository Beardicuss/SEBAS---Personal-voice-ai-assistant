# -*- coding: utf-8 -*-
import logging


class VoiceProfile:
    def __init__(self, name, rate=160, volume=0.9, pitch_delta=None):
        self.name = name
        self.rate = rate
        self.volume = volume
        self.pitch_delta = pitch_delta  # driver dependent


DEFAULT_PROFILES = {
    "butler": VoiceProfile("butler", rate=160, volume=0.9, pitch_delta=-3),
    "professional": VoiceProfile("professional", rate=170, volume=0.92, pitch_delta=0),
    "friendly": VoiceProfile("friendly", rate=185, volume=1.0, pitch_delta=2),
    "technical": VoiceProfile("technical", rate=175, volume=0.95, pitch_delta=-1),
}


class VoiceManager:
    def __init__(self, tts_engine, profiles=None):
        self.engine = tts_engine
        self.profiles = profiles or DEFAULT_PROFILES
        self.current = "butler"
        self._pitch_supported_keys = ["pitch", "voice_pitch", "pitchPercent"]

    def set_profile(self, profile_name):
        key = (profile_name or "").strip().lower()
        if key not in self.profiles:
            raise ValueError("Unknown voice profile")
        self.current = key
        self.apply_current()
        return key

    def apply_current(self):
        p = self.profiles[self.current]
        try:
            self.engine.setProperty("rate", int(p.rate))
        except Exception:
            pass
        try:
            self.engine.setProperty("volume", float(p.volume))
        except Exception:
            pass
        if p.pitch_delta is not None:
            for k in self._pitch_supported_keys:
                try:
                    self.engine.setProperty(k, p.pitch_delta)
                    break
                except Exception:
                    continue

    def adjust(self, rate=None, volume=None, pitch_delta=None):
        # Adjust current profile and apply immediately
        p = self.profiles[self.current]
        if rate is not None:
            try:
                p.rate = int(rate)
            except Exception:
                logging.debug("Invalid rate value for adjust", exc_info=True)
        if volume is not None:
            try:
                p.volume = max(0.0, min(1.0, float(volume)))
            except Exception:
                logging.debug("Invalid volume value for adjust", exc_info=True)
        if pitch_delta is not None:
            try:
                p.pitch_delta = int(pitch_delta)
            except Exception:
                logging.debug("Invalid pitch value for adjust", exc_info=True)
        self.apply_current()

    def list_profiles(self):
        return list(self.profiles.keys())


