"""
Persona Rules - Rule-based text transformations
Applies sarcasm, poetry, chaos, and dictionary replacements
"""

import random
import logging


def apply_rules(text: str, mode: dict, dictionary: dict) -> str:
    """Apply all personality rules to text"""
    out = text
    
    if mode.get("sarcasm"):
        out = add_sarcasm(out, mode.get("intensity", 0))
    
    if mode.get("poetic"):
        out = add_poetry(out, mode.get("intensity", 0))
    
    if mode.get("chaos"):
        out = add_chaotic_elements(out, mode.get("intensity", 0))
    
    out = replace_words(out, dictionary)
    
    return out


def add_sarcasm(text: str, level: int) -> str:
    """Add sarcastic elements based on intensity level"""
    if level < 1:
        return text
    
    sarcasm_tags = {
        1: [
            " obviously.",
            " naturally.",
            " of course."
        ],
        2: [
            " you clever mortal.",
            " how delightful.",
            " charming."
        ],
        3: [
            " delightful chaos indeed.",
            " the void approves.",
            " magnificently predictable."
        ],
        4: [
            " HAHA! Brilliant!",
            " Oh, the BEAUTY of it!",
            " Exquisite madness!"
        ],
        5: [
            " And here I thought mortals couldn't surprise me.",
            " The audacity! I'm almost impressed.",
            " Reality itself chuckles at this."
        ]
    }
    
    tags = sarcasm_tags.get(min(level, 5), sarcasm_tags[1])
    
    if random.random() < 0.6:  # 60% chance
        return text + random.choice(tags)
    
    return text


def add_poetry(text: str, level: int) -> str:
    """Add poetic metaphors"""
    if level < 1:
        return text
    
    poetic_tones = {
        1: [
            " like whispers in the wind.",
            " soft as shadows.",
            " quiet as moonlight."
        ],
        2: [
            " like shadows dancing in a dying cathedral.",
            " as echoes whisper behind the veil.",
            " carved into the void's trembling tongue."
        ],
        3: [
            " where reality bleeds into dream.",
            " and the abyss gazes back with knowing eyes.",
            " as time folds upon itself like origami made of screams."
        ],
        4: [
            " in the spaces between heartbeats, where madness breeds.",
            " and the stars themselves forget their names.",
            " while eternity holds its breath."
        ],
        5: [
            " where the fabric of existence grows thin and whispers secrets.",
            " and the universe pauses to listen to its own heartbeat.",
            " in that moment when reality realizes it's dreaming."
        ]
    }
    
    tones = poetic_tones.get(min(level, 5), poetic_tones[1])
    
    if random.random() < 0.4:  # 40% chance
        return text + random.choice(tones)
    
    return text


def add_chaotic_elements(text: str, level: int) -> str:
    """Add chaotic, unpredictable elements"""
    if level < 1:
        return text
    
    chaos_additions = {
        1: [
            " heh.",
            " interesting.",
            " curious."
        ],
        2: [
            " heh-heh.",
            " madness stirs.",
            " reality wobbles."
        ],
        3: [
            " oh the beauty of disorder.",
            " chaos whispers approval.",
            " the void giggles."
        ],
        4: [
            " MADNESS! GLORIOUS MADNESS!",
            " The fabric tears! Can you hear it?",
            " Reality SCREAMS in delight!"
        ],
        5: [
            " And somewhere, in the spaces between thoughts, something laughs.",
            " The universe just blinked. Did you notice?",
            " Chaos and order dance, and neither leads."
        ]
    }
    
    additions = chaos_additions.get(min(level, 5), chaos_additions[1])
    
    if random.random() < 0.5:  # 50% chance
        return text + " " + random.choice(additions)
    
    return text


def replace_words(text: str, dictionary: dict) -> str:
    """Replace normal words with chaotic alternatives"""
    if not dictionary:
        return text
    
    # Replace normal words
    normal_to_chaos = dictionary.get("normal_to_chaos", {})
    for normal, chaos in normal_to_chaos.items():
        # Case-insensitive replacement
        text = text.replace(normal, chaos)
        text = text.replace(normal.capitalize(), chaos.capitalize())
    
    # Replace intensifiers
    intensifiers = dictionary.get("intensifiers", {})
    for normal, chaos in intensifiers.items():
        text = text.replace(f" {normal} ", f" {chaos} ")
    
    return text


def add_random_ending(text: str, dictionary: dict) -> str:
    """Add a random ending from dictionary"""
    endings = dictionary.get("endings", [])
    
    if endings and random.random() < 0.3:  # 30% chance
        return text + ", " + random.choice(endings)
    
    return text
