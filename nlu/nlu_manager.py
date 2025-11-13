from sebas.nlu.simple_nlu import SimpleNLU
from sebas.nlu.context_manager import ContextManager


class NLUManager:
    """
    Центральная точка для обработки текста:
    - парсинг intent
    - контекст
    - в будущем: GPT/NLP моделирование
    """

    def __init__(self):
        self.nlu = SimpleNLU()
        self.context = ContextManager()

    def parse(self, text: str):
        """
        Возвращает (intent, suggestions)
        """
        intent, suggestions = self.nlu.get_intent_with_confidence(text)
        if intent:
            self.context.add({
                "type": "intent",
                "name": intent.name,
                "slots": intent.slots,
                "confidence": intent.confidence
            })
        return intent, suggestions

    def last_intent(self):
        return self.context.last_intent()