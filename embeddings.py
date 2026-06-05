"""
embeddings.py
─────────────
Embedding wrapper built on fastembed (ONNX) instead of
sentence-transformers (PyTorch).

Why: sentence-transformers pulls in PyTorch (~440 MB on Mac, ~2 GB with
the CUDA libs on Linux) → an install wall for new users.
fastembed uses the SAME model (all-MiniLM-L6-v2) in ONNX: ~50 MB,
faster startup, zero PyTorch.

The .encode() API mirrors SentenceTransformer's so nothing else in the
codebase (server.py, memory_auto_review.py) needs to change.
"""

from __future__ import annotations

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def _get_model():
    """Loads the ONNX model once (downloaded on first call)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


class Embedder:
    """Compatible with SentenceTransformer.encode().

    - encode("text")     → 1D vector
    - encode(["a", "b"])  → 2D matrix (n, dim)
    fastembed vectors are already normalized (L2 norm = 1).
    """

    def encode(self, texts):
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        vecs = np.array(list(_get_model().embed(list(texts))))
        return vecs[0] if single else vecs
