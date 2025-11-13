import sys
import os
import logging
import traceback
import threading
import time
import speech_recognition as sr
import pyttsx3
import subprocess
import platform
import psutil
import requests
import webbrowser
import pyaudio
import screen_brightness_control as sbc
import ctypes
import json
import re
import winreg
import webbrowser as _web
import socket
from datetime import datetime, timedelta
from ctypes import cast, POINTER
from typing import Optional, Dict, Any
from sebas.services.voice_system import VoiceSystem
from sebas.services.language_manager import LanguageManager
from sebas.constants.permissions import Role, get_permission_for_intent
from comtypes import POINTER, cast
from comtypes import CLSCTX_ALL, cast
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from typing import Any
from comtypes.client import GetBestInterface
from PIL import ImageGrab
from sebas.logging_config import setup_structured_logging, log_with_context, get_audit_logger


# ----------------------- Profiles & Logging -----------------------
# Profile-aware base directory for logs and preferences
PROFILE_NAME = os.environ.get('SEBAS_PROFILE', 'default').strip() or 'default'
PROFILE_DIR = os.path.join(os.path.expanduser('~'), '.sebas', 'profiles', PROFILE_NAME)
print("=== USING PROFILE DIRECTORY ===")
print(PROFILE_DIR)
print("=== PROFILE NAME =", PROFILE_NAME, "===")

try:
    os.makedirs(PROFILE_DIR, exist_ok=True)
except Exception:
    pass
# Try to use structured logging if available (Phase 1.5)
try:
    from .logging_config import setup_structured_logging
    LOG_PATH = os.path.join(PROFILE_DIR, "sebas.log")
    setup_structured_logging(
        log_file=LOG_PATH,
        log_format='json', # Use JSON format for structured logging
        log_level='INFO',
        console_output=True,
        file_output=True
    )
    AUDIT_LOGGER = get_audit_logger()
    STRUCTURED_LOGGING = True
except ImportError:
    # Fallback to basic logging
    LOG_PATH = os.path.join(PROFILE_DIR, "sebas.log")
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    AUDIT_LOGGER = None
    STRUCTURED_LOGGING = False
    LogContext = None # type: ignore
                            

try:
    if str(os.environ.get('SEBAS_LOG_DASHBOARD', '0')).lower() in ('1', 'true', 'yes'):
        from logging_conf.logging_dashboard import start_logging_dashboard
        host = os.environ.get('SEBAS_LOG_DASHBOARD_HOST', '127.0.0.1')
        port = int(os.environ.get('SEBAS_LOG_DASHBOARD_PORT', '5600'))
        audit_path = os.path.join(os.path.dirname(LOG_PATH), 'sebas_audit.log')
        start_logging_dashboard(host=host, port=port, log_file=LOG_PATH, audit_log_file=audit_path)
        logging.info(f"Logging dashboard available at http://{host}:{port}")
except Exception:
    logging.exception("Failed to start logging dashboard")
# ----------------------- Runtime Base Directory -----------------------
# Ensure working directory is the app folder (supports PyInstaller _MEIPASS)
try:
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    os.chdir(BASE_DIR)
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def log_unhandled_exception(exc_type, exc_value, exc_tb):
    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    traceback.print_exception(exc_type, exc_value, exc_tb)
sys.excepthook = log_unhandled_exception
# ----------------------- Service Client -----------------------
class ServiceClient:
    """Client to communicate with the privileged background service."""
    def __init__(self, host='127.0.0.1', port=5001):
        self.host = host
        self.port = port
    def send_command(self, command, params=None):
        """Sends a command to the service and returns the response."""
        if params is None:
            params = {}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0) # 5 second timeout for connection and response
                s.connect((self.host, self.port))
                request = json.dumps({"command": command, "params": params})
                s.sendall(request.encode('utf-8'))
                response_data = s.recv(8192)
                response = json.loads(response_data.decode('utf-8'))
               
                logging.info(f"Service response for '{command}': {response}")
                if response.get('status') == 'ok':
                    return True, response
                else:
                    return False, response.get('message', 'Unknown service error')
        except ConnectionRefusedError:
            logging.error("Connection to SEBAS service refused. Is the service installed and running?")
            return False, "The privileged service is not running. Please install and start it from an admin command prompt."
        except Exception as e:
            logging.exception(f"Failed to communicate with service for command '{command}'")
            return False, str(e)
# ----------------------- Utilities: Error Handling -----------------------
def safe_call(log_message=None, speak_message=None):
    def _decorator(fn):
        def _wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                try:
                    logging.exception(log_message or f"Unhandled error in {getattr(fn, '__name__', 'call')}")
                finally:
                    # Optional voice feedback if first arg is self-like with speak()
                    if speak_message and args and hasattr(args[0], 'speak'):
                        try:
                            args[0].speak(speak_message)
                        except Exception:
                            pass
        return _wrapped
    return _decorator
# ----------------------- WakeWordDetector -----------------------
class WakeWordDetector:
    """
    Continuously listens for a wake word and triggers a callback.
    Silently handles timeouts and unknown speech.
    """
    def __init__(self, recognizer, microphone_device_index=None, wake_word="sebas", callback=None, audio_lock=None):
        self.recognizer = recognizer
        self.microphone_device_index = microphone_device_index
        self.wake_word = wake_word.lower()
        self.callback = callback
        self._mic_calibrated = False
        self._running_event = threading.Event()
        self._thread = None
        self._audio_lock = audio_lock
        # Presence flag to avoid attribute errors; actual mic opened lazily
        self.microphone = True
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running_event.set()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeWord")
        self._thread.start()
    def stop(self, join=True, timeout=3.0):
        self._running_event.clear()
        if join and self._thread:
            self._thread.join(timeout=timeout)
    def _loop(self):
        logging.info("WakeWordDetector thread started")
        consecutive_errors = 0
        max_errors = 5
       
        while self._running_event.is_set():
            try:
                if self.microphone is None:
                    time.sleep(1)
                    continue
                # Ensure exclusive access to the microphone
                lock = self._audio_lock
                _context = lock if lock is not None else threading.Lock()
                with _context:
                    recognized_text = None
                    # Open mic lazily for each capture
                    try:
                        if self.microphone_device_index is not None:
                            mic_cm = sr.Microphone(device_index=self.microphone_device_index)
                        else:
                            mic_cm = sr.Microphone()
                       
                        # Reset error counter on successful mic access
                        consecutive_errors = 0
                    except Exception as e:
                        consecutive_errors += 1
                        logging.warning(f"Microphone access error ({consecutive_errors}/{max_errors}): {e}")
                        if consecutive_errors >= max_errors:
                            logging.error("Too many microphone errors, sleeping for 5 seconds")
                            time.sleep(5)
                            consecutive_errors = 0
                        continue
                    with mic_cm as source:
                        # Calibrate once
                        # Ambient calibration moved out of wake loop to avoid init crashes
                        try:
                            audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)
                        except sr.WaitTimeoutError:
                            continue # silently ignore timeout
                        # Lightweight VAD: skip recognition if captured chunk is extremely quiet
                        try:
                            raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                            if raw:
                                # compute simple average absolute amplitude for 16-bit samples
                                # avoid external deps
                                import array
                                samples = array.array('h', raw)
                                avg_amp = sum(abs(s) for s in samples) / max(1, len(samples))
                                logging.debug(f"Wake VAD avg_amp={avg_amp:.1f}")
                                if avg_amp < 150: # tuned threshold; skip likely non-speech
                                    continue
                        except Exception:
                            pass
                        try:
                            text = self.recognizer.recognize_google(audio).lower()
                            logging.debug(f"Wake recognized text: {text}")
                            if text:
                                recognized_text = text
                        except sr.UnknownValueError:
                            continue # silently ignore unclear speech
                        except sr.RequestError as e:
                            logging.error(f"Speech API error: {e}")
                            continue
                        except Exception:
                            # Catch any other recognizer issues and keep looping
                            logging.debug("Non-fatal recognition error", exc_info=True)
                            continue
                # Call the callback ONLY after mic context has been exited
                if recognized_text and self.callback:
                    try:
                        self.callback(recognized_text)
                    except Exception:
                        logging.debug("Callback error after wake recognition", exc_info=True)
            except Exception:
                logging.exception("Error in WakeWordDetector loop")
            time.sleep(0.1)
