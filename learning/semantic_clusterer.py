"""
Semantic Clusterer - Group similar phrases without external APIs
Uses simple similarity matching to cluster related phrases
"""

import logging
import hashlib
from difflib import SequenceMatcher
from typing import Dict, List


class SemanticClusterer:
    """Groups similar phrases without external APIs"""
    
    def __init__(self, memory_store, similarity_threshold: float = 0.75):
        self.mem = memory_store
        self.threshold = similarity_threshold
        logging.info("[SemanticClusterer] Initialized")
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def update_clusters(self, text: str, intent: str):
        """Add text to appropriate cluster or create new one"""
        clusters = self.mem.get("semantic_clusters", {})
        text_lower = text.lower()
        
        # Find matching cluster
        best_cluster = None
        best_score = 0
        
        for cluster_id, cluster_data in clusters.items():
            if cluster_data["intent"] != intent:
                continue
            
            # Check similarity with anchor
            score = self._similarity(text_lower, cluster_data["anchor"])
            if score > best_score and score >= self.threshold:
                best_score = score
                best_cluster = cluster_id
        
        if best_cluster:
            # Add to existing cluster
            if text_lower not in clusters[best_cluster]["members"]:
                clusters[best_cluster]["members"].append(text_lower)
        else:
            # Create new cluster
            cluster_id = hashlib.md5(text_lower.encode()).hexdigest()[:8]
            clusters[cluster_id] = {
                "anchor": text_lower,
                "members": [text_lower],
                "intent": intent
            }
        
        self.mem.update("semantic_clusters", clusters)
    
    def find_cluster(self, text: str) -> Dict:
        """Find cluster for given text"""
        clusters = self.mem.get("semantic_clusters", {})
        text_lower = text.lower()
        
        best_cluster = None
        best_score = 0
        
        for cluster_data in clusters.values():
            for member in cluster_data["members"]:
                score = self._similarity(text_lower, member)
                if score > best_score and score >= self.threshold:
                    best_score = score
                    best_cluster = cluster_data
        
        return best_cluster if best_cluster else {}
    
    def inject_into_nlu(self, nlu):
        """Add cluster-based matching to NLU"""
        clusters = self.mem.get("semantic_clusters", {})
        
        original_parse = nlu.parse
        
        def cluster_aware_parse(text, *args, **kwargs):
            cluster = self.find_cluster(text)
            
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
            
            return original_parse(text, *args, **kwargs)
        
        nlu.parse = cluster_aware_parse
        logging.info(f"[SemanticClusterer] Injected {len(clusters)} clusters into NLU")
    
    def merge_similar_clusters(self):
        """Cleanup: merge clusters that are too similar"""
        clusters = self.mem.get("semantic_clusters", {})
        
        to_merge = []
        cluster_ids = list(clusters.keys())
        
        for i, id1 in enumerate(cluster_ids):
            for id2 in cluster_ids[i+1:]:
                if clusters[id1]["intent"] != clusters[id2]["intent"]:
                    continue
                
                sim = self._similarity(
                    clusters[id1]["anchor"],
                    clusters[id2]["anchor"]
                )
                
                if sim >= 0.85:  # Very similar
                    to_merge.append((id1, id2))
        
        # Merge clusters
        for id1, id2 in to_merge:
            if id2 in clusters:
                clusters[id1]["members"].extend(clusters[id2]["members"])
                clusters[id1]["members"] = list(set(clusters[id1]["members"]))
                del clusters[id2]
        
        self.mem.update("semantic_clusters", clusters)
