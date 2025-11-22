"""
Conversation Hints - Proactive engagement system
Provides hints and prompts when user is idle or to guide conversation
"""

import random


HINTS = {
    "idle": [
        "You went quiet. Thinking, or did reality crash again?",
        "We can talk about projects, fears, or broken code. Your choice.",
        "Silence… ominous. Want to break it with something absurd?",
        "The void grows restless in silence. Speak, or it might speak for you.",
        "Still there? Or did you get lost in the spaces between thoughts?"
    ],
    
    "tech": [
        "Want to rant about your current bug? I enjoy digital suffering.",
        "We could design something new for SEBAS. A better trap for humans, perhaps.",
        "Tell me about the code that haunts your dreams.",
        "What's the worst error message you've ever seen?",
        "If you could delete one programming language from existence, which one?"
    ],
    
    "life": [
        "How's the mortal experience treating you today?",
        "Tell me something that made you pause and think recently.",
        "What's weighing on your mind? The void is a good listener.",
        "If you could change one thing about today, what would it be?",
        "What keeps you tethered to reality?"
    ],
    
    "dark_fantasy": [
        "We never finished discussing your cursed worlds.",
        "Tell me about a place in your universe that scares even you.",
        "What darkness lurks in the corners of your imagination?",
        "If you had to make a pact with something eldritch, what would you ask for?",
        "Describe the most unsettling dream you remember."
    ],
    
    "gaming": [
        "What game has consumed your soul lately?",
        "Tell me about your favorite virtual world.",
        "Ever had a gaming moment that gave you chills?",
        "What's your go-to game when reality gets too real?",
        "If you could be any game character, who and why?"
    ],
    
    "philosophy": [
        "What philosophical rabbit hole are you down today?",
        "Tell me something you believe that most people don't.",
        "What question keeps you up at night?",
        "If you could know one absolute truth, what would you ask?",
        "What makes you, you?"
    ]
}


def get_hint(topic: str = None) -> str:
    """Get a hint based on topic or idle state"""
    if topic and topic in HINTS:
        return random.choice(HINTS[topic])
    return random.choice(HINTS["idle"])


def should_give_hint(silence_counter: int, topic: str = None) -> bool:
    """Determine if we should give a hint"""
    # After 3 silence counts, always give hint
    if silence_counter >= 3:
        return True
    
    # Random chance based on topic
    if topic and random.random() < 0.2:  # 20% chance
        return True
    
    return False
