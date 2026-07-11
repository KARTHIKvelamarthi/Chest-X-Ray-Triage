"""Shared Pydantic models."""
from typing import Literal, Optional
from pydantic import BaseModel


class FindingScore(BaseModel):
    label: str
    score: float


class SimilarCase(BaseModel):
    uid: str
    findings: Optional[str] = None
    impression: Optional[str] = None
    similarity: float
    image_url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    id: int
    filename: str
    top_finding: str
    top_score: float
    findings: list[FindingScore]
    heatmap_url: str
    thumbnail_url: str
    priority: str
    status: str
    review_reason: Optional[str] = None   # "low_confidence" | "multiple_findings" | None
    similar_cases: list[SimilarCase]
    explanation: str
    explanation_source: Literal["openai", "ollama", "unavailable"]
    evidence_links: dict[str, list[str]] = {}
    disclaimer: str
    created_at: str


class CaseSummary(BaseModel):
    id: int
    filename: str
    top_finding: str
    top_score: float
    findings: Optional[list[FindingScore]] = None
    thumbnail_url: str
    priority: str
    status: str
    review_reason: Optional[str] = None   # "low_confidence" | "multiple_findings" | None
    created_at: str


class CaseDetail(BaseModel):
    id: int
    filename: str
    top_finding: str
    top_score: float
    findings: list[FindingScore]
    heatmap_url: str
    thumbnail_url: str
    priority: str
    status: str
    review_reason: Optional[str] = None
    similar_cases: list[SimilarCase]
    explanation: str
    explanation_source: Literal["openai", "ollama", "unavailable"]
    evidence_links: dict[str, list[str]] = {}
    disclaimer: str
    created_at: str


class StatusUpdate(BaseModel):
    status: Literal["reviewed"]
