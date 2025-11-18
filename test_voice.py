import logging
import time
from pathlib import Path

# Enable detailed logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Import your classes
from tts import tts_manager, piper_tts


# ---------------------------------------------------------
# Utility: Show status dict nicely
# ---------------------------------------------------------
def pretty_status(name, status_dict):
    print("\n" + "=" * 60)
    print(f" {name} STATUS")
    print("=" * 60)
    for k, v in status_dict.items():
        print(f"{k:<25} : {v}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------
# TEST 1 — Initialization test
# ---------------------------------------------------------
def test_initialization():
    print("\n===== TEST 1: Initialization =====")

    # Use default paths inside your project
    model = Path("voices/piper/en_US-john-medium.onnx")
    config = Path("voices/piper/en_US-john-medium.onnx.json")


    tts = piper_tts.PiperTTS(model_path=model, config_path=config)

    if tts.voice is None:
        print("❌ FAILED: Voice not loaded")
    else:
        print("✅ SUCCESS: Voice loaded")

    pretty_status("PiperTTS", tts.get_status())

    return tts


# ---------------------------------------------------------
# TEST 2 — Speak Test
# ---------------------------------------------------------
def test_speak(tts: piper_tts.PiperTTS):
    print("\n===== TEST 2: Speak() =====")

    if tts.voice is None:
        print("❌ Cannot run speak test — voice is None")
        return

    print("→ Speaking short text: 'Hello, this is a test.'")
    tts.speak("It is now 22 hours and 54 minutes ......")
    tts.wait_until_done(5)

    print("→ Speaking stream mode")
    tts.speak("It will soon be midnight ......", stream=True)
    tts.wait_until_done(5)

    print("→ Speaking stream mode")
    tts.speak("blyat", stream=True)
    tts.wait_until_done(5)

    pretty_status("After Speak", tts.get_status())


# ---------------------------------------------------------
# TEST 3 — Health Check
# ---------------------------------------------------------
def test_health(tts: piper_tts.PiperTTS):
    print("\n===== TEST 3: Health Check =====")

    health = tts.health_check()
    pretty_status("Health Check", health)


# ---------------------------------------------------------
# TEST 4 — TTSManager Tests
# ---------------------------------------------------------
# def test_tts_manager():
#     print("\n===== TEST 4: TTSManager =====")

#     manager = tts_manager.TTSManager(
#         piper_model_path="sebas/voices/piper/en_US-lessac-medium.onnx",
#         piper_config_path="sebas/voices/piper/en_US-lessac-medium.json"
#     )

#     if manager.engine is None or manager.engine.voice is None:
#         print("❌ TTSManager failed to initialize PiperTTS")
#         return

#     print("→ Calling manager.speak()...")
#     manager.speak("This text is spoken from TTSManager.")
#     time.sleep(3)
#     manager.stop()

#     print("→ Listing voices:")
#     voices = manager.list_voices()
#     print(voices)

#     print("→ Testing set_voice():")
#     manager.set_voice("english")


# ---------------------------------------------------------
# TEST 5 — Missing Model File
# ---------------------------------------------------------
def test_missing_model():
    print("\n===== TEST 5: Missing Model File =====")

    tts = piper_tts.PiperTTS(
        model_path="sebas/voices/piper/THIS_DOES_NOT_EXIST.onnx",
        config_path="sebas/voices/piper/THIS_DOES_NOT_EXIST.json"
    )

    if tts.voice is None:
        print("✅ Correct behavior: Voice is None when model is missing")
    else:
        print("❌ ERROR: Voice should not load when model is missing")


# ---------------------------------------------------------
# Run all tests
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n==============================")
    print("   PIPERTTS TEST SUITE")
    print("==============================\n")

    tts = test_initialization()
    test_speak(tts)
    test_health(tts)
    #test_tts_manager()
    test_missing_model()

    print("\n✔ ALL TESTS COMPLETED")
