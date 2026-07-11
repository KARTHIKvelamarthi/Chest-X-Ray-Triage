"""POST /api/analyze — orchestrates the full inference pipeline."""
import io
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from PIL import Image, UnidentifiedImageError

from app.classifier import run_inference, get_query_embedding
from app.db import insert_case
from app.evidence import get_near_top_findings, match_findings_to_cases
from app.explainer import build_prompt, get_explanation
from app.gradcam import generate_heatmap
from app.models import AnalyzeResponse, FindingScore, SimilarCase
from app.priority import compute_priority, needs_human_review
from app.retriever import cosine_search

THUMBNAIL_DIR = os.path.join("static", "thumbnails")
UPLOAD_DIR = os.path.join("static", "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DISCLAIMER = "Research prototype — not for clinical use. Not a diagnostic tool."

router = APIRouter()


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, file: UploadFile = File(...)):
    # --- size guard ---
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    # --- MIME type validation ---
    allowed = {"image/jpeg", "image/png", "image/jpg"}
    content_type = file.content_type or ""
    if content_type not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type '{content_type}'. Only JPG/PNG are accepted.",
        )

    # --- decode image ---
    try:
        pil_img = Image.open(io.BytesIO(content))
        pil_img.verify()  # catch corrupt files
        pil_img = Image.open(io.BytesIO(content))  # re-open after verify
    except (UnidentifiedImageError, Exception) as exc:
        raise HTTPException(
            status_code=422, detail=f"Cannot decode image: {exc}"
        )

    # --- pull app state set at startup ---
    model = request.app.state.model
    embeddings = request.app.state.embeddings
    metadata = request.app.state.index_metadata

    # --- inference ---
    try:
        scores = run_inference(model, pil_img)
        embedding = get_query_embedding(model, pil_img)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    # --- top finding ---
    top_label = max(scores, key=scores.get)
    top_score = scores[top_label]
    label_list = list(model.pathologies)
    top_idx = label_list.index(top_label)

    # --- Grad-CAM ---
    try:
        heatmap_url = generate_heatmap(model, pil_img, top_idx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Grad-CAM failed: {exc}")

    # --- save thumbnail ---
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    thumb_name = f"{uuid.uuid4().hex}_thumb.png"
    thumb_path = os.path.join(THUMBNAIL_DIR, thumb_name)
    thumb = pil_img.convert("RGB")
    thumb.thumbnail((128, 128))
    thumb.save(thumb_path)
    thumbnail_url = f"/static/thumbnails/{thumb_name}"

    # --- retrieval ---
    similar_raw = cosine_search(embedding, embeddings, metadata, k=5)
    similar_cases = [
        SimilarCase(
            uid=str(c.get("uid", "")),
            findings=c.get("findings"),
            impression=c.get("impression"),
            similarity=c.get("similarity", 0.0),
        )
        for c in similar_raw
    ]

    # --- evidence linking ---
    near_top = get_near_top_findings(scores)
    evidence_links = match_findings_to_cases(near_top, similar_raw)

    # --- grounded explanation ---
    prompt = build_prompt(scores, similar_raw)
    explanation, explanation_source = get_explanation(prompt)

    # --- priority / escalation ---
    priority = compute_priority(scores)
    review_reason = needs_human_review(scores)
    status = "needs_human_review" if review_reason else "pending"

    # --- persist ---
    now = datetime.now(timezone.utc).isoformat()
    original_filename = file.filename or "upload.png"
    case_row = {
        "filename": original_filename,
        "top_finding": top_label,
        "top_score": top_score,
        "findings_json": json.dumps(scores),
        "heatmap_path": heatmap_url,
        "thumbnail_path": thumbnail_url,
        "priority": priority,
        "status": status,
        "review_reason": review_reason,
        "similar_cases_json": json.dumps([c.model_dump() for c in similar_cases]),
        "explanation": explanation,
        "explanation_source": explanation_source,
        "evidence_links_json": json.dumps(evidence_links),
        "created_at": now,
    }

    conn = request.app.state.db_conn
    case_id = insert_case(conn, case_row)

    findings_list = [
        FindingScore(label=lbl, score=sc) for lbl, sc in sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )
    ]

    return AnalyzeResponse(
        id=case_id,
        filename=original_filename,
        top_finding=top_label,
        top_score=top_score,
        findings=findings_list,
        heatmap_url=heatmap_url,
        thumbnail_url=thumbnail_url,
        priority=priority,
        status=status,
        review_reason=review_reason,
        similar_cases=similar_cases,
        explanation=explanation,
        explanation_source=explanation_source,
        evidence_links=evidence_links,
        disclaimer=DISCLAIMER,
        created_at=now,
    )
