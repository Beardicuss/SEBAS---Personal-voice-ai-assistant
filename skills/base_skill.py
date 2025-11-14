class BaseSkill:
    """
    Base class for all SEBAS skills.

    Each skill may define:
        - intents: list[str]
        - events: list[str]  (optional)

    If 'events' is defined, SkillRegistry will subscribe them automatically.
    """

    intents = []  # override in subclasses
    events = []   # optional: ["core.started", "core.after_speak", ...]

    def can_handle(self, intent_name: str) -> bool:
        return intent_name in self.intents

    def handle(self, intent_name: str, slots: dict, sebas):
        raise NotImplementedError("handle() must be implemented by subclasses")

    # For event subscriptions:
    def on_event(self, event_name: str, data):
        """Override in skill if you want to handle events."""
        pass