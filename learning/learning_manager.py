"""
Learning Manager - Main orchestrator for the self-learning system
Coordinates all learning engines and integrates with NLU
"""

import logging
from typing import Dict, Any, List

from .memory_store import MemoryStore
from .correction_engine import CorrectionEngine
from .pattern_expander import PatternExpander
from .stats_tracker import StatsTracker
from .parameter_learner import ParameterLearner
from .bayesian_scorer import BayesianScorer
from .ngram_miner import NGramMiner
from .temporal_miner import TemporalMiner
from .dependency_graph import DependencyGraph
from .semantic_clusterer import SemanticClusterer
from .active_learner import ActiveLearner
from .forgetting_engine import ForgettingEngine
from .workflow_learner import WorkflowLearner
from .context_tracker import ContextTracker


class LearningManager:
    """Main orchestrator for self-learning system"""
    
    def __init__(self, nlu, prefs, memory_store: MemoryStore, assistant_ref):
        self.nlu = nlu
        self.prefs = prefs
        self.memory = memory_store
        self.assistant = assistant_ref
        
        logging.info("[LearningManager] Initializing self-learning system...")
        
        # Core engines
        self.correction_engine = CorrectionEngine(self.memory)
        self.pattern_expander = PatternExpander(self.memory)
        self.workflow_learner = WorkflowLearner(self.memory)
        self.stats = StatsTracker(self.memory)
        
        # Context and parameters
        self.context_tracker = ContextTracker(self.memory)
        self.parameter_learner = ParameterLearner(self.memory)
        
        # Advanced engines
        self.bayesian = BayesianScorer(self.memory)
        self.ngram_miner = NGramMiner(self.memory)
        self.temporal = TemporalMiner(self.memory)
        self.dependency_graph = DependencyGraph(self.memory)
        self.semantic_clusterer = SemanticClusterer(self.memory)
        self.active_learner = ActiveLearner(self.memory)
        self.forgetting_engine = ForgettingEngine(self.memory)
        
        # Auto-enhance NLU on startup
        self.enhance_nlu()
        
        logging.info("[LearningManager] ✓ Self-learning system initialized")
    
    def save_after_interaction(self, text: str, intent: str, slots: Dict[str, Any], 
                               success: bool, confidence: float):
        """Called after every command execution - MAXIMUM LEARNING"""
        # Basic stats
        self.stats.record_usage(intent, success, confidence, slots)
        
        # Bayesian update
        self.bayesian.update_prior(intent, success)
        
        # Auto-learn from high-confidence successes
        if success and confidence > 0.85:
            self.pattern_expander.auto_learn_pattern(text, intent)
            self.parameter_learner.learn_slots(intent, slots)
            self.ngram_miner.learn_from_text(text, intent)
            self.semantic_clusterer.update_clusters(text, intent)
        
        # Context tracking
        self.context_tracker.record_interaction(text, intent, slots)
        self.temporal.record_interaction(intent, slots)
        
        # Dependency graph
        self.dependency_graph.record_command(intent)
    
    def learn_correction(self, wrong_text: str, correct_intent: str):
        """User explicitly corrects SEBAS"""
        self.correction_engine.add_correction(wrong_text, correct_intent)
        self.semantic_clusterer.update_clusters(wrong_text, correct_intent)
        logging.info(f"[LearningManager] Learned correction: '{wrong_text}' → {correct_intent}")
    
    def learn_workflow(self, name: str, step_list: List[Dict], triggers: List[str] = None, 
                      context: Dict = None):
        """Learn multi-step routine"""
        self.workflow_learner.save_workflow(name, step_list, triggers, context)
    
    def enhance_nlu(self):
        """Inject all learned knowledge into NLU"""
        logging.info("[LearningManager] Enhancing NLU with learned patterns...")
        
        # Wrap NLU parse with all learning engines
        original_parse = self.nlu.parse
        
        def ultra_enhanced_parse(text, *args, **kwargs):
            # 1. Check corrections first (highest priority)
            correction = self.correction_engine.check_correction(text)
            if correction:
                try:
                    from sebas.services.nlu import Intent
                    return Intent(
                        name=correction["name"],
                        slots=correction["slots"],
                        confidence=correction["confidence"]
                    )
                except:
                    pass
            
            # 2. Try semantic clustering
            cluster = self.semantic_clusterer.find_cluster(text)
            if cluster:
                try:
                    from sebas.services.nlu import Intent
                    return Intent(
                        name=cluster["intent"],
                        slots={},
                        confidence=0.9
                    )
                except:
                    pass
            
            # 3. Try n-gram prediction
            ngram_intent, ngram_conf = self.ngram_miner.predict_intent_from_ngrams(text)
            if ngram_intent and ngram_conf > 0.7:
                try:
                    from sebas.services.nlu import Intent
                    return Intent(
                        name=ngram_intent,
                        slots={},
                        confidence=ngram_conf
                    )
                except:
                    pass
            
            # 4. Original NLU parse
            result = original_parse(text, *args, **kwargs)
            
            # 5. Bayesian confidence adjustment
            if result and hasattr(result, 'name') and hasattr(result, 'confidence'):
                adjusted_conf = self.bayesian.calculate_confidence(
                    result.name,
                    result.confidence
                )
                result.confidence = adjusted_conf
            
            return result
        
        # Replace NLU parse
        self.nlu.parse = ultra_enhanced_parse
        
        # Also inject patterns
        self.pattern_expander.inject_into_nlu(self.nlu)
        
        logging.info("[LearningManager] ✓ NLU enhanced with self-learning")
    
    def get_suggestions(self) -> List[str]:
        """Get smart suggestions based on context"""
        suggestions = []
        
        # Temporal suggestions
        temporal_intents = self.temporal.get_likely_intents(top_n=3)
        suggestions.extend(temporal_intents)
        
        # Dependency-based suggestions
        if self.dependency_graph.recent_commands:
            last_cmd = self.dependency_graph.recent_commands[-1]
            next_cmds = self.dependency_graph.get_likely_next_commands(last_cmd, top_n=2)
            suggestions.extend(next_cmds)
        
        # Predicted next command
        predicted = self.temporal.predict_next_command()
        if predicted:
            suggestions.append(predicted)
        
        # Deduplicate and return
        return list(dict.fromkeys(suggestions))[:5]
    
    def periodic_maintenance(self):
        """Run cleanup and optimization (call daily)"""
        logging.info("[LearningManager] Running periodic maintenance...")
        
        removed = self.forgetting_engine.decay_unused_patterns()
        self.semantic_clusterer.merge_similar_clusters()
        self.memory.save()
        
        logging.info(f"[LearningManager] ✓ Maintenance complete (removed {removed} patterns)")
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary of learning system stats"""
        return {
            "total_interactions": self.bayesian.priors.get("total_interactions", 0),
            "corrections_learned": len(self.memory.get("corrections", {})),
            "custom_patterns": len(self.memory.get("custom_patterns", {})),
            "workflows": len(self.memory.get("workflows", {})),
            "semantic_clusters": len(self.memory.get("semantic_clusters", {})),
            "most_used_intents": self.stats.get_most_used_intents(top_n=5)
        }
