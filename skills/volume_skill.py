"""
Skill: System Volume Control
"""

import logging
from sebas.skills.base_skill import BaseSkill
import ctypes

class VolumeSkill(BaseSkill):

    @property
    def name(self):
        return "Volume Control"

    @property
    def intents(self):
        return {
            "set_volume": "Set system volume"
        }

    def handle(self, intent_name: str, slots: dict, sebas):
        if intent_name != "set_volume":
            return False

        vol = slots.get("level")
        try:
            vol = int(vol)
        except:
            sebas.speak("Sir, the volume must be a number.")
            return True

        if not 0 <= vol <= 100:
            sebas.speak("Volume must be between zero and one hundred.")
            return True

        logging.info(f"VolumeSkill: Setting volume to {vol}%")

        # Windows endpoint API
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(vol / 100.0, None)

            sebas.speak(f"Volume set to {vol} percent.")
            return True

        except Exception as e:
            logging.error(f"VolumeSkill failed: {e}")
            sebas.speak("Volume subsystem unavailable.")
            return True