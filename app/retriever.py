"""Embedding index and cosine similarity retrieval."""
import json
import logging
import os
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve absolute path relative to this file's location so the index is
# found regardless of which working directory uvicorn is launched from.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(_HERE, "data", "embeddings.npz")


def load_index(path: str = INDEX_PATH) -> tuple[Optional[np.ndarray], list[dict]]:
    """Load embedding matrix and metadata list from .npz.
    Returns (None, []) gracefully if file is missing.
    """
    try:
        data = np.load(path, allow_pickle=True)
        embeddings = data["embeddings"].astype(np.float32)  # (N, 1024)
        metadata = [json.loads(s) for s in data["metadata"]]
        logger.info(
            "Loaded embedding index: %d vectors from %s", len(metadata), path
        )
        return embeddings, metadata
    except FileNotFoundError:
        logger.warning(
            "Embedding index not found at %s. "
            "Run scripts/build_index.py to generate it.",
            path,
        )
        return None, []
    except Exception as exc:
        logger.error("Failed to load embedding index: %s", exc)
        return None, []


def cosine_search(
    query: np.ndarray,
    embeddings: np.ndarray,
    metadata: list[dict],
    k: int = 5,
) -> list[dict]:
    """Return top-k metadata dicts sorted by cosine similarity descending."""
    if embeddings is None or len(metadata) == 0:
        return []

    # L2-normalise
    q_norm = query / (np.linalg.norm(query) + 1e-8)
    e_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

    sims = e_norms @ q_norm  # (N,)
    top_k = min(k, len(metadata))
    top_indices = np.argsort(sims)[::-1][:top_k]

    results = []
    for idx in top_indices:
        entry = dict(metadata[idx])
        entry["similarity"] = float(sims[idx])
        results.append(entry)
    return results
