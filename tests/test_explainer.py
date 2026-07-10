"""Tests for explainer prompt construction (Property P5)."""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.explainer import FALLBACK, build_prompt, get_explanation


# --- P5: Prompt contains all retrieved report text ---
# Feature: chest-xray-triage, Property 5
@given(
    cases=st.lists(
        st.fixed_dictionaries({
            "uid": st.text(min_size=1, max_size=10),
            "findings": st.one_of(st.none(), st.text(min_size=1, max_size=200)),
            "impression": st.one_of(st.none(), st.text(min_size=1, max_size=200)),
            "similarity": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        }),
        min_size=1,
        max_size=5,
    ),
    scores=st.dictionaries(
        st.text(min_size=1, max_size=30),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=18,
    ),
)
@settings(max_examples=100)
def test_prompt_contains_all_impressions(cases, scores):
    prompt = build_prompt(scores, cases)
    for case in cases:
        impression = case.get("impression")
        if impression:
            assert impression in prompt, (
                f"Impression '{impression[:40]}...' not found in prompt"
            )


def test_build_prompt_no_similar_cases():
    prompt = build_prompt({"Pneumonia": 0.8}, [])
    assert "No similar historical cases available" in prompt


def test_fallback_string():
    assert "not for clinical use" in FALLBACK.lower()
    # get_explanation returns (text, source) — verify graceful fallback when no key set
    import os
    os.environ.pop("OPENAI_API_KEY", None)
    text, source = get_explanation("test prompt")
    # Either ollama or unavailable — never raises
    assert isinstance(text, str)
    assert source in ("ollama", "unavailable")
