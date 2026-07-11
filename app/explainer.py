"""RAG-grounded explanation.

Priority:
  1. OpenAI gpt-4o-mini  — when OPENAI_API_KEY is set
  2. Ollama qwen2.5:7b-instruct — local fallback when key is absent
  3. Static string — when Ollama is also unreachable

Returns (explanation_text, source) where source is one of:
  "openai" | "ollama" | "unavailable"
"""
import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

ExplanationSource = Literal["openai", "ollama", "unavailable"]

FALLBACK = (
    "Automated explanation unavailable. "
    "Please review the finding scores and similar cases directly. "
    "Research prototype — not for clinical use."
)

OLLAMA_MODEL = "mistral"


def build_prompt(query_scores: dict[str, float], similar_cases: list[dict]) -> str:
    """Construct a grounded prompt using retrieved report text as context.
    Reused by both the OpenAI and Ollama paths — no duplication.
    """
    top_findings = sorted(query_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    findings_text = ", ".join(
        f"{label} ({score:.2f})" for label, score in top_findings
    )
    max_score = top_findings[0][1] if top_findings else 0.0

    context_parts = []
    for case in similar_cases:
        uid = case.get("uid")
        findings = case.get("findings")
        impression = case.get("impression")
        parts = []
        if findings is not None:
            parts.append(findings)
        if impression is not None:
            parts.append(impression)
        if parts:
            context_parts.append(f"Case {uid}: {' '.join(parts)}")

    context_block = (
        "\n".join(context_parts)
        if context_parts
        else "No similar historical cases available."
    )

    if max_score < 0.4:
        low_confidence_instruction = (
            "IMPORTANT: The current image's highest finding score is below 0.4, meaning no finding is even moderately confident. "
            "You MUST state plainly that no strong findings were detected and that retrieved historical cases are largely unremarkable or normal. "
            "Do NOT force an explanation connecting these low-confidence scores to specific diseases."
        )
    else:
        low_confidence_instruction = ""

    return (
        f"You are a medical AI assistant helping radiologists review chest X-rays. "
        f"This is a RESEARCH PROTOTYPE — NOT for clinical use.\n\n"
        f"The current image's model scores (top findings): {findings_text}\n\n"
        f"Similar historical cases from the dataset showed:\n{context_block}\n\n"
        f"Based ONLY on the information above, describe in 2-3 plain-language sentences "
        f"what the current image's findings may be consistent with.\n"
        f"CRITICAL RULES:\n"
        f"1. Never cite a negated statement (e.g. 'no evidence of X', 'without X', 'X is not present', 'no active disease') from a retrieved case as if it supports or suggests X is present in the current image. Negated mentions should only be used to say a case was unremarkable for that finding, never as pathological evidence.\n"
        f"2. When referencing a finding that has supporting historical evidence, use its exact label name as given (e.g. 'Effusion', not a paraphrase), so it can be matched precisely later. Only claim similarity to historical cases for findings explicitly listed as having evidence. "
        f"Do not invent information not present in the context.\n"
        f"3. When referencing a historical case, refer to it exactly by its case ID as presented in the context (e.g. 'Case 1241' or 'Case 328'). Do not refer to them as 'Case 1', 'Case 2', etc., or by their list order index.\n"
        f"{low_confidence_instruction}\n"
        f"End with: 'This is AI-generated prototype output — not for clinical use.'"
    )


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def _call_ollama(prompt: str) -> str:
    import ollama

    response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
    return response["response"].strip()


def get_explanation(prompt: str) -> tuple[str, ExplanationSource]:
    """Return (explanation_text, source).

    Tries OpenAI first (if key present), then Ollama, then static fallback.
    Never raises — the app must not crash because no LLM is reachable.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if api_key:
        try:
            text = _call_openai(prompt, api_key)
            logger.info("Explanation generated via OpenAI.")
            return text, "openai"
        except Exception as exc:
            logger.error("OpenAI call failed: %s — trying Ollama.", exc)

    # No API key, or OpenAI failed — try local Ollama
    try:
        text = _call_ollama(prompt)
        logger.info("Explanation generated via Ollama (%s).", OLLAMA_MODEL)
        return text, "ollama"
    except Exception as exc:
        logger.warning("Ollama call failed: %s — using static fallback.", exc)

    return FALLBACK, "unavailable"
