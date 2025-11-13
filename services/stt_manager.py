"""
Unified STT (speech-to-text) engine for SEBAS.
Handles microphone access, Vosk, Google and others.
"""

import logging
import speech_recognition as sr
import requests


class STTManager:
    def __init__(self, device_index=None):
        self.recognizer = sr.Recognizer()
        self.device_index = device_index
        self._mic_calibrated = False

    def listen(self, timeout=5, phrase_time_limit=10):
        """Record audio from microphone and return recognized text."""
        try:
            mic = sr.Microphone(device_index=self.device_index)
        except Exception:
            logging.exception("STT: Failed to open microphone")
            return ""

        # Capture audio
        try:
            with mic as source:
                if not self._mic_calibrated:
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=1)
                        self._mic_calibrated = True
                    except Exception:
                        pass

                # UI HUD status
                try:
                    requests.post("http://127.0.0.1:5000/api/status",
                                  json={"mic": "listening"}, timeout=0.25)
                except:
                    pass

                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            logging.exception(f"STT listen() failed: {e}")
            return ""

        # Recognition
        try:
            # Try Vosk first
            try:
                return self.recognizer.recognize_vosk(audio).lower()
            except Exception:
                pass

            # Google fallback
            try:
                text = self.recognizer.recognize_google(audio).lower()
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                logging.error(f"Speech recognition API error: {e}")
                return ""

        except Exception:
            logging.exception("STT recognition failed")
            return ""

        finally:
            try:
                requests.post("http://127.0.0.1:5000/api/status",
                              json={"mic": "idle"}, timeout=0.25)
            except:
                pass

