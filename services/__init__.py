"""
SEBAS Services Module
"""

# Import from simple_nlu (note the dot for relative import)
try:
    from .simple_nlu import SimpleNLU, IntentBase, IntentWithConfidence, ContextManager
    HAS_SIMPLE_NLU = True
except ImportError as e:
    print(f"[Services] SimpleNLU not available: {e}")
    SimpleNLU = IntentBase = IntentWithConfidence = ContextManager = None
    HAS_SIMPLE_NLU = False

# Import from enhanced_nlu
try:
    from .enhanced_nlu import EnhancedNLU, EnhancedIntent
    HAS_ENHANCED_NLU = True
except ImportError as e:
    print(f"[Services] EnhancedNLU not available: {e}")
    EnhancedNLU = EnhancedIntent = None
    HAS_ENHANCED_NLU = False

__all__ = [
    'SimpleNLU',
    'IntentBase',
    'IntentWithConfidence',
    'ContextManager',
    'EnhancedNLU',
    'EnhancedIntent',
    'HAS_SIMPLE_NLU',
    'HAS_ENHANCED_NLU'
]