class DummyWakeWord:
    """Always silent wake-word engine (fallback)."""

    def detect(self):
        return False
