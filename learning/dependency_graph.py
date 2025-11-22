"""
Dependency Graph - Learn command relationships and sequences
Builds Markov chains of command sequences
"""

import logging
from typing import List, Dict
from collections import defaultdict


class DependencyGraph:
    """Learn command relationships and sequences"""
    
    def __init__(self, memory_store):
        self.mem = memory_store
        self.graph = self._load_graph()
        self.recent_commands = []
        logging.info("[DependencyGraph] Initialized")
    
    def _load_graph(self) -> dict:
        """Load dependency graph"""
        graph = self.mem.get("dependency_graph", {})
        if "edges" not in graph:
            graph["edges"] = {}
        if "chains" not in graph:
            graph["chains"] = []
        return graph
    
    def record_command(self, intent: str):
        """Record command and update graph"""
        # Add to recent commands
        self.recent_commands.append(intent)
        self.recent_commands = self.recent_commands[-5:]  # Keep last 5
        
        # Update edges
        if len(self.recent_commands) >= 2:
            prev_intent = self.recent_commands[-2]
            curr_intent = self.recent_commands[-1]
            
            if prev_intent not in self.graph["edges"]:
                self.graph["edges"][prev_intent] = {}
            
            self.graph["edges"][prev_intent][curr_intent] = \
                self.graph["edges"][prev_intent].get(curr_intent, 0) + 1
        
        # Detect chains (sequences of 3+)
        if len(self.recent_commands) >= 3:
            chain = tuple(self.recent_commands[-3:])
            chain_str = " -> ".join(chain)
            
            # Check if this chain exists
            existing_chain = None
            for c in self.graph["chains"]:
                if c["sequence"] == chain_str:
                    existing_chain = c
                    break
            
            if existing_chain:
                existing_chain["count"] += 1
            else:
                self.graph["chains"].append({
                    "sequence": chain_str,
                    "count": 1
                })
        
        self.mem.update("dependency_graph", self.graph)
    
    def get_likely_next_commands(self, current_intent: str, top_n: int = 3) -> List[str]:
        """Predict likely next commands"""
        if current_intent not in self.graph["edges"]:
            return []
        
        edges = self.graph["edges"][current_intent]
        sorted_edges = sorted(edges.items(), key=lambda x: x[1], reverse=True)
        
        return [intent for intent, count in sorted_edges[:top_n]]
    
    def get_common_chains(self, min_count: int = 3) -> List[Dict]:
        """Get frequently used command chains"""
        return [
            c for c in self.graph["chains"]
            if c["count"] >= min_count
        ]
