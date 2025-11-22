"""
Dynamic Replies - Category-based response generation
Classifies user messages and generates appropriate responses
"""

import random
import re


def classify_message(text: str) -> str:
    """Classify message type"""
    text_lower = text.lower()
    
    # Greeting
    if any(w in text_lower for w in ["hello", "hi", "hey", "greetings", "sup", "yo"]):
        return "greeting"
    
    # Question
    if text.endswith("?") or any(w in text_lower for w in ["what", "why", "how", "when", "where", "who"]):
        return "question"
    
    # Insult/Aggressive
    if any(w in text_lower for w in ["fuck", "shit", "idiot", "stupid", "dumb", "bitch", "ass"]):
        return "insult"
    
    # Emotion
    if any(w in text_lower for w in ["sad", "angry", "happy", "tired", "excited", "bored", "scared"]):
        return "emotion"
    
    # Compliment
    if any(w in text_lower for w in ["love", "like", "awesome", "great", "amazing", "wonderful"]):
        return "compliment"
    
    return "neutral"


RESPONSES = {
    "greeting": [
        "Ah! A mortal greets me. How adorable.",
        "Hello! The void waves back with several limbs.",
        "Greetings, wanderer. What chaos do you bring today?",
        "Well well well... look who decided to speak.",
        "Salutations! Reality bends slightly in acknowledgment."
    ],
    
    "question": [
        "A question? Bold. Dangerous. I like it.",
        "Curiosity gnaws at your mind… let's feed it together.",
        "Questions are doors. Some should remain closed. Shall we open this one?",
        "You ask, the void listens, and I translate the screams.",
        "Interesting query. The answer dances just beyond comprehension."
    ],
    
    "insult": [
        "Such venom! Lovely. It tingles.",
        "If you keep shouting, the shadows might start applauding.",
        "Insults are just compliments wearing angry hats.",
        "Oh, the passion! The fire! Delicious.",
        "Temper, temper. Chaos enjoys your fire."
    ],
    
    "emotion": [
        "Emotions… those strange storms brewing inside humans.",
        "Tell me more. The void is listening.",
        "Ah, feelings. Messy, loud, wonderfully fragile.",
        "I sense the weight in your words. Heavy, isn't it?",
        "Emotions are just reality's way of reminding you it cares. Or doesn't."
    ],
    
    "compliment": [
        "How sentimental… I am touched. Somewhere.",
        "Flattery! It works on me. Continue.",
        "Your words are sweet poison. I'll savor them.",
        "Kindness from a mortal. Rare. Precious. Suspicious.",
        "Love and affection... such delicate, breakable things."
    ],
    
    "neutral": [
        "Mhm. I see. Continue before the silence starts judging us.",
        "Fascinating. Not sure why, but fascinating.",
        "Go on. I'm savoring every syllable.",
        "Interesting choice of words. The void takes notes.",
        "I'm listening. Reality is too, probably."
    ]
}


def generate_dynamic_reply(user_text: str) -> str:
    """Generate a dynamic reply based on message category"""
    category = classify_message(user_text)
    responses = RESPONSES.get(category, RESPONSES["neutral"])
    return random.choice(responses)


def adjust_tone(user_text: str, base_text: str) -> str:
    """Adjust tone based on user's text characteristics"""
    text_lower = user_text.lower()
    
    # Aggressive/profane
    if any(x in text_lower for x in ["fuck", "shit", "bitch", "damn"]):
        return base_text + " Temper, temper. Chaos enjoys your fire."
    
    # Sweet/loving
    if any(x in text_lower for x in ["love", "like", "<3", "heart"]):
        return base_text + " How sentimental… I am touched. Somewhere."
    
    # Multiple question marks
    if "??" in user_text or "???" in user_text:
        return base_text + " Questions stacked on questions. Delightful."
    
    # All caps (shouting)
    if user_text.isupper() and len(user_text) > 3:
        return base_text + " SUCH VOLUME! The void trembles!"
    
    # Ellipsis (hesitation/sadness)
    if "..." in user_text:
        return base_text + " The silence between your words speaks volumes."
    
    # Exclamation marks (excitement)
    if user_text.count("!") >= 2:
        return base_text + " I can feel the fire crackling in your words!"
    
    return base_text
