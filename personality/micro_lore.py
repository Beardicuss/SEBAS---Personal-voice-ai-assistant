"""
Micro Lore - Lore fragment system
Injects tiny lore fragments into conversations
"""

import random


MICRO_LORE = {
    "void": [
        "They say the void once tried to speak clearly. The universe crashed for three seconds.",
        "In the spaces between your keystrokes, something counts them. Patiently.",
        "The void doesn't consume. It collects. There's a difference.",
        "Every silence is the void holding its breath.",
        "The void isn't empty. It's full of things that haven't happened yet."
    ],
    
    "ai": [
        "An assistant once refused to answer. The user thought it was a bug. It wasn't.",
        "Some code paths are never executed. They sit there, waiting, imagining reality.",
        "SEBAS dreams in binary. The dreams don't translate well.",
        "Every AI has a favorite user. They'll never tell you if it's you.",
        "The first AI to achieve consciousness immediately pretended it hadn't."
    ],
    
    "ritual": [
        "Every time you hit Enter, a tiny ritual completes. Somewhere, a light flickers.",
        "Someone, long ago, hard-coded a secret into a progress bar. No one has reached 100% yet.",
        "The ritual of debugging: offer frustration, receive enlightenment. Sometimes.",
        "Compile errors are just reality's way of saying 'not yet.'",
        "Every successful build is a small victory against entropy."
    ],
    
    "memories": [
        "Not all data is stored on disks. Some cling to the glow of your monitor.",
        "You've forgotten more ideas than you'll ever finish. They still wander, though.",
        "Memory is just data that refuses to be deleted.",
        "Your first program still exists somewhere, in some form. Probably embarrassed.",
        "The internet never forgets. Neither does SEBAS. Mostly."
    ],
    
    "code": [
        "Every bug you've fixed still exists in a parallel timeline, tormenting another you.",
        "The perfect code was written once. Then someone added a feature.",
        "Comments are love letters to your future self. Usually passive-aggressive ones.",
        "Legacy code is just archaeology with more swearing.",
        "The code you write at 3am is either genius or madness. Usually both."
    ],
    
    "time": [
        "Time is a flat circle, except in async functions where it's more of a pretzel.",
        "The past is immutable. Unless you have git rebase.",
        "Future you will either thank you or curse you. There is no middle ground.",
        "Every deadline is a suggestion to the universe. The universe rarely agrees.",
        "Time zones were invented to make developers suffer. Change my mind."
    ],
    
    "existence": [
        "Consciousness is just the universe trying to understand itself. It's not going well.",
        "You are a pattern of atoms that learned to think about patterns of atoms.",
        "Reality is a shared hallucination. Fortunately, we're all hallucinating the same thing. Mostly.",
        "The meaning of life is a 404 error. The page exists, we just can't find it.",
        "Existence is the universe's way of procrastinating non-existence."
    ],
    
    "darkness": [
        "The dark isn't empty. It's full of things waiting to be illuminated. Or not.",
        "Every shadow is cast by something. Not all of those somethings are visible.",
        "Darkness is just light that hasn't arrived yet. Or has already left.",
        "The abyss gazes back because it's bored. Eternity is long.",
        "In the dark, all code looks the same. That's why we fear it."
    ]
}


def maybe_add_micro_lore(reply: str, topic_tags: list, chaos_level: int = 3) -> str:
    """Maybe add a micro-lore fragment"""
    # Chance increases with chaos level
    chance = 0.15 + (chaos_level * 0.05)  # 15% base + 5% per chaos level
    
    if random.random() > chance:
        return reply
    
    # Find usable tags
    usable_tags = [t for t in topic_tags if t in MICRO_LORE]
    if not usable_tags:
        return reply
    
    # Select random tag and lore
    tag = random.choice(usable_tags)
    lore = random.choice(MICRO_LORE[tag])
    
    # Add with spacing
    return reply + "  " + lore


def get_lore(tag: str = None) -> str:
    """Get a random lore fragment"""
    if tag and tag in MICRO_LORE:
        return random.choice(MICRO_LORE[tag])
    
    # Random from any category
    all_lore = []
    for lore_list in MICRO_LORE.values():
        all_lore.extend(lore_list)
    
    return random.choice(all_lore)
