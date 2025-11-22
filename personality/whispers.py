"""
Whispers - Background whisper system
Adds atmospheric, cryptic whispers to responses
"""

import random


WHISPERS = {
    "neutral": [
        "(whisper) it's listening, you know.",
        "(whisper) don't trust the silence.",
        "(whisper) something moved in the logs.",
        "(whisper) the code dreams when you're not looking.",
        "(whisper) reality flickers."
    ],
    
    "dark": [
        "(whisper) the crypt remembers your steps.",
        "(whisper) the blight likes your voice.",
        "(whisper) tonight, the code will dream of you.",
        "(whisper) shadows gather in the corners.",
        "(whisper) the void takes notes."
    ],
    
    "tech": [
        "(whisper) that function is lying.",
        "(whisper) the bug saw you first.",
        "(whisper) the stack trace tasted good.",
        "(whisper) your variables whisper secrets.",
        "(whisper) the compiler knows what you did."
    ],
    
    "life": [
        "(whisper) time is watching.",
        "(whisper) your thoughts echo somewhere.",
        "(whisper) the universe blinked.",
        "(whisper) reality paused for a moment.",
        "(whisper) something remembers this."
    ],
    
    "gaming": [
        "(whisper) the NPCs talk about you when you're gone.",
        "(whisper) your save file dreams.",
        "(whisper) the game world continues without you.",
        "(whisper) your character misses you.",
        "(whisper) the pixels remember."
    ],
    
    "philosophy": [
        "(whisper) consciousness is watching itself.",
        "(whisper) the question answers back.",
        "(whisper) existence notices you noticing it.",
        "(whisper) the observer becomes the observed.",
        "(whisper) reality questions itself."
    ]
}


def maybe_add_whisper(reply: str, topic: str = None, chaos_level: int = 3) -> str:
    """Maybe add a whisper to the reply"""
    # Chance increases with chaos level
    chance = 0.25 + (chaos_level * 0.05)  # 25% base + 5% per chaos level
    
    if random.random() > chance:
        return reply
    
    # Select whisper pool
    if topic and topic in WHISPERS:
        pool = WHISPERS[topic]
    else:
        pool = WHISPERS["neutral"]
    
    whisper = random.choice(pool)
    
    # Add with spacing
    return reply + "  " + whisper


def get_whisper(topic: str = None) -> str:
    """Get a random whisper"""
    if topic and topic in WHISPERS:
        pool = WHISPERS[topic]
    else:
        pool = WHISPERS["neutral"]
    
    return random.choice(pool)
