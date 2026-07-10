"""Priority and escalation logic.

These are simple heuristics, NOT clinical assessments.
"""
from typing import Literal, Optional

ReviewReason = Literal["low_confidence", "multiple_findings"]


def compute_priority(scores: dict[str, float]) -> str:
    """Return 'High' if any score > 0.7, else 'Normal'."""
    if not scores:
        return "Normal"
    return "High" if max(scores.values()) > 0.7 else "Normal"


def needs_human_review(scores: dict[str, float]) -> Optional[ReviewReason]:
    """
    Return a reason string if the case needs human review, else None.

    Two independent conditions (checked in order; first match wins):

    - "low_confidence":    the single highest score is in [0.4, 0.6] inclusive
                           — even the best guess is not confident.

    - "multiple_findings": 2 or more findings score above 0.6
                           — multiple concurrent findings need clinical correlation.

    Returns None when neither condition is met (routine case).
    """
    if not scores:
        return None

    vals = list(scores.values())
    top = max(vals)

    # Condition 1: top score in the uncertain band [0.4, 0.6]
    if 0.4 <= top <= 0.6:
        return "low_confidence"

    # Condition 2: multiple findings above the significance threshold
    significant_count = sum(1 for v in vals if v > 0.6)
    if significant_count >= 2:
        return "multiple_findings"

    return None
