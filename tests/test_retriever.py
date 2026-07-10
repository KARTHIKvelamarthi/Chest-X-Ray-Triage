"""Tests for cosine retrieval (Property P4)."""
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.retriever import cosine_search, load_index


# --- P4: Retrieval returns k sorted results with required fields ---
# Feature: chest-xray-triage, Property 4
@given(
    n=st.integers(min_value=1, max_value=50),
    k=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100)
def test_cosine_search_property(n, k):
    rng = np.random.default_rng(42)
    embeddings = rng.standard_normal((n, 32)).astype(np.float32)
    metadata = [
        {"uid": str(i), "findings": f"findings {i}", "impression": f"impression {i}"}
        for i in range(n)
    ]
    query = rng.standard_normal(32).astype(np.float32)

    results = cosine_search(query, embeddings, metadata, k=k)

    expected_len = min(k, n)
    assert len(results) == expected_len

    # Sorted descending by similarity
    sims = [r["similarity"] for r in results]
    assert sims == sorted(sims, reverse=True), "Results not sorted by similarity"

    # Required fields present
    for r in results:
        assert "uid" in r
        assert "findings" in r
        assert "impression" in r
        assert "similarity" in r
        assert -1.0 <= r["similarity"] <= 1.0 + 1e-6


def test_cosine_search_empty_index():
    query = np.ones(32, dtype=np.float32)
    assert cosine_search(query, None, [], k=5) == []


def test_load_index_missing_file(tmp_path):
    embeddings, metadata = load_index(str(tmp_path / "nonexistent.npz"))
    assert embeddings is None
    assert metadata == []
