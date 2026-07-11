"""Evidence matching and negation analysis logic."""
import re

SYNONYM_MAP = {
    "Atelectasis": ["atelectasis", "atelectatic", "collapse", "lobar collapse"],
    "Consolidation": ["consolidation", "consolidative", "airspace disease", "airspace opacity", "airspace opacities"],
    "Infiltration": ["infiltration", "infiltrate", "infiltrates", "interstitial opacity", "interstitial opacities"],
    "Pneumothorax": ["pneumothorax", "collapsed lung", "air in pleural space"],
    "Edema": ["edema", "pulmonary edema", "fluid in lungs", "congestion", "vascular congestion"],
    "Emphysema": ["emphysema", "hyperinflation", "copd"],
    "Fibrosis": ["fibrosis", "scarring", "fibrotic change", "fibrotic changes"],
    "Effusion": ["effusion", "pleural effusion", "fluid in pleural space", "pleural fluid"],
    "Pneumonia": ["pneumonia", "infection", "bronchopneumonia"],
    "Pleural_Thickening": ["pleural thickening", "thickened pleura", "pleural scar"],
    "Cardiomegaly": ["cardiomegaly", "enlarged cardiac silhouette", "enlarged heart", "heart enlargement", "heart is enlarged"],
    "Nodule": ["nodule", "nodules", "pulmonary nodule", "pulmonary nodules", "small mass"],
    "Mass": ["mass", "masses", "tumor", "tumors", "lesion", "lesions"],
    "Hernia": ["hernia", "hiatal hernia", "diaphragmatic hernia"],
    "Lung Lesion": ["lung lesion", "lung lesions", "lesion", "lesions"],
    "Fracture": ["fracture", "fractures", "broken rib", "broken ribs", "rib fracture", "rib fractures"],
    "Lung Opacity": ["lung opacity", "lung opacities", "opacity", "opacities", "density", "densities"],
    "Enlarged Cardiomediastinum": ["enlarged cardiomediastinum", "cardiomediastinal widening", "widened mediastinum"]
}


def get_near_top_findings(scores: dict[str, float]) -> list[str]:
    """Return all finding labels whose score is within 5 percentage points (0.05) of the highest score."""
    if not scores:
        return []
    max_score = max(scores.values())
    threshold = max_score - 0.05
    return [label for label, score in scores.items() if score >= threshold]


def check_match(finding: str, text: str) -> bool:
    """Return True if the finding (or any of its synonyms) occurs in text and is NOT negated."""
    if not text:
        return False

    text_lower = text.lower()
    synonyms = SYNONYM_MAP.get(finding, [finding])
    finding_normalized = finding.lower().replace("_", " ")
    all_terms = list(set([finding_normalized] + [syn.lower() for syn in synonyms]))

    negation_cues = ["no", "without", "negative for", "not seen", "absence of", "rule out", "none"]

    for term in all_terms:
        # Search for the term with word boundaries
        pattern = r"\b" + re.escape(term) + r"\b"
        for match in re.finditer(pattern, text_lower):
            start_pos = match.start()
            before_substring = text_lower[:start_pos].strip()
            words = before_substring.split()
            recent_words = words[-5:] if len(words) > 5 else words
            recent_text = " ".join(recent_words)

            is_negated = False
            for cue in negation_cues:
                cue_pattern = r"\b" + re.escape(cue) + r"\b"
                if re.search(cue_pattern, recent_text):
                    is_negated = True
                    break

            if not is_negated:
                return True

    return False


def match_findings_to_cases(near_top_findings: list[str], similar_cases: list) -> dict[str, list[str]]:
    """For each near-top finding, match against findings/impression text in similar historical cases."""
    evidence = {}
    for finding in near_top_findings:
        matching_uids = []
        for case in similar_cases:
            if isinstance(case, dict):
                uid = str(case.get("uid", ""))
                findings = case.get("findings", "") or ""
                impression = case.get("impression", "") or ""
            else:
                uid = str(getattr(case, "uid", ""))
                findings = getattr(case, "findings", "") or ""
                impression = getattr(case, "impression", "") or ""

            combined_text = f"{findings} {impression}"
            if check_match(finding, combined_text):
                matching_uids.append(uid)

        if matching_uids:
            evidence[finding] = matching_uids

    return evidence
