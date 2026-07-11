"""Tests for DB operations (Properties P6, P7, P8)."""
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.db import delete_case, get_case, get_queue, init_db, insert_case, update_case_status


def make_conn():
    """Return an in-memory SQLite connection with the schema initialised."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Run init_db against the in-memory connection directly
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            filename        TEXT    NOT NULL,
            top_finding     TEXT    NOT NULL,
            top_score       REAL    NOT NULL,
            findings_json   TEXT    NOT NULL,
            heatmap_path    TEXT    NOT NULL,
            thumbnail_path  TEXT    NOT NULL,
            priority        TEXT    NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'pending',
            similar_cases_json TEXT NOT NULL DEFAULT '[]',
            explanation     TEXT    NOT NULL DEFAULT '',
            explanation_source TEXT NOT NULL DEFAULT 'unavailable',
            review_reason   TEXT,
            evidence_links_json TEXT NOT NULL DEFAULT '{}',
            created_at      TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


def make_case(
    filename="test.png",
    top_finding="Pneumonia",
    top_score=0.8,
    priority="High",
    status="pending",
    created_at=None,
    review_reason=None,
):
    return {
        "filename": filename,
        "top_finding": top_finding,
        "top_score": top_score,
        "findings_json": json.dumps({"Pneumonia": top_score}),
        "heatmap_path": "/static/heatmaps/test.png",
        "thumbnail_path": "/static/thumbnails/test.png",
        "priority": priority,
        "status": status,
        "similar_cases_json": "[]",
        "explanation": "Test explanation.",
        "review_reason": review_reason,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }


# --- P6: Case persistence round-trip ---
# Feature: chest-xray-triage, Property 6
@given(
    top_finding=st.text(min_size=1, max_size=50),
    top_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    priority=st.sampled_from(["High", "Normal"]),
    status=st.sampled_from(["pending", "reviewed", "needs_human_review"]),
    review_reason=st.sampled_from(["low_confidence", "multiple_findings", None]),
)
@settings(max_examples=100)
def test_case_persistence_roundtrip(top_finding, top_score, priority, status, review_reason):
    conn = make_conn()
    case = make_case(
        top_finding=top_finding,
        top_score=top_score,
        priority=priority,
        status=status,
        review_reason=review_reason,
    )
    case_id = insert_case(conn, case)
    retrieved = get_case(conn, case_id)
    assert retrieved is not None
    assert retrieved["top_finding"] == top_finding
    assert abs(retrieved["top_score"] - top_score) < 1e-9
    assert retrieved["priority"] == priority
    assert retrieved["status"] == status
    assert retrieved["review_reason"] == review_reason


# --- P7: Queue filter returns only matching-status cases in correct order ---
# Feature: chest-xray-triage, Property 7
def test_queue_filter_by_status():
    conn = make_conn()
    insert_case(conn, make_case(priority="High", status="pending", created_at="2024-01-01T00:00:00+00:00"))
    insert_case(conn, make_case(priority="Normal", status="pending", created_at="2024-01-02T00:00:00+00:00"))
    insert_case(conn, make_case(priority="Normal", status="reviewed", created_at="2024-01-03T00:00:00+00:00"))

    pending = get_queue(conn, status="pending")
    assert all(r["status"] == "pending" for r in pending)
    assert len(pending) == 2

    reviewed = get_queue(conn, status="reviewed")
    assert all(r["status"] == "reviewed" for r in reviewed)
    assert len(reviewed) == 1


def test_queue_priority_order():
    conn = make_conn()
    insert_case(conn, make_case(priority="Normal", status="pending", created_at="2024-01-01T00:00:00+00:00"))
    insert_case(conn, make_case(priority="High", status="pending", created_at="2024-01-02T00:00:00+00:00"))

    rows = get_queue(conn, status="pending")
    assert rows[0]["priority"] == "High"
    assert rows[1]["priority"] == "Normal"


# --- P8: Mark-reviewed removes case from pending view ---
# Feature: chest-xray-triage, Property 8
def test_mark_reviewed_moves_case():
    conn = make_conn()
    case_id = insert_case(conn, make_case(status="pending"))

    # Confirm it's in pending
    pending_before = get_queue(conn, status="pending")
    assert any(r["id"] == case_id for r in pending_before)

    # Mark reviewed
    result = update_case_status(conn, case_id, "reviewed")
    assert result is True

    # Should no longer be in pending
    pending_after = get_queue(conn, status="pending")
    assert not any(r["id"] == case_id for r in pending_after)

    # Should be in reviewed
    reviewed = get_queue(conn, status="reviewed")
    assert any(r["id"] == case_id for r in reviewed)


def test_update_nonexistent_case():
    conn = make_conn()
    assert update_case_status(conn, 9999, "reviewed") is False


def test_get_nonexistent_case():
    conn = make_conn()
    assert get_case(conn, 9999) is None


def test_delete_case():
    conn = make_conn()
    case_id = insert_case(conn, make_case())
    assert get_case(conn, case_id) is not None
    assert delete_case(conn, case_id) is True
    assert get_case(conn, case_id) is None


def test_delete_nonexistent_case():
    conn = make_conn()
    assert delete_case(conn, 9999) is False
