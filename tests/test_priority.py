"""Tests for priority and escalation logic (Properties P9, P10)."""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.priority import compute_priority, needs_human_review


# --- P9: compute_priority assigns High iff any score exceeds 0.7 ---
# Feature: chest-xray-triage, Property 9
@given(
    scores=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_compute_priority_property(scores):
    result = compute_priority(scores)
    if any(v > 0.7 for v in scores.values()):
        assert result == "High"
    else:
        assert result == "Normal"


def test_compute_priority_empty():
    assert compute_priority({}) == "Normal"


def test_compute_priority_exact_boundary():
    assert compute_priority({"A": 0.7}) == "Normal"
    assert compute_priority({"A": 0.701}) == "High"


# --- P10: needs_human_review triggers on ambiguous or low-confidence scores ---
# Feature: chest-xray-triage, Property 10
@given(
    scores=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_needs_human_review_property(scores):
    result = needs_human_review(scores)
    if not scores:
        assert result is None
        return
    vals = list(scores.values())
    top = max(vals)
    if 0.4 <= top <= 0.6:
        expected = "low_confidence"
    elif sum(1 for v in vals if v > 0.6) >= 2:
        expected = "multiple_findings"
    else:
        expected = None
    assert result == expected


def test_needs_human_review_not_enough_scores():
    assert needs_human_review({"A": 0.9}) is None
    assert needs_human_review({}) is None


def test_needs_human_review_low_confidence():
    assert needs_human_review({"A": 0.5}) == "low_confidence"
    assert needs_human_review({"A": 0.4, "B": 0.3}) == "low_confidence"
    assert needs_human_review({"A": 0.6, "B": 0.1}) == "low_confidence"


def test_needs_human_review_multiple_findings():
    assert needs_human_review({"A": 0.7, "B": 0.8}) == "multiple_findings"
    assert needs_human_review({"A": 0.7, "B": 0.8, "C": 0.3}) == "multiple_findings"


def test_needs_human_review_clear_winner():
    # top is 0.7 (> 0.6), other is 0.5 (<= 0.6) -> single significant finding, top is not in [0.4, 0.6]
    assert needs_human_review({"A": 0.7, "B": 0.5}) is None
