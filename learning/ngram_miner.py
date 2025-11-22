"""
N-Gram Miner - Discover common phrase patterns automatically
Extracts unigrams, bigrams, and trigrams to predict intents
"""

import logging
import re
from collections import defaultdict
from typing import List, Tuple, Optional


class NGramMiner:
    """Discover common phrase patterns automatically"""
    
    def __init__(self, memory_store, min_frequency: int = 3):
        self.mem = memory_store
        self.min_frequency = min_frequency
        self.patterns = self._load_patterns()
        logging.info("[NGramMiner] Initialized")
    
    def _load_patterns(self) -> dict:
        """Load discovered n-gram patterns"""
        patterns = self.mem.get("ngram_patterns", {})
        if "unigrams" not in patterns:
            patterns["unigrams"] = {}
        if "bigrams" not in patterns:
            patterns["bigrams"] = {}
        if "trigrams" not in patterns:
            patterns["trigrams"] = {}
        if "intent_ngrams" not in patterns:
            patterns["intent_ngrams"] = {}
        return patterns
    
    def extract_ngrams(self, text: str, n: int = 3) -> List[str]:
        """Extract n-grams from text"""
        words = re.findall(r'\w+', text.lower())
        ngrams = []
        
        for i in range(len(words) - n + 1):
            ngrams.append(' '.join(words[i:i+n]))
        
        return ngrams
    
    def learn_from_text(self, text: str, intent: str):
        """Extract and store n-grams"""
        # Unigrams
        words = re.findall(r'\w+', text.lower())
        for word in words:
            if word not in self.patterns["unigrams"]:
                self.patterns["unigrams"][word] = {"count": 0, "intents": {}}
            self.patterns["unigrams"][word]["count"] += 1
            self.patterns["unigrams"][word]["intents"][intent] = \
                self.patterns["unigrams"][word]["intents"].get(intent, 0) + 1
        
        # Bigrams
        bigrams = self.extract_ngrams(text, 2)
        for bg in bigrams:
            if bg not in self.patterns["bigrams"]:
                self.patterns["bigrams"][bg] = {"count": 0, "intents": {}}
            self.patterns["bigrams"][bg]["count"] += 1
            self.patterns["bigrams"][bg]["intents"][intent] = \
                self.patterns["bigrams"][bg]["intents"].get(intent, 0) + 1
        
        # Trigrams
        trigrams = self.extract_ngrams(text, 3)
        for tg in trigrams:
            if tg not in self.patterns["trigrams"]:
                self.patterns["trigrams"][tg] = {"count": 0, "intents": {}}
            self.patterns["trigrams"][tg]["count"] += 1
            self.patterns["trigrams"][tg]["intents"][intent] = \
                self.patterns["trigrams"][tg]["intents"].get(intent, 0) + 1
        
        self.mem.update("ngram_patterns", self.patterns)
    
    def predict_intent_from_ngrams(self, text: str) -> Tuple[Optional[str], float]:
        """Predict intent based on n-gram patterns"""
        intent_scores = defaultdict(float)
        
        # Check trigrams (most specific)
        trigrams = self.extract_ngrams(text, 3)
        for tg in trigrams:
            if tg in self.patterns["trigrams"]:
                data = self.patterns["trigrams"][tg]
                if data["count"] >= self.min_frequency:
                    for intent, count in data["intents"].items():
                        intent_scores[intent] += count * 3  # Weight trigrams higher
        
        # Check bigrams
        bigrams = self.extract_ngrams(text, 2)
        for bg in bigrams:
            if bg in self.patterns["bigrams"]:
                data = self.patterns["bigrams"][bg]
                if data["count"] >= self.min_frequency:
                    for intent, count in data["intents"].items():
                        intent_scores[intent] += count * 2
        
        # Check unigrams
        words = re.findall(r'\w+', text.lower())
        for word in words:
            if word in self.patterns["unigrams"]:
                data = self.patterns["unigrams"][word]
                if data["count"] >= self.min_frequency:
                    for intent, count in data["intents"].items():
                        intent_scores[intent] += count
        
        if not intent_scores:
            return None, 0.0
        
        # Get best intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        total_score = sum(intent_scores.values())
        confidence = best_intent[1] / total_score if total_score > 0 else 0
        
        return best_intent[0], confidence
