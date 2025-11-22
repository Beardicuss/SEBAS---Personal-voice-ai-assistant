"""
Bayesian Scorer - Probabilistic confidence scoring for intent prediction
Uses Beta distribution to model success rates
"""

import logging
from typing import Dict, Tuple


class BayesianScorer:
    """Bayesian confidence scoring for intent prediction"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        self.priors = self._load_priors()
        logging.info("[BayesianScorer] Initialized")
    
    def _load_priors(self) -> Dict:
        """Load Bayesian priors from memory"""
        priors = self.mem.get("bayesian_priors", {})
        if "intent_success_rate" not in priors:
            priors["intent_success_rate"] = {}
        if "pattern_accuracy" not in priors:
            priors["pattern_accuracy"] = {}
        if "total_interactions" not in priors:
            priors["total_interactions"] = 0
        return priors
    
    def update_prior(self, intent: str, success: bool):
        """Update Bayesian prior after interaction"""
        if intent not in self.priors["intent_success_rate"]:
            self.priors["intent_success_rate"][intent] = {
                "successes": 0,
                "failures": 0
            }
        
        if success:
            self.priors["intent_success_rate"][intent]["successes"] += 1
        else:
            self.priors["intent_success_rate"][intent]["failures"] += 1
        
        self.priors["total_interactions"] += 1
        self.mem.update("bayesian_priors", self.priors)
    
    def calculate_confidence(self, intent: str, base_confidence: float) -> float:
        """Calculate Bayesian-adjusted confidence"""
        if intent not in self.priors["intent_success_rate"]:
            return base_confidence
        
        stats = self.priors["intent_success_rate"][intent]
        total = stats["successes"] + stats["failures"]
        
        if total == 0:
            return base_confidence
        
        # Bayesian adjustment with Beta distribution
        # Prior: Beta(1, 1) (uniform)
        # Posterior: Beta(1 + successes, 1 + failures)
        alpha = 1 + stats["successes"]
        beta = 1 + stats["failures"]
        
        # Expected value of Beta distribution
        bayesian_prob = alpha / (alpha + beta)
        
        # Combine with base confidence (weighted average)
        # More weight to Bayesian as we get more data
        weight = min(total / 10.0, 1.0)
        adjusted = (1 - weight) * base_confidence + weight * bayesian_prob
        
        return adjusted
    
    def predict_failure_risk(self, intent: str) -> float:
        """Predict probability of failure"""
        if intent not in self.priors["intent_success_rate"]:
            return 0.5  # Unknown
        
        stats = self.priors["intent_success_rate"][intent]
        total = stats["successes"] + stats["failures"]
        
        if total == 0:
            return 0.5
        
        # Bayesian failure probability
        alpha = 1 + stats["failures"]
        beta = 1 + stats["successes"]
        
        return alpha / (alpha + beta)
    
    def get_intent_stats(self, intent: str) -> Tuple[int, int, float]:
        """Get success/failure counts and success rate"""
        if intent not in self.priors["intent_success_rate"]:
            return (0, 0, 0.5)
        
        stats = self.priors["intent_success_rate"][intent]
        total = stats["successes"] + stats["failures"]
        
        if total == 0:
            return (0, 0, 0.5)
        
        success_rate = stats["successes"] / total
        return (stats["successes"], stats["failures"], success_rate)
