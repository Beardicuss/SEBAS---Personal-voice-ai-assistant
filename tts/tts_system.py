import pyttsx3

class SystemTTS:
    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()

    def list_voices(self):
        return self.engine.getProperty("voices")

    def set_voice(self, voice_id):
        self.engine.setProperty("voice", voice_id)