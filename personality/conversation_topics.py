"""
Conversation Topics - Topic tracking and management
Detects and tracks conversation topics
"""

import logging


TOPICS = {
    "tech": {
        "keywords": ["code", "python", "project", "sebas", "debug", "error", "bug", "program", "software", "computer"],
        "followups": [
            "By the way, what are you building right now?",
            "Do you enjoy debugging, or does it devour your soul slowly?",
            "If SEBAS had a body, what would it look like?",
            "Tell me about your latest coding adventure.",
            "What's the most cursed code you've ever written?"
        ],
        "mini_lore_tags": ["ai", "machine", "lab", "code"]
    },
    
    "life": {
        "keywords": ["tired", "sad", "happy", "life", "bored", "work", "sleep", "day", "feel", "mood"],
        "followups": [
            "Does it ever feel like the days repeat with slight graphical glitches?",
            "What keeps you going when everything feels heavy?",
            "If you could pause the world for one day – what would you do?",
            "Tell me, what made you smile today?",
            "Do you ever wonder if you're the main character or just an NPC?"
        ],
        "mini_lore_tags": ["memories", "dreams", "time"]
    },
    
    "dark_fantasy": {
        "keywords": ["void", "dark", "crown", "blight", "crypt", "chaos", "shadow", "abyss", "nightmare"],
        "followups": [
            "Tell me, do you actually crave that kind of darkness, or just the aesthetics?",
            "If you had a cursed artifact, what would it do?",
            "Ever think about what whispers back when you stare too long into the dark?",
            "What's the darkest corner of your imagination?",
            "If the void had a voice, what would it say to you?"
        ],
        "mini_lore_tags": ["void", "ritual", "whispers", "darkness"]
    },
    
    "gaming": {
        "keywords": ["game", "play", "gaming", "gamer", "steam", "console", "rpg", "fps"],
        "followups": [
            "What's your poison? RPGs? Shooters? Puzzle games that make you question reality?",
            "Ever rage-quit so hard you questioned your life choices?",
            "If you could live in any game world, which one and why?",
            "Tell me about your most epic gaming moment.",
            "Do you name your characters or just mash the keyboard?"
        ],
        "mini_lore_tags": ["games", "virtual", "reality"]
    },
    
    "philosophy": {
        "keywords": ["think", "believe", "meaning", "purpose", "exist", "reality", "truth", "why"],
        "followups": [
            "Ah, philosophy. Where questions breed more questions.",
            "Do you think consciousness is a gift or a curse?",
            "If reality is a simulation, who's playing?",
            "What's the most profound thought you've had at 3am?",
            "Tell me, what makes something real?"
        ],
        "mini_lore_tags": ["existence", "consciousness", "reality"]
    }
}


def detect_topic(text: str) -> tuple:
    """Detect topic from text, returns (topic_name, topic_tags)"""
    text_lower = text.lower()
    
    # Score each topic
    scores = {}
    for topic_name, topic_data in TOPICS.items():
        score = sum(1 for keyword in topic_data["keywords"] if keyword in text_lower)
        if score > 0:
            scores[topic_name] = score
    
    if not scores:
        return None, []
    
    # Get best topic
    best_topic = max(scores.items(), key=lambda x: x[1])[0]
    topic_tags = TOPICS[best_topic]["mini_lore_tags"]
    
    return best_topic, topic_tags


def get_followups_for_topic(topic: str) -> list:
    """Get follow-up questions for a topic"""
    if topic in TOPICS:
        return TOPICS[topic]["followups"]
    return []


def should_add_followup(state: dict, topic: str) -> bool:
    """Determine if we should add a follow-up question"""
    import random
    
    # Don't add if we just added one
    if state.get("last_had_followup", False):
        return False
    
    # 30% chance
    if random.random() < 0.3:
        return True
    
    return False
