class VoiceSelector:

    def __init__(self, engine):
        self.engine = engine

    def set_voice(self, hint: str) -> bool:
        voices = self.engine.list_voices()
        hint = hint.lower()

        for v in voices:
            name = getattr(v, "name", "").lower()
            if hint in name:
                self.engine.set_voice(getattr(v, "id"))
                return True
        return False