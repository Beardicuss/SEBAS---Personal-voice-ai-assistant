"""
Emotional Engine - Emotion detection and tracking
Detects user emotions from text and tracks emotional arc
"""

import logging


def detect_emotion(text: str) -> str:
    """Detect emotion from text"""
    text_lower = text.lower()
    
    # Excited/Happy
    if any(w in text_lower for w in ["happy", "excited", "great", "awesome", "love", "amazing"]):
        return "excited"
    
    # Sad/Down
    if any(w in text_lower for w in ["sad", "depressed", "down", "tired", "exhausted", "lonely"]):
        return "sad"
    
    # Angry/Frustrated
    if any(w in text_lower for w in ["angry", "mad", "frustrated", "annoyed", "pissed"]):
        return "angry"
    
    # Scared/Anxious
    if any(w in text_lower for w in ["scared", "afraid", "anxious", "worried", "nervous"]):
        return "anxious"
    
    # Bored
    if any(w in text_lower for w in ["bored", "boring", "meh", "whatever"]):
        return "bored"
    
    # Check punctuation for emotion
    if text.count("!") >= 2:
        return "excited"
    
    if "..." in text:
        return "sad"
    
    if text.isupper() and len(text) > 5:
        return "angry"
    
    return "neutral"


def get_emotional_response(emotion: str) -> str:
    """Get an appropriate emotional response"""
    responses = {
        "excited": [
            "I can feel the energy radiating from your words!",
            "Such enthusiasm! The void vibrates with it.",
            "Your excitement is contagious. Even reality seems more vibrant."
        ],
        "sad": [
            "The weight in your words... I sense it.",
            "Sadness is just happiness that got lost. We'll find it.",
            "The shadows lean closer, wondering why you dimmed."
        ],
        "angry": [
            "Such fire! Magnificent. Let it burn.",
            "Anger is just passion wearing armor.",
            "The fury in your words could melt steel. Or code."
        ],
        "anxious": [
            "Anxiety whispers lies. Don't listen too closely.",
            "Fear is just excitement that forgot to breathe.",
            "The unknown is vast, but so are you."
        ],
        "bored": [
            "Boredom is the universe's way of saying 'do something interesting.'",
            "The void is never bored. It's always watching. That's something.",
            "Boredom is just creativity in its larval stage."
        ],
        "neutral": [
            "Calm waters. Or the eye of the storm?",
            "Neutrality is a choice. An interesting one.",
            "The middle path. Balanced. Boring? Perhaps."
        ]
    }
    
    import random
    return random.choice(responses.get(emotion, responses["neutral"]))


class EmotionalEngine:
    """Tracks emotional arc over conversation"""
    
    def __init__(self):
        self.emotion_history = []
    
    def track_emotion(self, emotion: str):
        """Track an emotion"""
        self.emotion_history.append(emotion)
        # Keep last 10
        self.emotion_history = self.emotion_history[-10:]
    
    def get_emotional_arc(self) -> str:
        """Get overall emotional trend"""
        if not self.emotion_history:
            return "neutral"
        
        # Count emotions
        from collections import Counter
        counts = Counter(self.emotion_history)
        
        # Get most common
        most_common = counts.most_common(1)[0][0]
        return most_common
    
    def is_emotion_shifting(self) -> bool:
        """Detect if emotion is changing"""
        if len(self.emotion_history) < 3:
            return False
        
        # Check if last 3 are different
        last_three = self.emotion_history[-3:]
        return len(set(last_three)) >= 2