# ----------------------- Sebas Class -----------------------
class Sebas:
    def __init__(self):
        logging.info("Initializing Sebas assistant")
        self.recognizer = sr.Recognizer()
        # Microphone selection is index-only; device is opened lazily inside context managers
        self.microphone_device_index = self.select_microphone_index()
        from sebas.services.voice_system import VoiceSystem
        self.tts_engine = VoiceSystem()
        self.system = platform.system()
        # Ensure exclusive access to audio I/O across threads
        self.audio_lock = threading.RLock()
        # Presence flag; actual device contexts are created on demand
        self.microphone = True
        # Client for the privileged service
        self.service_client = ServiceClient()
        # Premium modules
                # Premium modules (без жесткой зависимости от AD)
        # Premium modules (без жесткой зависимости от AD)
        try:
            from sebas.services.nlu import SimpleNLU, ContextManager
            from sebas.services.task_manager import TaskManager
            # from integrations.smart_home import HomeAssistantClient
            from sebas.integrations.calendar_client import CalendarClient
            from sebas.integrations.email_client import EmailClient
            from sebas.constants.preferences import PreferenceStore
            from sebas.constants.suggestions import SuggestionEngine
            from core.skill_registry import SkillRegistry

            self.voice = self.tts_engine
            self.nlu = SimpleNLU()
            self.context = ContextManager()
            self.tasks = TaskManager()
            # self.smarthome = HomeAssistantClient()
            self.calendar = CalendarClient()
            self.email = EmailClient()
            try:
                profile_dir = PROFILE_DIR
            except Exception:
                profile_dir = os.path.join(os.path.expanduser('~'), '.sebas')

            self.prefs = PreferenceStore(os.path.join(profile_dir, 'prefs.json'))
            self.suggestions = SuggestionEngine(self.prefs)
        except Exception:
            logging.exception("Failed to initialize premium modules")

            # Phase 2–6 как у тебя дальше (WindowsServiceManager, NetworkManager и прочее)
                    # Premium modules (без жесткой зависимости от AD)
        try:
            from sebas.services.nlu import SimpleNLU, ContextManager
            from sebas.services.task_manager import TaskManager
            from sebas.integrations.calendar_client import CalendarClient
            from sebas.integrations.email_client import EmailClient
            from sebas.constants.preferences import PreferenceStore
            from sebas.constants.suggestions import SuggestionEngine
            from core.skill_registry import SkillRegistry

            # VoiceSystem уже инициализирован как self.tts_engine
            self.voice = self.tts_engine
            self.nlu = SimpleNLU()
            self.context = ContextManager()
            self.tasks = TaskManager()
            self.calendar = CalendarClient()
            self.email = EmailClient()

            try:
                profile_dir = PROFILE_DIR
            except Exception:
                profile_dir = os.path.join(os.path.expanduser('~'), '.sebas')
            self.prefs = PreferenceStore(os.path.join(profile_dir, 'prefs.json'))
            self.suggestions = SuggestionEngine(self.prefs)

            # Initialize skill registry (resolve absolute skills path)
            try:
                skills_dir = os.path.join(BASE_DIR, 'skills')
            except Exception:
                skills_dir = 'skills'
            self.skill_registry = SkillRegistry(self, skills_dir=skills_dir)
            self.skill_registry.load_skill_preferences()

            # Phase 2–6 как у тебя дальше (WindowsServiceManager, NetworkManager и прочее)
            try:
                from sebas.integrations.windows_service_manager import WindowsServiceManager
                from sebas.integrations.process_manager import ProcessManager
                from sebas.integrations.network_manager import NetworkManager
                from sebas.integrations.firewall_manager import FirewallManager
                from sebas.integrations.port_monitor import PortMonitor
                # from integrations.vpn_manager import VPNManager

                if platform.system() == 'Windows':
                    self.service_manager = WindowsServiceManager()
                    self.process_manager = ProcessManager()
                    self.network_manager = NetworkManager()
                    self.firewall_manager = FirewallManager()
                    self.port_monitor = PortMonitor()
                    # self.vpn_manager = VPNManager()
                else:
                    self.service_manager = None
                    self.process_manager = None
                    self.network_manager = None
                    self.firewall_manager = None
                    self.port_monitor = None
                    # self.vpn_manager = None

                if platform.system() == 'Windows':
                    from sebas.integrations.file_operations import FileOperations
                    from sebas.integrations.storage_manager import StorageManager
                    self.file_operations = FileOperations()
                    self.storage_manager = StorageManager()
                else:
                    self.file_operations = None
                    self.storage_manager = None

                if platform.system() == 'Windows':
                    from sebas.integrations.security_manager import SecurityManager
                    from sebas.integrations.compliance_manager import ComplianceManager
                    self.security_manager = SecurityManager()
                    self.compliance_manager = ComplianceManager()
                else:
                    self.security_manager = None
                    self.compliance_manager = None

                from sebas.integrations.automation_engine import AutomationEngine
                from sebas.integrations.script_executor import ScriptExecutor
                from sebas.integrations.event_system import EventSystem
                from sebas.integrations.enterprise_integrations import DocumentationGenerator
                self.automation_engine = AutomationEngine()
                self.script_executor = ScriptExecutor()
                self.event_system = EventSystem()
                self.doc_generator = DocumentationGenerator()

                if platform.system() == 'Windows':
                    from sebas.integrations.task_scheduler import TaskScheduler
                    self.task_scheduler = TaskScheduler()
                else:
                    self.task_scheduler = None

                from sebas.integrations.ai_analytics import (
                    AnomalyDetector, PredictiveAnalyzer,
                    PerformanceOptimizer, TroubleshootingGuide
                )
                from sebas.integrations.nlu_enhancer import (
                    ContextManager as EnhancedContextManager,
                    MultiPartCommandParser,
                    LearningSystem, IntentResolver
                )
                self.anomaly_detector = AnomalyDetector()
                self.predictive_analyzer = PredictiveAnalyzer()
                self.performance_optimizer = PerformanceOptimizer()
                self.troubleshooting_guide = TroubleshootingGuide()
                self.nlu_context_manager = EnhancedContextManager()
                self.multipart_parser = MultiPartCommandParser()
                self.learning_system = LearningSystem()
                self.intent_resolver = IntentResolver()
            except Exception:
                logging.exception("Failed to initialize Phase 2, 3, 4, 5, and 6 managers")
                self.service_manager = None
                self.process_manager = None
                self.network_manager = None
                self.firewall_manager = None
                self.port_monitor = None
                self.vpn_manager = None
                self.file_operations = None
                self.storage_manager = None
                self.security_manager = None
                self.compliance_manager = None
                self.automation_engine = None
                self.script_executor = None
                self.event_system = None
                self.doc_generator = None
                self.task_scheduler = None
                self.anomaly_detector = None
                self.predictive_analyzer = None
                self.performance_optimizer = None
                self.troubleshooting_guide = None
                self.nlu_context_manager = None
                self.multipart_parser = None
                self.learning_system = None
                self.intent_resolver = None
        except Exception:
            logging.exception("Failed to initialize premium modules")

       
        # Initialize Active Directory client (Phase 2) - after prefs is initialized
        try:
            self._initialize_ad_client()
        except Exception:
            logging.exception("Failed to initialize AD client")
            self.ad_client = None
        # TTS configuration: refined British butler voice
        self.tts_engine.speak("Sebas online.")

        # Notes and screenshots
        self.notes_file = os.path.join(os.path.expanduser('~'), 'sebas_notes.txt')
        self.screenshots_folder = os.path.join(os.path.expanduser('~'), 'Pictures', 'Screenshots')
        os.makedirs(self.screenshots_folder, exist_ok=True)
        # Learned commands storage
        self.learned_file = os.path.join(os.path.expanduser('~'), '.sebas_learned_commands.json')
        self.learned_commands = self._load_learned_commands()
        # Program index (installed apps and shortcuts)
        self.program_index_file = os.path.join(os.path.expanduser('~'), '.sebas_program_index.json')
        self.program_index = self._load_program_index()
        # Auto-scan at startup and periodic refresh
        self.program_rescan_interval_hours = 6
        try:
            self._maybe_scan_programs_startup(max_age_days=7)
            self._start_program_rescan_thread()
        except Exception:
            logging.exception("Failed to initialize program scanning threads")
        # Recognizer thresholds
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.5
        self.recognizer.phrase_threshold = 0.3
        # Butler persona configuration
        self.form_of_address = "sir" # could be changed to "madam" by user preference
       
        # Phase 1: Optional default TTS language from environment/config
        try:
            default_lang = os.environ.get('SEBAS_TTS_LANGUAGE') or os.environ.get('SEBAS_LANGUAGE')
            if default_lang:
                self.set_tts_language(default_lang)
        except Exception:
            logging.exception("Failed to apply default TTS language from environment")
       
        # Initialize AD authentication and role detection
        self._initialize_ad_authentication()
    # ----------------------- Microphone Selection (Index only) -----------------------
    def select_microphone_index(self):
        try:
            mic_names = sr.Microphone.list_microphone_names()
            if not mic_names:
                logging.error("No microphones found")
                return None
            logging.info("Available microphones:")
            for i, name in enumerate(mic_names):
                logging.info(f"{i}: {name}")
            # Prefer entries containing 'microphone'
            for i, name in enumerate(mic_names):
                if 'microphone' in (name or '').lower():
                    logging.info(f"Preferred microphone index selected (by name): {i} - {name}")
                    return i
            # Fallback to index 0
            logging.info(f"Defaulting to microphone index 0 - {mic_names[0]}")
            return 0
        except Exception:
            logging.exception("Microphone index selection failed")
            return None
    # ----------------------- TTS -----------------------
    def speak(self, text, proactive: bool = False):
        logging.info(f"Sebas speaking: {text}")
        try:
            try:
                requests.post(
                    "http://127.0.0.1:5000/api/status",
                    json={"processing": True},
                    timeout=0.25
                )
            except Exception:
                pass

            with self.audio_lock:
                lang = "en"
                try:
                    lm = getattr(self, "language_manager", None)
                    if lm is not None:
                        lang = lm.get_iso3()
                except Exception:
                    pass

                ve = getattr(self, "tts_engine", None)
                if ve is None:
                    logging.error("TTS engine not initialized")
                else:
                    try:
                        ve.speak(text, language=lang)
                    except Exception:
                        logging.exception("VoiceSystem.speak failed")
                
            # For proactive suggestions, wait a bit for user response
            if proactive:
                time.sleep(2)
        except Exception:
            logging.exception("TTS error in speak()")
        finally:
            try:
                requests.post(
                    "http://127.0.0.1:5000/api/status",
                    json={"processing": False},
                    timeout=0.25
                )
            except Exception:
                pass
    # ----------------------- Premium: Voice Control -----------------------
    def set_voice_profile(self, profile: str) -> bool:
        try:
            if not getattr(self, 'voice', None):
                return False
            key = self.voice.set_profile(profile)
            self.prefs.set_pref('voice_profile', key)
            self.speak(f"Voice profile set to {key}")
            return True
        except Exception:
            logging.exception("set_voice_profile failed")
            return False
    def adjust_voice(self, rate: Optional[int] = None, volume: Optional[float] = None, pitch: Optional[int] = None) -> bool:
        try:
            if not getattr(self, 'voice', None):
                return False
            self.speak("Voice settings updated")
            return True
        except Exception:
            logging.exception("adjust_voice failed")
            return False
    # ----------------------- Butler Persona Helpers -----------------------
    def get_time_of_day(self):
        try:
            hour = datetime.now().hour
            if 5 <= hour < 12:
                return "morning"
            if 12 <= hour < 17:
                return "afternoon"
            if 17 <= hour < 22:
                return "evening"
            return "night"
        except Exception:
            return "day"
    def get_salutation(self):
        return self.form_of_address
    def butler_greeting(self):
        tod = self.get_time_of_day()
        sal = self.get_salutation()
        options = [
            f"Good {tod}, {sal}. Sebas at your service.",
            f"Your humble servant Sebas is ready to attend to your needs, {sal}.",
            f"The household assistant Sebas is now operational and prepared to serve, {sal}."
        ]
        try:
            import random
            return random.choice(options)
        except Exception:
            return options[0]
    def speak_formal_ack(self, text):
        # Centralize refined responses
        self.speak(text)
    def _parse_language_code(self, language_input: str) -> Optional[str]:
        try:
            lang_mgr = getattr(self, 'language_manager', None)
            if lang_mgr is None:
                return None
           
            s = (language_input or '').lower().strip()
           
            # direct code
            if s in getattr(lang_mgr, 'LANGUAGE_NAMES', {}):
                return s
           
            # by name
            for code, name in getattr(lang_mgr, 'LANGUAGE_NAMES', {}).items():
                if s in name.lower():
                    return code
           
            return None
        except Exception:
            return None
    def list_available_voices(self):
        try:
            ve = getattr(self, "tts_engine", None)
            if ve is None:
                return []

            voices_list = ve.get_voices() or []
            listed = []
            for v in voices_list:
                info = {
                    "id": getattr(v, "id", ""),
                    "name": getattr(v, "name", ""),
                    "languages": [str(x) for x in getattr(v, "languages", [])],
                    "age": getattr(v, "age", ""),
                    "gender": getattr(v, "gender", ""),
                }
                listed.append(info)
                logging.debug(f"Voice: {info}")
            return listed
        except Exception:
            logging.exception("Failed to list voices")
            return []

    # Phase 1: Multilingual TTS selection by language/name
    def set_tts_language(self, language_hint: str) -> bool:
        try:
            hint = (language_hint or "").lower().strip()
            ve = getattr(self, "tts_engine", None)
            if not ve:
                self.speak("TTS engine not initialized")
                return False

            voices_list = ve.get_voices()
            if not voices_list or not isinstance(voices_list, (list, tuple)):
                voices_list = []

            def matches(v):
                name = (getattr(v, "name", "") or "").lower()
                vid = (getattr(v, "id", "") or "").lower()
                langs = " ".join([str(x).lower() for x in getattr(v, "languages", [])])
                h = hint
                return (
                    h in name
                    or h in vid
                    or h in langs
                    or h.replace("_", "-") in name
                    or h.replace("_", "-") in vid
                    or h.replace("_", "-") in langs
                )

            candidates = [v for v in voices_list if matches(v)]
            selected = None

            if candidates:
                for v in candidates:
                    if any(
                        k in (getattr(v, "name", "") or "").lower()
                        for k in ["uk", "brit", "en-gb", "english (united kingdom)"]
                    ):
                        selected = v
                        break
                if not selected:
                    selected = candidates[0]
            else:
                short = hint.split("-")[0]
                for v in voices_list:
                    langs = " ".join([str(x).lower() for x in getattr(v, "languages", [])])
                    if short and short in langs:
                        selected = v
                        break

            if not selected:
                self.speak(f"I could not find a voice matching {language_hint}")
                return False

            voice_id = getattr(selected, "id", None)
            if voice_id is None:
                self.speak("Selected voice has no valid ID")
                return False

            ve.set_voice_id(voice_id)
            self.speak(f"Voice set to {getattr(selected, 'name', 'the selected voice')}")
            return True
        except Exception:
            logging.exception("Failed to set TTS language")
            return False

    def _select_best_voice_id(self):
        ve = getattr(self, "tts_engine", None)
        if not ve:
            return None

        voices_list = ve.get_voices()
        if not voices_list or not isinstance(voices_list, (list, tuple)):
            voices_list = []

        def score(v):
            name = (getattr(v, 'name', '') or '').lower()
            vid = (getattr(v, 'id', '') or '').lower()
            gender = (getattr(v, 'gender', '') or '').lower()
            langs = ' '.join([str(x).lower() for x in getattr(v, 'languages', [])])
            s = 0
            # Strong preferences: British + Male
            if 'brit' in name or 'uk' in name or 'united kingdom' in langs or 'en-gb' in langs or 'en_gb' in vid:
                s += 30
            if 'male' in gender or 'male' in name or 'male' in vid:
                s += 15
            # Known good voices
            if any(k in name for k in ['david', 'google uk english male']):
                s += 25
            if 'hazel' in name:
                s += 10
            if any(k in name for k in ['baritone', 'bass', 'deep']):
                s += 12
            if any(k in name for k in ['professional', 'pro', 'authority', 'authoritative']):
                s += 6
            if 'us' in name or 'zira' in name or 'zira' in vid:
                s -= 5
            return s

        best = None
        best_score = -10**9
        for v in voices_list:
            sc = score(v)
            if sc > best_score:
                best = v
                best_score = sc

        logging.info(f"Selected voice: {getattr(best, 'name', 'default')} (score={best_score})")
        return getattr(best, 'id', None)

    def test_butler_voice(self):
        phrases = [
            "At your command, sir. Sebas awaits your instructions.",
            "The system is fully operational.",
            "I have adjusted the parameters to your preference.",
            "Shall I proceed with the next task?",
        ]
        for p in phrases:
            self.speak(p)
    # ----------------------- Listening -----------------------
        def listen(self, timeout=5, phrase_time_limit=10):
            if self.microphone is None:
                logging.warning("Microphone not available.")
                return ""

            # ===== Capture audio =====
            try:
                with self.audio_lock:
                    try:
                        source_cm = sr.Microphone(device_index=self.microphone_device_index)
                    except Exception:
                        source_cm = sr.Microphone()

                    with source_cm as source:
                        if not hasattr(self, "_mic_calibrated"):
                            if getattr(source, "stream", None):
                                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                                self._mic_calibrated = True

                        try:
                            requests.post("http://127.0.0.1:5000/api/status",
                                        json={"mic": "listening"}, timeout=0.25)
                        except Exception:
                            pass

                        audio = self.recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_time_limit
                        )

            except sr.WaitTimeoutError:
                return ""
            except Exception as e:
                logging.exception(f"Error while listening: {e}")
                return ""

            # ===== Recognition =====
            try:
                try:
                    requests.post("http://127.0.0.1:5000/api/level",
                                json={"level": 0.2}, timeout=0.2)
                except Exception:
                    pass

                text = ""

                with self.audio_lock:
                    # Try Vosk first
                    try:
                        text = self.recognizer.recognize_vosk(audio).lower()
                    except Exception:
                        # Google fallback safely
                        if hasattr(self.recognizer, "recognize_google"):
                            google_recognizer = getattr(self.recognizer, "recognize_google")
                            try:
                                text = google_recognizer(audio).lower()
                            except sr.UnknownValueError:
                                return ""
                            except sr.RequestError as e:
                                logging.error(f"Speech recognition service error: {e}")
                                self.speak("Speech recognition service unavailable")
                                return ""
                        else:
                            logging.error("Google recognition is not available.")
                            return ""

                logging.debug(f"Recognized: {text}")
                return text

            except Exception as e:
                logging.exception(f"Unexpected recognition error: {e}")
                return ""

            finally:
                try:
                    requests.post("http://127.0.0.1:5000/api/status",
                                json={"mic": "idle"}, timeout=0.25)
                except Exception:
                    pass

    # ----------------------- Command Parsing -----------------------
    @safe_call(log_message="Error executing command", speak_message=None)
    def parse_and_execute(self, command):
        raw_command = (command or "").strip()

        # Авто-детект языка (без lower)
        try:
            lm = getattr(self, 'language_manager', None)
            if lm is not None:
                lm.detect_language(raw_command)
        except Exception:
            pass

        command = raw_command.lower()
        if not command:
            logging.warning("Empty command received")
            return

        # Быстрая смена языка: "language xx" / "set language xx"
        try:
            if command.startswith('language ') or command.startswith('set language'):
                arg = command
                arg = arg.replace('set language', '').replace('language', '').strip()
                code = self._parse_language_code(arg)
                if code:
                    lm = getattr(self, 'language_manager', None)
                    if lm is not None:
                        if lm.set_language(code):
                            self.speak(f"Language set to {lm.get_current_language_name()}")
                            return
                self.speak("Unsupported language")
                return
        except Exception:
            logging.exception("Language switch handling failed")

        logging.info(f"parse_and_execute called with command: '{command}'")

        # "service ..." → синтаксический сахар для open
        try:
            if command.startswith('service '):
                service_cmd = command[len('service '):].strip()
                if service_cmd.startswith('open '):
                    command = 'open ' + service_cmd[len('open '):].strip()
                elif len(service_cmd) == 0 or service_cmd == 'open':
                    self.speak("What application would you like to open?")
                    app_name = self.listen(timeout=5)
                    if app_name:
                        command = f"open {app_name}"
                    else:
                        return
                else:
                    command = 'open ' + service_cmd
        except Exception:
            logging.exception("Service alias handling failed")

        # ---------- NLU БЛОК (вынесен из except!) ----------
        intent = None
        intent_name_for_check = command
        suggestions = []

        try:
            nlu = getattr(self, 'nlu', None)
            if nlu:
                logging.debug(f"Trying NLU for command: {command}")

                # Совместимость с разными версиями NLU
                if hasattr(nlu, "get_intent_with_confidence"):
                    intent, suggestions = nlu.get_intent_with_confidence(command)
                elif hasattr(nlu, "parse"):
                    parsed = nlu.parse(command)
                    if parsed:
                        class _Wrap:
                            def __init__(self):
                                self.name: str = ""
                                self.slots: dict = {}
                                self.confidence: float = 1.0
                                self.fuzzy_match = None
                            pass
                        intent = _Wrap()
                        intent.name = parsed.name
                        intent.slots = getattr(parsed, "slots", {}) or {}
                        intent.confidence = 1.0
                        intent.fuzzy_match = None
                        suggestions = []
                else:
                    logging.warning("NLU object has no known interface")

                if intent:
                    logging.info(f"NLU found intent: {getattr(intent, 'name', '?')} with confidence {getattr(intent, 'confidence', 1.0)}")
                else:
                    logging.debug("NLU did not find intent")
            else:
                logging.warning("NLU module not available")
        except Exception as e:
            logging.debug(f"NLU parse failed: {e}", exc_info=True)
            intent = None

        if intent:
            intent_name_for_check = intent.name
            try:
                self.context.add({
                    "type": "intent",
                    "name": intent.name,
                    "slots": getattr(intent, "slots", {}),
                    "confidence": getattr(intent, "confidence", 1.0)
                })
            except Exception:
                pass

            # Сообщение при низкой уверенности
            try:
                if getattr(intent, "confidence", 1.0) < 0.8:
                    confidence_msg = f"I detected '{intent.name}' with {intent.confidence:.1%} confidence."
                    if getattr(intent, 'fuzzy_match', None):
                        confidence_msg += f" Did you mean '{intent.fuzzy_match}'?"
                    self.speak(confidence_msg)
                    time.sleep(0.5)
            except Exception:
                pass

            if not self.has_permission(intent.name):
                logging.warning(f"Permission denied for intent: {intent.name}")
                return

            # Фикс кривого app_name у NLU
            try:
                if intent.name in ("open_app_with_context", "open_application"):
                    slots = getattr(intent, "slots", {}) or {}
                    app_slot = slots.get('app_name') or slots.get('application')
                    if not app_slot or len((app_slot or '').strip()) < 2:
                        import re as _re
                        m = _re.search(r"\bopen\s+(.+?)(?:\s+and\s+.+)?$", command)
                        if m:
                            fixed_app = m.group(1).strip().strip('"')
                            if fixed_app:
                                slots['app_name'] = fixed_app
                                intent.slots = slots
                                logging.info(f"Fixed app name slot to: {fixed_app}")
            except Exception:
                pass

            # Сначала пробуем skills
            try:
                logging.debug(f"Trying skills for intent: {intent.name}")
                handled = self.skill_registry.handle_intent(intent.name, getattr(intent, "slots", {}) or {})
            except Exception:
                handled = False

            if handled:
                logging.info(f"Skill handled intent: {intent.name}")
                return

            # Потом legacy intent handler
            logging.debug(f"Trying legacy handler for intent: {intent.name}")
            handled = self._handle_intent(intent.name, getattr(intent, "slots", {}) or {})
            if handled:
                logging.info(f"Legacy handler handled intent: {intent.name}")
                return

        # ---------- Если NLU не сработал ----------

        # Явный разбор "open <app>"
        try:
            import re as _re
            open_match = _re.search(r'(?:open|launch)\s+(.+)', command, _re.I)
            if open_match:
                app_name = (open_match.group(1) or '').strip().strip('"')
                sub_match = _re.search(r'^service\s+open\s+(.+)', command, _re.I)
                if sub_match:
                    app_name = (sub_match.group(1) or '').strip().strip('"')
                if app_name:
                    self.open_application(app_name)
                    return
                else:
                    self.speak("Please specify an application after 'open'.")
                    return
        except Exception:
            pass

        # Learned commands
        handled = self._try_handle_learned_command(command)
        if handled:
            return

        # Fallback через skills
        logging.debug(f"Trying fallback handling for command: {command}")
        fallback_intent, _ = self._extract_intent_from_command(command)
        if fallback_intent:
            logging.debug(f"Extracted fallback intent: {fallback_intent}")
            if not self.has_permission(fallback_intent):
                logging.warning(f"Permission denied for fallback intent: {fallback_intent}")
                return
        handled = self._handle_fallback_with_skills(command)
        if handled:
            logging.info(f"Fallback handling succeeded for: {command}")
            return

        # Legacy команды
        if command.startswith("learn ") or command.startswith("teach ") or "learn command" in command:
            self._handle_learn_intent(command)
            return
        elif command.startswith("forget ") or "forget command" in command or "remove command" in command:
            self._handle_forget_intent(command)
            return
        elif "list learned" in command or "learned commands" in command:
            self._handle_list_learned()
            return
        elif "create a note" in command:
            note = command.split("create a note")[-1].strip()
            self.create_note(note)
            return
        elif "take a screenshot" in command or "screenshot" in command:
            self.take_screenshot()
            return
        elif "ip address" in command:
            self.get_ip_address()
            return
        elif "speed test" in command:
            self.run_speed_test()
            return

        legacy_handled = self._handle_legacy_commands(command)
        if legacy_handled:
            return

        # Сообщение, если вообще ничего не поняли
        if suggestions:
            suggestion_text = "I didn't understand that command. Did you mean: " + ", or ".join(suggestions)
            self.speak(suggestion_text)
        else:
            self.speak("I beg your pardon; I did not quite catch the instruction, " + self.get_salutation() + ". Try saying 'help' for available commands.")
            logging.warning(f"Command not handled: '{command}'")

        
    def _handle_legacy_commands(self, command):
        """Handle old-style direct commands for backward compatibility, with permission checks."""
        if "shutdown" in command:
            if self.has_permission('shutdown_computer'):
                self.shutdown_computer()
                return True
        elif "restart" in command:
            if self.has_permission('restart_computer'):
                self.restart_computer()
                return True
        return False
    # ----------------------- Active Directory Integration (Phase 2) -----------------------
    def _initialize_ad_client(self):
        """Initialize Active Directory client from preferences."""
        try:
            from sebas.integrations.ad_client import ADClient
           
            ad_config = self.prefs.get_ad_config()
            if not ad_config.get('enabled', False):
                # AD not enabled, skip initialization
                self.ad_client = None
                return
           
            # Initialize AD client with configuration
            self.ad_client = ADClient(
                domain=ad_config.get('domain'),
                ldap_server=ad_config.get('ldap_server'),
                use_windows_auth=ad_config.get('use_windows_auth', True),
                bind_user=ad_config.get('bind_user')
            )
           
            # Apply role mappings from preferences
            role_mappings = ad_config.get('role_mappings', {})
            for group, role_name in role_mappings.items():
                try:
                    role = Role[role_name.upper()]
                    self.ad_client.set_role_mapping(group, role)
                except (KeyError, AttributeError):
                    logging.warning(f"Invalid role mapping: {group} -> {role_name}")
           
            logging.info("Active Directory client initialized")
        except Exception:
            logging.exception("Failed to initialize AD client")
            self.ad_client = None
   
    def _initialize_ad_authentication(self):
        """Authenticate with AD and set user role based on group membership."""
        try:
            if not hasattr(self, 'ad_client') or not self.ad_client:
                return
           
            if not self.ad_client.available():
                logging.info("AD integration not available")
                return
           
            # Get current user info
            user_info = self.ad_client.get_current_user()
            if user_info:
                logging.info(f"Current user: {user_info.get('username')} ({user_info.get('domain')})")
           
            # Try to connect to AD
            if self.ad_client.connect():
                # Get user's role from AD groups
                ad_role = self.ad_client.get_user_role()
                if ad_role:
                    # Set role in preferences (from AD)
                    self.prefs.set_user_role(ad_role, from_ad=True)
                    logging.info(f"User role set from AD: {ad_role.name}")
                   
                    # Get user groups for logging
                    groups = self.ad_client.get_user_groups()
                    if groups:
                        logging.info(f"User AD groups: {', '.join(groups[:10])}") # Log first 10 groups
                else:
                    logging.warning("Could not determine user role from AD")
            else:
                logging.warning("Failed to connect to Active Directory")
        except Exception:
            logging.exception("Failed to initialize AD authentication")
   
    def get_ad_user_info(self, username: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Get Active Directory user information.
       
        Args:
            username: Username to look up (optional, uses current user if not provided)
           
        Returns:
            Dict with user info or None
        """
        try:
            if not hasattr(self, 'ad_client') or not self.ad_client:
                return None
           
            if not self.ad_client.available():
                return None
           
            if username:
                return self.ad_client.lookup_user(username)
            else:
                return self.ad_client.get_current_user()
        except Exception:
            logging.exception("Failed to get AD user info")
            return None
   
    def authenticate_ad_user(self, username: str, password: str) -> bool:
        """
        Authenticate a user against Active Directory.
       
        Args:
            username: Username
            password: Password
           
        Returns:
            True if authentication successful
        """
        try:
            if not hasattr(self, 'ad_client') or not self.ad_client:
                return False
           
            if not self.ad_client.available():
                return False
           
            return self.ad_client.authenticate_user(username, password)
        except Exception:
            logging.exception("AD authentication failed")
            return False
    # ----------------------- Utilities -----------------------
    def confirm_action(self, question):
        try:
            # Preference: allow skipping confirmations
            try:
                if hasattr(self, 'prefs') and self.prefs.get_pref('confirm_actions', True) is False:
                    return True
            except Exception:
                pass
            self.speak(question)
            response = self.listen(timeout=7, phrase_time_limit=5)
            return any(w in (response or "").lower() for w in ["yes", "yep", "confirm", "do it", "proceed", "affirmative"])
        except Exception:
            logging.exception("Confirmation check failed.")
            # Fail safe: if listening fails, do not proceed with the action.
            return False
    def has_permission(self, intent_name: str) -> bool:
        """Checks if the current user role has permission to execute an intent."""
        try:
            required_role = get_permission_for_intent(intent_name)
            user_role = self.prefs.get_user_role()
           
            # Ensure both are Role enum instances
            if not isinstance(user_role, type(required_role)) or not isinstance(required_role, type(user_role)):
                logging.error(f"Invalid role types: user_role={type(user_role)}, required_role={type(required_role)}")
                # Default to allowing if there's a type mismatch (fail open for now)
                return True
           
            # Compare enum values (ADMIN=2 > STANDARD=1)
            def role_to_int(role) -> int:
                if hasattr(role, 'value'):
                    return int(role.value)
                try:
                    return int(role)
                except Exception:
                    raise TypeError(f"Cannot convert {role!r} to int")
            user_value = role_to_int(user_role)
            required_value = role_to_int(required_role)
            if user_value >= required_value:
                return True
            else:
                self.speak(f"I'm sorry, that action requires {required_role.name.capitalize()} privileges.")
                logging.warning(f"Permission denied for user role '{user_role.name}' on intent '{intent_name}' (requires '{required_role.name}')")
                return False
        except Exception as e:
            logging.exception(f"Error checking permission for intent '{intent_name}': {e}")
            # Default to allowing if there's an error (fail open for now)
            return True
    # ----------------------- Program Indexing -----------------------
    def _load_program_index(self):
        try:
            if os.path.isfile(self.program_index_file):
                with open(self.program_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            return {}
        except Exception:
            logging.exception("Failed to load program index")
            return {}
    def _save_program_index(self):
        try:
            with open(self.program_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.program_index, f, ensure_ascii=False, indent=2)
        except Exception:
            logging.exception("Failed to save program index")
    def _maybe_scan_programs_startup(self, max_age_days=7):
        try:
            needs_scan = False
            if not self.program_index:
                needs_scan = True
            else:
                try:
                    mtime = os.path.getmtime(self.program_index_file)
                    age_days = max(0, (time.time() - mtime) / 86400.0)
                    if age_days > max_age_days:
                        needs_scan = True
                except Exception:
                    needs_scan = True
            if needs_scan:
                threading.Thread(target=self.scan_installed_programs, daemon=True).start()
        except Exception:
            logging.exception("Startup program scan check failed")
    def _start_program_rescan_thread(self):
        def _loop():
            while True:
                try:
                    time.sleep(max(1, int(self.program_rescan_interval_hours * 3600)))
                    self.scan_installed_programs()
                except Exception:
                    logging.exception("Background program rescan failed")
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
    def scan_installed_programs(self):
        try:
            index = {}
            # 1) Start Menu shortcuts (User and All Users)
            start_menu_paths = [
                os.path.join(os.environ.get('ProgramData', r'C:\\ProgramData'), r'Microsoft\\Windows\\Start Menu\\Programs'),
                os.path.join(os.path.expanduser('~'), r'AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs'),
            ]
            for base in start_menu_paths:
                for root, _, files in os.walk(base):
                    for file in files:
                        if file.lower().endswith('.lnk'):
                            name = os.path.splitext(file)[0].lower()
                            index[name] = os.path.join(root, file)
            # 2) Registry Uninstall keys for DisplayName -> InstallLocation/DisplayIcon
            uninstall_roots = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
            ]
            for root, path in uninstall_roots:
                try:
                    with winreg.OpenKey(root, path) as key:
                        for i in range(0, winreg.QueryInfoKey(key)[0]):
                            try:
                                subname = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subname) as subkey:
                                    display_name = self._reg_get_string(subkey, 'DisplayName')
                                    if not display_name:
                                        continue
                                    display_icon = self._reg_get_string(subkey, 'DisplayIcon')
                                    install_loc = self._reg_get_string(subkey, 'InstallLocation')
                                    exe_path = None
                                    # Prefer DisplayIcon if it points to an exe
                                    if display_icon and os.path.exists(display_icon.split(',')[0].strip('"')):
                                        exe_path = display_icon.split(',')[0].strip('"')
                                    elif install_loc and os.path.isdir(install_loc):
                                        # try common exe name matching first 1-2 levels
                                        exe_path = self._find_primary_exe(install_loc, max_depth=2)
                                    if exe_path:
                                        index[display_name.lower()] = exe_path
                            except Exception:
                                continue
                except Exception:
                    continue
            # 3) Common quick executables in Program Files root folders (shallow)
            for pf in [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')]:
                if not pf or not os.path.isdir(pf):
                    continue
                for entry in os.listdir(pf):
                    full = os.path.join(pf, entry)
                    if os.path.isdir(full):
                        exe = self._find_primary_exe(full, max_depth=1)
                        if exe:
                            index[entry.lower()] = exe
            # Merge with existing and save
            self.program_index.update(index)
            self._save_program_index()
            logging.info(f"Program scan complete. {len(self.program_index)} entries indexed")
            return len(self.program_index)
        except Exception:
            logging.exception("Program scan failed")
            self.speak("Program scan failed")
            return 0
    def _reg_get_string(self, key, value_name):
        try:
            val, typ = winreg.QueryValueEx(key, value_name)
            if isinstance(val, str):
                return val
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None
    def _find_primary_exe(self, base_dir, max_depth=2):
        try:
            base_dir = os.path.abspath(base_dir)
            for root, dirs, files in os.walk(base_dir):
                depth = root[len(base_dir):].count(os.sep)
                if depth > max_depth:
                    # do not descend further
                    dirs[:] = []
                    continue
                for f in files:
                    if f.lower().endswith('.exe') and 'unins' not in f.lower() and 'uninstall' not in f.lower():
                        return os.path.join(root, f)
            return None
        except Exception:
            return None
    def _handle_list_programs(self, limit=20):
        try:
            if not getattr(self, 'program_index', None):
                self.speak("I don't have any programs indexed yet. Say learn programs to scan.")
                return
            names = sorted(list(self.program_index.keys()))[:limit]
            self.speak("Some programs I can open are: " + ", ".join(names))
        except Exception:
            logging.exception("List programs failed")
    # ----------------------- Learning -----------------------
    def _load_learned_commands(self):
        try:
            if os.path.isfile(self.learned_file):
                with open(self.learned_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            return {}
        except Exception:
            logging.exception("Failed to load learned commands")
            return {}
    def _save_learned_commands(self):
        try:
            with open(self.learned_file, 'w', encoding='utf-8') as f:
                json.dump(self.learned_commands, f, ensure_ascii=False, indent=2)
        except Exception:
            logging.exception("Failed to save learned commands")
    def _try_handle_learned_command(self, command_text):
        try:
            if not self.learned_commands:
                return False
            # 1) Pattern matches with {slots}
            for key, action in self.learned_commands.items():
                is_pattern = action.get('is_pattern') or ('{' in key and '}' in key)
                if not is_pattern:
                    continue
                regex = self._pattern_to_regex(key)
                try:
                    m = re.search(regex, command_text)
                except re.error:
                    m = None
                if m:
                    params = {k: (v or '').strip() for k, v in m.groupdict().items()}
                    return self._execute_learned_action(action, params)
            # 2) Exact match
            if command_text in self.learned_commands:
                action = self.learned_commands[command_text]
                return self._execute_learned_action(action)
            # 3) Contained match (longest key wins)
            candidates = [(k, v) for k, v in self.learned_commands.items() if k in command_text]
            if candidates:
                candidates.sort(key=lambda kv: len(kv[0]), reverse=True)
                return self._execute_learned_action(candidates[0][1])
            return False
        except Exception:
            logging.exception("Failed to handle learned command")
            return False
   
    # def run_shell_command(self, cmd):
    # if not self.has_permission('run_shell_command'):
    # return
    # success, response = self.service_client.send_command('run_shell', {'cmd': cmd})
    # if success:
    # self.speak("Command sent to the service for execution.")
    # if isinstance(response, dict):
    # output = response.get('stdout') or response.get('stderr')
    # else:
    # output = str(response)
    # logging.info(f"Service command output: {output}")
    # else:
    # self.speak(f"Command failed. {response}")
    def _execute_learned_action(self, action, params=None):
        try:
            a_type = (action or {}).get('type')
            value = (action or {}).get('value')
            if params and isinstance(value, str):
                try:
                    value = value.format(**params)
                except Exception:
                    pass
            if not a_type or not value:
                return False
            if a_type == 'shell':
                self.run_shell_command(value)
                return True
            if a_type == 'open':
                self.open_application(value)
                return True
            if a_type == 'speak':
                self.speak(value)
                return True
            return False
        except Exception:
            logging.exception("Learned action execution failed")
            return False
    def _pattern_to_regex(self, pattern_text):
        # Convert a phrase with {slot} into a regex with named groups
        # Example: "open project {name}" -> r"open\s+project\s+(?P<name>.+)"
        text = pattern_text.strip()
        # Collapse whitespace to \s+
        text = re.sub(r"\s+", r" ", text)
        # Escape regex special chars except braces
        safe = ''
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '{':
                j = text.find('}', i + 1)
                if j != -1:
                    slot = text[i+1:j].strip()
                    safe += rf"(?P<{slot}>.+)"
                    i = j + 1
                    continue
            # escape
            if ch in "+*?^$|[]()\\.":
                safe += '\\' + ch
            elif ch == ' ':
                safe += r"\s+"
            else:
                safe += ch
            i += 1
        return safe
    def _handle_learn_intent(self, command):
        try:
            # Patterns supported:
            # "learn when i say <phrase> run command <cmd>"
            # "learn command <phrase> => <cmd>"
            # "learn <phrase> open <app>"
            phrase = ""
            action = {}
            text = command.replace('teach', 'learn')
            if '=>' in text:
                left, right = text.split('=>', 1)
                phrase = left.replace('learn command', '').replace('learn', '').strip().strip('"')
                action = {'type': 'shell', 'value': right.strip().strip('"')}
            elif 'run command' in text:
                parts = text.split('run command', 1)
                phrase = parts[0].replace('learn command', '').replace('learn', '').replace('when i say', '').strip().strip('"')
                action = {'type': 'shell', 'value': parts[1].strip().strip('"')}
            elif ' open ' in text:
                parts = text.split(' open ', 1)
                phrase = parts[0].replace('learn command', '').replace('learn', '').strip().strip('"')
                action = {'type': 'open', 'value': parts[1].strip().strip('"')}
            elif ' say ' in text and ' speak ' in text:
                # e.g., learn when I say X speak Hello
                parts = text.split(' speak ', 1)
                phrase = parts[0].replace('learn command', '').replace('learn', '').replace('when i say', '').strip().strip('"')
                action = {'type': 'speak', 'value': parts[1].strip().strip('"')}
            phrase = (phrase or '').lower()
            if phrase and action.get('type') and action.get('value'):
                if '{' in phrase and '}' in phrase:
                    action['is_pattern'] = True
                self.learned_commands[phrase] = action
                self._save_learned_commands()
                self.speak("Learned new command")
            else:
                self.speak("Please say, learn when I say phrase, run command, followed by the command")
        except Exception:
            logging.exception("Learn intent failed")
            self.speak("I failed to learn that command")
    def _handle_forget_intent(self, command):
        try:
            text = command.replace('remove command', 'forget').replace('forget command', 'forget')
            key = text.split('forget', 1)[-1].strip().strip('"').lower()
            if key:
                target = None
                if key in self.learned_commands:
                    target = key
                else:
                    # fuzzy contains
                    for k in self.learned_commands.keys():
                        if key in k:
                            target = k
                            break
                if target:
                    del self.learned_commands[target]
                    self._save_learned_commands()
                    self.speak("Forgot that command")
                    return
            self.speak("I could not find that learned command")
        except Exception:
            logging.exception("Forget intent failed")
    def _handle_list_learned(self):
        try:
            if not self.learned_commands:
                self.speak("No learned commands yet")
                return
            phrases = []
            for k, v in list(self.learned_commands.items())[:10]:
                tag = " (pattern)" if v.get('is_pattern') or ('{' in k and '}' in k) else ""
                phrases.append(k + tag)
            self.speak("Top learned commands are: " + ", ".join(phrases))
        except Exception:
            logging.exception("List learned failed")
    # ----------------------- Skill-based Fallback Handling -----------------------
    def _handle_fallback_with_skills(self, command):
        """
        Try to handle commands using skills when NLU fails.
        This method attempts to extract intents and slots from raw text commands.
        """
        try:
            # Extract basic intents from command text
            intent, slots = self._extract_intent_from_command(command)
            if intent:
                logging.info(f"Fallback extracted intent: {intent} with slots: {slots}")
                handled = self.skill_registry.handle_intent(intent, slots)
                if handled:
                    logging.info(f"Fallback skill successfully handled: {intent}")
                else:
                    logging.debug(f"Fallback skill did not handle: {intent}")
                return handled
            else:
                logging.debug(f"Fallback could not extract intent from: {command}")
            return False
        except Exception as e:
            logging.exception(f"Fallback skill handling failed: {e}")
            return False
    def _extract_intent_from_command(self, command):
        """
        Extract intent and slots from raw command text.
        Returns (intent_name, slots_dict) or (None, None)
        """
        cmd = command.lower()
        # System commands
        if "shutdown in" in cmd:
            try:
                minutes = int(cmd.split("shutdown in")[-1].replace("minutes", "").strip())
                return 'schedule_shutdown', {'minutes': minutes}
            except:
                pass
        elif "shutdown" in cmd:
            return 'shutdown_computer', {}
        elif "restart" in cmd or "reboot" in cmd:
            return 'restart_computer', {}
        elif "lock" in cmd:
            return 'lock_computer', {}
        elif "sleep" in cmd:
            return 'sleep_computer', {}
        elif "hibernate" in cmd:
            return 'hibernate_computer', {}
        elif "log off" in cmd or "sign out" in cmd:
            return 'log_off_user', {}
        # Volume and brightness
        elif "volume" in cmd:
            if "mute" in cmd:
                return 'set_volume', {'level': 0}
            else:
                try:
                    level = int(cmd.split("volume")[-1].replace("percent", "").strip())
                    return 'set_volume', {'level': level}
                except:
                    pass
        elif "brightness" in cmd:
            if "maximum" in cmd:
                return 'set_brightness', {'level': 100}
            elif "minimum" in cmd:
                return 'set_brightness', {'level': 0}
            else:
                try:
                    level = int(cmd.split("brightness to")[-1].replace("percent", "").strip())
                    return 'set_brightness', {'level': level}
                except:
                    pass
        # CPU and processes
        elif "cpu usage" in cmd or ("cpu" in cmd and ("show" in cmd or "usage" in cmd or "use" in cmd)):
            return 'get_cpu_info', {}
        elif "list processes" in cmd or "running processes" in cmd:
            return 'list_processes', {}
        elif "kill process" in cmd:
            proc_name = cmd.split("kill process")[-1].strip()
            if proc_name:
                return 'kill_process', {'process_name': proc_name}
        # System status queries
        elif "system status" in cmd or "what's my system status" in cmd or "check system" in cmd:
            return 'get_system_status', {}
        elif "memory usage" in cmd or ("memory" in cmd and ("show" in cmd or "usage" in cmd or "check" in cmd)):
            return 'get_memory_info', {}
        elif "check memory" in cmd or "show memory" in cmd:
            return 'get_memory_info', {}
       
        # Application commands
        elif "open" in cmd:
            app_name = cmd.split("open")[-1].strip()
            return 'open_application', {'app_name': app_name}
        elif "close" in cmd:
            app_name = cmd.split("close")[-1].strip()
            return 'close_application', {'app_name': app_name}
        elif "list programs" in cmd or "list installed programs" in cmd:
            return 'list_programs', {}
        elif "learn programs" in cmd or "scan programs" in cmd or "rescan programs" in cmd:
            return 'scan_programs', {}
        # File commands
        elif "create folder" in cmd:
            path = cmd.split("create folder")[-1].strip().strip('"')
            return 'create_folder', {'path': path}
        elif "delete" in cmd:
            path = cmd.split("delete")[-1].strip().strip('"')
            return 'delete_path', {'path': path}
        # Search
        elif "search for" in cmd:
            query = cmd.split("search for")[-1].strip()
            return 'web_search', {'query': query}
        # Weather
        elif "weather" in cmd:
            return 'get_weather', {}
        # Battery status
        elif "battery" in cmd or "charge" in cmd:
            return 'get_battery_status', {}
        # Printers
        elif "print test page" in cmd:
            return 'print_test_page', {}
        elif "list printers" in cmd or "show printers" in cmd:
            return 'list_printers', {}
        elif "set default printer" in cmd:
            # supports: set default printer to <name>
            try:
                if " to " in cmd:
                    target = cmd.split("set default printer", 1)[1].split(" to ", 1)[1].strip().strip('"')
                else:
                    target = cmd.split("set default printer", 1)[1].strip().strip('"')
            except Exception:
                target = ''
            return 'set_default_printer', {'printer_name': target}
        # User sessions
        elif "list sessions" in cmd or "active users" in cmd or "list user sessions" in cmd:
            return 'list_user_sessions', {}
        # Voice/Language controls
        elif "list voices" in cmd or "available voices" in cmd:
            return 'list_voices', {}
        elif ("set language to" in cmd) or ("change language to" in cmd) or ("set voice to" in cmd) or ("change voice to" in cmd):
            try:
                lang = cmd.split("to", 1)[1].strip().strip('"')
            except Exception:
                lang = ''
            return 'set_tts_language', { 'language': lang }
        # Single-word app open fallback (e.g., "notepad")
        try:
            if ' ' not in cmd and cmd.isalpha() and len(cmd) >= 2:
                return 'open_application', {'app_name': cmd}
        except Exception:
            pass
        return None, None
    # ----------------------- Intent Handling -----------------------
    def _handle_intent(self, name, slots):
        try:
            if name == 'set_voice':
                return self.set_voice_profile(slots.get('profile'))
            if name == 'list_voices':
                try:
                    voices = self.list_available_voices() or []
                    if not voices:
                        self.speak("No voices available")
                        return True
                    # Speak top few options
                    names = [v.get('name') or v.get('id') for v in voices][:5]
                    self.speak("Top available voices: " + ", ".join([n for n in names if n]))
                except Exception:
                    logging.exception("list_voices failed")
                return True
            if name == 'set_tts_language':
                return self.set_tts_language(slots.get('language') or '')
            if name == 'adjust_voice_rate':
                try:
                    return self.adjust_voice(rate=int(slots.get('rate')))
                except Exception:
                    return False
            if name == 'adjust_voice_volume':
                try:
                    v = int(slots.get('volume'))
                    if not self._validate_range(v, 0, 100):
                        return False
                    return self.adjust_voice(volume=v/100.0)
                except Exception:
                    return False
            if name == 'adjust_voice_pitch':
                try:
                    return self.adjust_voice(pitch=int(slots.get('pitch')))
                except Exception:
                    return False
            # if name == 'smarthome_toggle':
            # ent = (slots.get('device') or '').replace(' ', '_')
            # state = (slots.get('state') or 'off') == 'on'
            # ok = self.smarthome.set_switch(f"switch.{ent}", state) if getattr(self, 'smarthome', None) else False
            # self.speak("Done" if ok else "Unable to control that device")
            # return True
            if name == 'schedule_event':
                title = slots.get('title') or 'Untitled'
                when_text = slots.get('time') or ''
                dt = None
                try:
                    # naive parse: accept 'tomorrow 9am' or 'today 3pm'
                    now = datetime.now()
                    if 'tomorrow' in when_text:
                        base = now + timedelta(days=1)
                        tm = when_text.replace('tomorrow', '').strip()
                    elif 'today' in when_text:
                        base = now
                        tm = when_text.replace('today', '').strip()
                    else:
                        base = now
                        tm = when_text
                    tm = tm.replace('am',' am').replace('pm',' pm').strip()
                    # parse hour
                    m = re.search(r"(\d{1,2})\s*(am|pm)?", tm)
                    if m:
                        h = int(m.group(1))
                        mer = m.group(2)
                        if mer == 'pm' and h < 12:
                            h += 12
                        if mer == 'am' and h == 12:
                            h = 0
                        dt = base.replace(hour=h, minute=0, second=0, microsecond=0)
                except Exception:
                    dt = None
                if dt is None:
                    self.speak("I could not parse the time for that event")
                    return True
                if getattr(self, 'calendar', None):
                    provider = "microsoft" # or whatever provider you use
                    event_title = title
                   
                    start_iso = dt.isoformat()
                    end_iso = (dt + timedelta(hours=1)).isoformat()
                    ok, msg = self.calendar.add_event(
                        provider=provider,
                        title=event_title,
                        start_iso=start_iso,
                        end_iso=end_iso,
                        description="" # optional
                    )
                else:
                    ok = False
                self.speak("Event scheduled" if ok else "Failed to schedule event")
                return True
            if name == 'send_email':
                ok = self.email.send_mail(slots.get('to'), slots.get('subject'), slots.get('body')) if getattr(self, 'email', None) else False
                self.speak("Email sent" if ok else "Failed to send email")
                return True
            if name == 'open_app_with_context':
                self.open_application(slots.get('app_name'))
                return True
            if name == 'get_battery_status':
                self.get_battery_status()
                return True
            if name == 'list_printers':
                self.list_printers()
                return True
            if name == 'set_default_printer':
                self.set_default_printer(slots.get('printer_name') or '')
                return True
            if name == 'print_test_page':
                self.print_test_page()
                return True
            if name == 'list_user_sessions':
                self.list_user_sessions()
                return True
            return False
        except Exception:
            logging.exception("_handle_intent failed")
            return False
    # Phase 1: Battery monitoring
    def get_battery_status(self):
        if not self.has_permission('get_battery_status'): return
        try:
            batt = None
            try:
                batt = psutil.sensors_battery()
            except Exception:
                batt = None
            if not batt:
                self.speak("I could not access battery information on this system")
                return
            percent = int(getattr(batt, 'percent', 0) or 0)
            plugged = bool(getattr(batt, 'power_plugged', False))
            secs_left = getattr(batt, 'secsleft', None)
            if plugged:
                status = "and charging" if percent < 100 else "and fully charged"
                self.speak(f"Battery is at {percent} percent {status}")
            else:
                # Estimate time remaining if available
                eta = ""
                try:
                    if secs_left and secs_left > 0:
                        hrs = int(secs_left // 3600)
                        mins = int((secs_left % 3600) // 60)
                        if hrs > 0 or mins > 0:
                            eta = f", approximately {hrs} hours and {mins} minutes remaining"
                except Exception:
                    eta = ""
                self.speak(f"Battery is at {percent} percent{eta}")
        except Exception:
            logging.exception("Failed to get battery status")
            self.speak("Unable to retrieve battery information")
    # ----------------------- System/Admin Actions -----------------------
    def is_admin(self):
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    def shutdown_computer(self):
        if not self.has_permission('shutdown_computer'): return
        if self.confirm_action("Are you sure you want to shut down the computer?"):
            self.speak("Shutting down now.")
            success, response = self.service_client.send_command('shutdown', {'delay': 1})
            if not success:
                self.speak(f"Failed to initiate shutdown. {response}")
        else:
            self.speak("Shutdown cancelled.")
    def restart_computer(self):
        if not self.has_permission('restart_computer'): return
        if self.confirm_action("Are you sure you want to restart the computer?"):
            self.speak("Restarting now.")
            success, response = self.service_client.send_command('restart', {'delay': 1})
            if not success:
                self.speak(f"Failed to initiate restart. {response}")
        else:
            self.speak("Restart cancelled.")
    def schedule_shutdown(self, minutes):
        if not self.has_permission('schedule_shutdown'): return
        if not self.confirm_action(f"Are you sure you want to schedule a shutdown in {minutes} minutes?"):
            self.speak("Shutdown scheduling cancelled.")
            return
        try:
            seconds = max(0, int(minutes) * 60)
            success, response = self.service_client.send_command('shutdown', {'delay': seconds})
            if success:
                self.speak(f"Shutdown scheduled in {minutes} minutes")
            else:
                self.speak(f"Failed to schedule shutdown. {response}")
        except Exception as e:
            logging.exception("Failed to schedule shutdown")
            self.speak(f"Failed to schedule shutdown. {e}")
    def lock_computer(self):
        if not self.has_permission('lock_computer'): return
        try:
            # This one doesn't require admin, but for consistency, we can move it.
            success, response = self.service_client.send_command('lock_workstation')
            if not success:
                self.speak(f"Failed to lock. {response}")
        except Exception:
            logging.exception("Failed to lock workstation")
    def sleep_computer(self):
        if not self.has_permission('sleep_computer'): return
        try:
            # This is a privileged operation
            success, response = self.service_client.send_command('run_shell', {'cmd': 'rundll32.exe powrprof.dll,SetSuspendState Sleep'})
            if not success:
                self.speak(f"Failed to sleep. {response}")
        except Exception:
            logging.exception("Failed to sleep")
    def hibernate_computer(self):
        try:
            ctypes.windll.powrprof.SetSuspendState(True, True, True)
        except Exception:
            logging.exception("Failed to hibernate")
    def log_off_user(self):
        try: # This does not require admin
            if self.confirm_action("Are you sure you want to sign out?"):
                subprocess.run(["shutdown", "/l"], check=False)
        except Exception: # pragma: no cover
            logging.exception("Failed to sign out")
    def empty_recycle_bin(self):
        try:
            # SHERB_NOCONFIRMATION(0x00000001) | SHERB_NOPROGRESSUI(0x00000002) | SHERB_NOSOUND(0x00000004)
            flags = 0x00000001 | 0x00000002 | 0x00000004
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            self.speak("Recycle bin emptied")
        except Exception:
            logging.exception("Failed to empty recycle bin")
            self.speak("Failed to empty recycle bin")
    def list_processes(self, limit=10):
        if not self.has_permission('list_processes'): return
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
                procs.append(p.info)
            procs.sort(key=lambda x: (x.get("cpu_percent") or 0), reverse=True)
            top = procs[:limit]
            names = ", ".join(f"{p.get('name')} ({p.get('pid')})" for p in top if p.get('name'))
            self.speak(f"Top processes: {names}")
        except Exception:
            logging.exception("Failed to list processes")
    def kill_process(self, name_or_pid):
        if not self.has_permission('kill_process'): return
        try:
            # Killing other users' processes requires admin
            success, response = self.service_client.send_command('run_shell', {'cmd': f'taskkill /F /IM "{name_or_pid}" /T'})
            if not success:
                # Fallback to non-admin for current user's processes
                killed = getattr(self, '_kill_process_local', lambda x: 0)(name_or_pid)
                if killed > 0:
                    self.speak(f"Terminated {killed} of your processes.")
                else:
                    self.speak(f"Could not terminate process. {response}")
            else:
                self.speak(f"Termination signal sent to {name_or_pid}.")
        except Exception:
            logging.exception("Failed to kill process")
    def create_folder(self, path):
        if not self.has_permission('create_folder'): return
        try:
            os.makedirs(path, exist_ok=True)
            self.speak("Folder created")
        except Exception:
            logging.exception("Failed to create folder")
            self.speak("Failed to create folder")
    def delete_path(self, path):
        if not self.has_permission('delete_path'): return
        try:
            if not self.confirm_action(f"Are you sure you want to permanently delete {os.path.basename(path)}?"):
                self.speak("Deletion cancelled.")
                return
           
            # Use service for privileged deletion
            success, response = self.service_client.send_command('delete_path', {'path': path})
            if success:
                self.speak("Deleted successfully")
            else:
                self.speak(f"Failed to delete. {response}")
        except Exception:
            logging.exception("Failed to delete path")
            self.speak("Failed to delete path")
    def run_shell_command(self, cmd):
        if not self.has_permission('run_shell_command'):
            return
        success, response = self.service_client.send_command('run_shell', {'cmd': cmd})
        if success:
            self.speak("Command sent to the service for execution.")
            # Ensure response is a dict before calling .get()
            if isinstance(response, dict):
                output = response.get('stdout') or response.get('stderr')
            else:
                output = str(response) # fallback if response is string
            logging.info(f"Service command output: {output}")
        else:
            self.speak(f"Command failed. {response}")
    # ----------------------- Windows App Control -----------------------
    def open_application(self, app_name):
        if not self.has_permission('open_application'): return
        apps = {
            "notepad": "notepad.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "word": "winword.exe"
        }
        name = (app_name or "").lower()
        # Common synonyms for "This PC/My Computer"
        if name in ("my computer", "this pc", "computer", "thispc"):
            try:
                subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"]) # Works on modern Windows
                self.speak(f"Opening {app_name} as requested, {self.get_salutation()}.")
                return
            except Exception:
                logging.exception("Failed to open 'This PC'")
        exe = apps.get(name)
        if exe is None and getattr(self, 'program_index', None):
            if name in self.program_index:
                exe = self.program_index[name]
            else:
                candidates = []
                for k, v in self.program_index.items():
                    if k.startswith(name) or name in k:
                        candidates.append((k, v))
                if candidates:
                    candidates.sort(key=lambda kv: (not kv[0].startswith(name), len(kv[0])))
                    exe = candidates[0][1]
        if exe is None:
            exe = app_name
       
        # Ensure we have a valid executable path or name
        if not exe:
            self.speak(f"Could not find application '{app_name}'")
            return
       
        try:
            # Handle .lnk shortcuts
            if isinstance(exe, str) and exe.lower().endswith('.lnk'):
                subprocess.Popen(exe, shell=True)
            # Handle full paths or executable names
            elif isinstance(exe, str) and (os.path.exists(exe) or os.path.isfile(exe)):
                # Full path to executable
                subprocess.Popen([exe])
            elif isinstance(exe, str) and os.path.sep in exe:
                # Path with separators but might not exist - try anyway
                subprocess.Popen([exe])
            else:
                # Just executable name - try with shell
                subprocess.Popen(exe, shell=True)
            self.speak(f"Opening {app_name} as requested, {self.get_salutation()}.")
        except Exception as e:
            logging.exception(f"Failed to open {app_name} (exe: {exe})")
            self.speak(f"Failed to open {app_name}")
    def close_application(self, app_name):
        if not self.has_permission('close_application'): return
        closed = False
        for proc in psutil.process_iter(['name']):
            try:
                if app_name.lower() in (proc.info.get('name') or '').lower():
                    proc.kill()
                    closed = True
            except Exception:
                continue
        if closed:
            self.speak(f"{app_name} has been closed, {self.get_salutation()}.")
        else:
            self.speak(f"No running application found with name {app_name}")
    def web_search(self, query):
        if not self.has_permission('web_search'): return
        # Handle both skill-based and direct calls
        if hasattr(self, 'skill_registry'):
            return self.skill_registry.handle_intent('web_search', {'query': query})
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        self.speak(f"Commencing search for {query}.")
        return True
    def set_volume(self, level):
        if not self.has_permission('set_volume'):
            return
        try:
            # Clamp level to [0,1]
            try:
                level = float(level)
            except Exception:
                level = 0.0
            level = max(0.0, min(1.0, level))
            devices = AudioUtilities.GetSpeakers()
            # Explicitly ignore type checking for Activate (Pylance will hush)
            interface = devices.Activate( # type: ignore[attr-defined]
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = GetBestInterface(interface)
            volume.SetMasterVolumeLevelScalar(level, None) # type: ignore[attr-defined]
        except Exception:
            logging.exception("Failed to set volume")
    def set_brightness(self, level):
        if not self.has_permission('set_brightness'): return
        try:
            level = int(max(0, min(100, int(level))))
            sbc.set_brightness(level)
            self.speak(f"Adjusting brightness to {level} percent.")
        except Exception:
            logging.exception("Failed to set brightness")
            self.speak("Failed to set brightness")
    # ----------------------- Validation Helpers -----------------------
    def _validate_range(self, value, min_value, max_value):
        try:
            v = int(value)
            return min_value <= v <= max_value
        except Exception:
            return False
    def _validate_safe_path(self, path):
        try:
            p = os.path.abspath(path)
            # Must either exist or the parent exists; block Windows directory root deletions implicitly
            return os.path.exists(p) or os.path.isdir(os.path.dirname(p))
        except Exception:
            return False
    def _validate_shell_command(self, cmd):
        try:
            if not cmd or len(cmd) > 2048:
                return False
            deny = [
                "format ", "diskpart", "bcdedit", "cipher /w", "chkdsk",
                "del /q /s c:\\", "rd /s /q c:\\"
            ]
            cl = cmd.lower().strip()
            return not any(x in cl for x in deny)
        except Exception:
            return False
    # ----------------------- Info Utilities -----------------------
    def get_weather(self):
        if not self.has_permission('get_weather'): return
        try:
            # Simple no-key weather
            resp = requests.get("https://wttr.in/?format=j1", timeout=10)
            data = resp.json()
            area = data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", "your area")
            cur = data.get("current_condition", [{}])[0]
            temp_c = cur.get("temp_C")
            desc = (cur.get("weatherDesc", [{}])[0].get("value") or "").lower()
            self.speak(f"Weather in {area}: {desc}, {temp_c} degrees Celsius")
        except Exception:
            logging.exception("Failed to get weather")
            self.speak("Unable to fetch weather right now")
    def get_cpu_info(self):
        if not self.has_permission('get_cpu_info'): return
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            self.speak(f"CPU usage is {int(cpu)} percent. Memory used {int(mem.percent)} percent")
        except Exception:
            logging.exception("Failed to get CPU info")
    def create_note(self, note):
        if not self.has_permission('create_note'): return
        try:
            note = note or ""
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] {note}\n")
            self.speak("Note saved")
        except Exception:
            logging.exception("Failed to create note")
            self.speak("Failed to save note")
    def take_screenshot(self):
        if not self.has_permission('take_screenshot'): return
        try:
            filename = os.path.join(self.screenshots_folder, f"screenshot_{int(time.time())}.png")
            try:
                import pyautogui
                img = pyautogui.screenshot()
                img.save(filename)
            except Exception:
                img = ImageGrab.grab()
                img.save(filename)
            self.speak("Screenshot taken")
        except Exception:
            logging.exception("Failed to take screenshot")
            self.speak("Failed to take screenshot")
    def get_ip_address(self):
        if not self.has_permission('get_ip_address'): return
        try:
            ip = requests.get("https://api.ipify.org?format=text", timeout=5).text.strip()
            self.speak(f"Your public IP address is {ip}")
        except Exception:
            logging.exception("Failed to get IP address")
            self.speak("Unable to get IP address")
    def run_speed_test(self):
        if not self.has_permission('run_speed_test'): return
        try:
            self.speak("Running speed test")
            # Use subprocess to run speedtest-cli command
            result = subprocess.run(["speedtest-cli", "--simple"], capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                output = result.stdout.strip()
                lines = output.split('\n')
                down = up = 0
                for line in lines:
                    if line.startswith('Download:'):
                        down = float(line.split()[1])
                    elif line.startswith('Upload:'):
                        up = float(line.split()[1])
                self.speak(f"Download {int(down)} megabits per second. Upload {int(up)} megabits per second")
            else:
                logging.error(f"speedtest-cli failed: {result.stderr}")
                self.speak("Speed test failed")
        except subprocess.TimeoutExpired:
            self.speak("Speed test timed out")
        except FileNotFoundError:
            self.speak("speedtest-cli not found. Please install it with pip install speedtest-cli")
        except Exception:
            logging.exception("Failed to run speed test")
            self.speak("Speed test failed")
    # ----------------------- Phase 2: Printer Management -----------------------
    def list_printers(self):
        if not self.has_permission('list_printers'): return
        try:
            try:
                import win32print # type: ignore
            except Exception:
                self.speak("Printer features require Windows printer support on this system")
                return
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = win32print.EnumPrinters(flags)
            names = []
            for p in printers:
                # p structure varies by level; when not providing level, tuple index 1 often holds name
                try:
                    names.append(str(p[1]))
                except Exception:
                    pass
            names = list(dict.fromkeys([n for n in names if n]))
            if not names:
                self.speak("I could not find any printers configured")
                return
            # Announce up to first 5 printers
            preview = ", ".join(names[:5])
            if len(names) > 5:
                preview += f", and {len(names)-5} more"
            self.speak("Available printers: " + preview)
        except Exception:
            logging.exception("Failed to list printers")
            self.speak("Unable to list printers")
    def set_default_printer(self, printer_name: str):
        if not self.has_permission('set_default_printer'): return
        try:
            try:
                import win32print # type: ignore
            except Exception:
                self.speak("Setting the default printer requires Windows printer support")
                return
            target = (printer_name or '').strip()
            if not target:
                self.speak("Please specify a printer name to set as default")
                return
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = win32print.EnumPrinters(flags)
            names = []
            for p in printers:
                try:
                    names.append(str(p[1]))
                except Exception:
                    pass
            match = None
            tl = target.lower()
            for n in names:
                if n and tl == n.lower():
                    match = n
                    break
            if not match:
                # fuzzy startswith/contains
                starts = [n for n in names if n and n.lower().startswith(tl)]
                contains = [n for n in names if n and tl in n.lower()]
                match = (starts or contains or [None])[0]
            if not match:
                self.speak(f"I could not find a printer matching {printer_name}")
                return
            win32print.SetDefaultPrinter(match)
            self.speak(f"Default printer set to {match}")
        except Exception:
            logging.exception("Failed to set default printer")
            self.speak("Unable to set the default printer")
    def print_test_page(self):
        if not self.has_permission('print_test_page'): return
        try:
            try:
                import win32print # type: ignore
                import win32ui # type: ignore
            except Exception:
                self.speak("Printing a test page requires Windows printer support")
                return
            # Use default printer
            try:
                printer_name = win32print.GetDefaultPrinter()
            except Exception:
                printer_name = None
            if not printer_name:
                self.speak("No default printer is set")
                return
            # Create a very simple text test page
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(hPrinter, 1, ("SEBAS Test Page", "", "RAW"))
                win32print.StartPagePrinter(hPrinter)
                try:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    message = f"SEBAS Test Page\r\nPrinted at {now}\r\nIf you can read this, printing works.\r\n"
                    win32print.WritePrinter(hPrinter, message.encode('utf-8', errors='ignore'))
                finally:
                    win32print.EndPagePrinter(hPrinter)
                    win32print.EndDocPrinter(hPrinter)
                self.speak("Test page sent to the default printer")
            finally:
                try:
                    win32print.ClosePrinter(hPrinter)
                except Exception:
                    pass
        except Exception:
            logging.exception("Failed to print test page")
            self.speak("Unable to print the test page")
    # ----------------------- Phase 2: User Session Monitoring -----------------------
    def list_user_sessions(self):
        if not self.has_permission('list_user_sessions'): return
        try:
            users = []
            try:
                users = psutil.users()
            except Exception:
                users = []
            if users:
                # Aggregate unique (name, terminal)
                seen = []
                for u in users:
                    name = getattr(u, 'name', None) or ''
                    term = getattr(u, 'terminal', None) or ''
                    key = (name, term)
                    if key not in seen:
                        seen.append(key)
                if seen:
                    formatted = ", ".join([f"{n} on {t or 'console'}" for n, t in seen])
                    self.speak("Active user sessions: " + formatted)
                    return
            # Fallback using 'query user'
            try:
                result = subprocess.run(["query", "user"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout:
                    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
                    if len(lines) > 1:
                        entries = ", ".join([ln.split()[0] for ln in lines[1:] if ln.split()])
                        if entries:
                            self.speak("Active users: " + entries)
                            return
            except Exception:
                pass
            self.speak("I could not determine active user sessions")
        except Exception:
            logging.exception("Failed to list user sessions")
            self.speak("Unable to list user sessions")
# ----------------------- Main -----------------------
if __name__ == "__main__":
    # Admin elevation is now handled by the background service.
    assistant = Sebas()
    # Start UI server
    try:
        from sebas.api.ui_server import start_ui_server
        start_ui_server()
        try:
            _web.open("http://127.0.0.1:5000/", new=1)
        except Exception:
            pass
    except Exception:
        logging.exception("Failed to start UI server")
   
    # Start API server (Phase 1.3)
    try:
        from sebas.api.api_server import APIServer, create_api_server
        api_server = create_api_server(sebas_instance=assistant, host="127.0.0.1", port=5002)
        api_server.start()
        logging.info("SEBAS API server started on http://127.0.0.1:5002")
    except Exception:
        logging.exception("Failed to start API server")
   
    assistant.speak(assistant.butler_greeting())
    def on_wake_word(text=None):
        text = (text or "").lower()
        # If user said wake word + command in one utterance, execute immediately
        if text:
            if "sebas" in text and len(text.split()) > 1:
                # remove wake word token(s)
                cleaned = text.replace("sebas", "").strip(", .!?")
                if cleaned:
                    assistant.parse_and_execute(cleaned)
                    return
            # If clear command without wake word, still try to execute
            command_keywords = [
                "open", "close", "search for", "volume", "brightness", "shutdown", "restart",
                "lock", "sleep", "hibernate", "log off", "sign out", "weather", "cpu",
                "create a note", "screenshot", "ip address", "speed test", "list processes",
                "kill process", "create folder", "delete", "run command"
            ]
            if any(k in text for k in command_keywords):
                assistant.parse_and_execute(text)
                return
        # Otherwise, do two-step prompt then listen
        assistant.speak("How may I be of service, " + assistant.get_salutation() + "?")
        command = assistant.listen(timeout=10, phrase_time_limit=20)
        if command:
            assistant.parse_and_execute(command)
    wake_detector = WakeWordDetector(
        recognizer=assistant.recognizer,
        microphone_device_index=assistant.microphone_device_index,
        wake_word="sebas",
        callback=on_wake_word,
        audio_lock=assistant.audio_lock
    )
    wake_detector.start()
    shutdown_event = threading.Event()
    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received; shutting down...")
    except Exception:
        logging.exception("Fatal error in main loop")
    finally:
        try:
            wake_detector.stop(join=True)
        except Exception:
            logging.exception("Failed to stop wake detector")
        try:
            assistant.tts_engine.stop()
        except Exception:
            pass