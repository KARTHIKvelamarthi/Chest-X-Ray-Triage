"""Queue endpoints: GET /api/queue, GET /api/queue/{id}, PATCH /api/queue/{id}."""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.db import get_case, get_queue, update_case_status
from app.models import CaseDetail, CaseSummary, FindingScore, SimilarCase, StatusUpdate

DISCLAIMER = "Research prototype — not for clinical use. Not a diagnostic tool."

router = APIRouter()


def _row_to_summary(row: dict) -> CaseSummary:
    findings_raw = json.loads(row.get("findings_json", "{}"))
    findings = [
        FindingScore(label=lbl, score=sc)
        for lbl, sc in sorted(findings_raw.items(), key=lambda x: x[1], reverse=True)
    ]
    return CaseSummary(
        id=row["id"],
        filename=row["filename"],
        top_finding=row["top_finding"],
        top_score=row["top_score"],
        findings=findings,
        thumbnail_url=row.get("thumbnail_path", ""),
        priority=row["priority"],
        status=row["status"],
        review_reason=row.get("review_reason"),
        created_at=row["created_at"],
    )


def _row_to_detail(row: dict) -> CaseDetail:
    findings_raw = json.loads(row.get("findings_json", "{}"))
    findings = [
        FindingScore(label=lbl, score=sc)
        for lbl, sc in sorted(findings_raw.items(), key=lambda x: x[1], reverse=True)
    ]
    similar_raw = json.loads(row.get("similar_cases_json", "[]"))
    similar_cases = [SimilarCase(**c) for c in similar_raw]

    return CaseDetail(
        id=row["id"],
        filename=row["filename"],
        top_finding=row["top_finding"],
        top_score=row["top_score"],
        findings=findings,
        heatmap_url=row.get("heatmap_path", ""),
        thumbnail_url=row.get("thumbnail_path", ""),
        priority=row["priority"],
        status=row["status"],
        review_reason=row.get("review_reason"),
        similar_cases=similar_cases,
        explanation=row.get("explanation", ""),
        explanation_source=row.get("explanation_source", "unavailable"),
        disclaimer=DISCLAIMER,
        created_at=row["created_at"],
    )


@router.get("/api/queue", response_model=list[CaseSummary])
async def list_queue(request: Request, status: Optional[str] = None):
    conn = request.app.state.db_conn
    rows = get_queue(conn, status)
    return [_row_to_summary(r) for r in rows]


@router.get("/api/queue/{case_id}", response_model=CaseDetail)
async def get_case_detail(case_id: int, request: Request):
    conn = request.app.state.db_conn
    row = get_case(conn, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return _row_to_detail(row)


@router.patch("/api/queue/{case_id}", response_model=CaseDetail)
async def mark_reviewed(case_id: int, body: StatusUpdate, request: Request):
    conn = request.app.state.db_conn
    found = update_case_status(conn, case_id, body.status)
    if not found:
        raise HTTPException(status_code=404, detail="Case not found.")
    row = get_case(conn, case_id)
    return _row_to_detail(row)
