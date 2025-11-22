# SEBAS Self-Learning System

This directory contains local ML models for the self-learning system.

## Required Models (Optional)

### Sentence Transformer (for semantic embeddings)
**Model:** `all-MiniLM-L6-v2`
**Size:** ~80MB
**Purpose:** Local semantic similarity without APIs

### Installation:
```bash
pip install sentence-transformers
```

The model will be automatically downloaded on first use to:
```
sebas/models/sentence_transformer/
```

### Manual Download (if needed):
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save('sebas/models/sentence_transformer')
```

## Fallback Mode
If sentence-transformers is not installed, the system will automatically fall back to:
- Simple string similarity (difflib)
- N-gram based matching
- Pattern-based learning

**The system works 100% offline with or without the models!**
