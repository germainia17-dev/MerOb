"""
embeddings.py
─────────────
Wrapper d'embeddings basé sur fastembed (ONNX) au lieu de
sentence-transformers (PyTorch).

Pourquoi : sentence-transformers tire PyTorch (~440 Mo sur Mac, ~2 Go avec
les libs CUDA sur Linux) → mur d'installation pour les nouveaux utilisateurs.
fastembed utilise le MÊME modèle (all-MiniLM-L6-v2) en ONNX : ~50 Mo,
démarrage plus rapide, zéro PyTorch.

L'API .encode() reproduit celle de SentenceTransformer pour ne rien casser
dans le reste du code (server.py, memory_auto_review.py).
"""

from __future__ import annotations

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def _get_model():
    """Charge le modèle ONNX une seule fois (téléchargé au 1er appel)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


class Embedder:
    """Compatible avec SentenceTransformer.encode().

    - encode("texte")        → vecteur 1D
    - encode(["a", "b"])     → matrice 2D (n, dim)
    Les vecteurs fastembed sont déjà normalisés (norme L2 = 1).
    """

    def encode(self, texts):
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        vecs = np.array(list(_get_model().embed(list(texts))))
        return vecs[0] if single else vecs
