"""Tests for evidence mapping and negation handling (app/evidence.py)."""
import pytest
from app.evidence import get_near_top_findings, check_match, match_findings_to_cases


def test_get_near_top_findings():
    scores = {
        "Pneumonia": 0.95,
        "Effusion": 0.91,
        "Atelectasis": 0.89,
        "Cardiomegaly": 0.30
    }
    near_top = get_near_top_findings(scores)
    # 0.95 - 0.05 = 0.90. Pneumonia and Effusion should be included.
    assert "Pneumonia" in near_top
    assert "Effusion" in near_top
    assert "Atelectasis" not in near_top
    assert "Cardiomegaly" not in near_top


def test_get_near_top_findings_empty():
    assert get_near_top_findings({}) == []


def test_negation_checks():
    # True positives (valid matches)
    assert check_match("Effusion", "Findings consistent with pleural effusion.") is True
    assert check_match("Cardiomegaly", "The heart is enlarged.") is True
    assert check_match("Consolidation", "Consolidation seen in the left lower lobe.") is True

    # True negatives (negated matches)
    assert check_match("Effusion", "No evidence of pleural effusion.") is False
    assert check_match("Cardiomegaly", "Without cardiomegaly or congestion.") is False
    assert check_match("Effusion", "The lungs are negative for pleural effusion.") is False
    assert check_match("Pneumothorax", "Not seen: pneumothorax.") is False
    assert check_match("Fibrosis", "Absence of active fibrosis.") is False
    assert check_match("Pneumonia", "Rule out pneumonia.") is False

    # Irrelevant text
    assert check_match("Hernia", "Normal chest radiographic examination.") is False


def test_match_findings_to_cases():
    similar_cases = [
        {
            "uid": "case_1",
            "findings": "Cardiomegaly is present.",
            "impression": "No pleural effusion."
        },
        {
            "uid": "case_2",
            "findings": "Lungs are clear. Pleural space is normal.",
            "impression": "Normal exam."
        },
        {
            "uid": "case_3",
            "findings": "Findings consistent with pleural effusion.",
            "impression": "Enlarged heart is noted."
        }
    ]

    near_top = ["Cardiomegaly", "Effusion"]
    matches = match_findings_to_cases(near_top, similar_cases)

    # case_1 has non-negated Cardiomegaly, negated Effusion
    # case_3 has non-negated Effusion and non-negated Cardiomegaly (enlarged heart)
    assert matches["Cardiomegaly"] == ["case_1", "case_3"]
    assert matches["Effusion"] == ["case_3"]
