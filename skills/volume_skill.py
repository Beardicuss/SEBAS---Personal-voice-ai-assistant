"""
Skill: System Volume Control - FIXED
Type-safe implementation with proper error handling
"""

import logging
from sebas.skills.base_skill import BaseSkill
import ctypes
from typing import Any, Dict

class VolumeSkill(BaseSkill):
    """Handles system volume control on Windows."""

    def get_intents(self):
        return ["set_volume"]

    def handle(self, intent_name: str, slots: Dict[str, Any]) -> bool:
        """Handle volume control intent."""
        if intent_name != "set_volume":
            return False

        vol_str = slots.get("level")
        
        # Type guard: ensure vol_str is not None and can be converted
        if vol_str is None:
            self.assistant.speak("Sir, please specify a volume level.")
            return True
        
        try:
            vol = int(vol_str)
        except (ValueError, TypeError):
            self.assistant.speak("Sir, the volume must be a number.")
            return True

        if not 0 <= vol <= 100:
            self.assistant.speak("Volume must be between zero and one hundred.")
            return True

        logging.info(f"VolumeSkill: Setting volume to {vol}%")

        # Windows endpoint API with type guards
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            
            # Type guard for Pylance
            if devices is None:
                raise RuntimeError("No audio device found")
            
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(vol / 100.0, None)

            self.assistant.speak(f"Volume set to {vol} percent.")
            return True

        except ImportError:
            logging.error("VolumeSkill: pycaw or comtypes not installed")
            self.assistant.speak("Volume control requires pycaw library. Install with: pip install pycaw comtypes")
            return True
        except Exception as e:
            logging.error(f"VolumeSkill failed: {e}")
            self.assistant.speak("Volume subsystem unavailable.")
            return True