"""SQLite persistence layer for the chest X-ray triage app."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "cases.db"


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the cases table if it doesn't exist."""
    with get_conn(db_path) as conn:
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

        # Ensure review_reason column exists in case the table was created under an older schema
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN review_reason TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Ensure evidence_links_json column exists
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN evidence_links_json TEXT NOT NULL DEFAULT '{}'")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def insert_case(conn: sqlite3.Connection, case: dict) -> int:
    """Insert a case row and return the new id."""
    cur = conn.execute(
        """
        INSERT INTO cases
            (filename, top_finding, top_score, findings_json,
             heatmap_path, thumbnail_path, priority, status,
             similar_cases_json, explanation, explanation_source,
             review_reason, evidence_links_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case["filename"],
            case["top_finding"],
            case["top_score"],
            case["findings_json"],
            case["heatmap_path"],
            case.get("thumbnail_path", ""),
            case["priority"],
            case.get("status", "pending"),
            case.get("similar_cases_json", "[]"),
            case.get("explanation", ""),
            case.get("explanation_source", "unavailable"),
            case.get("review_reason"),
            case.get("evidence_links_json", "{}"),
            case.get("created_at", datetime.now(timezone.utc).isoformat()),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_queue(conn: sqlite3.Connection, status: Optional[str] = None) -> list[dict]:
    """Return cases filtered by status, sorted High priority first then by created_at asc."""
    if status:
        rows = conn.execute(
            """
            SELECT * FROM cases
            WHERE status = ?
            ORDER BY
                CASE priority WHEN 'High' THEN 0 ELSE 1 END ASC,
                created_at ASC
            """,
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM cases
            ORDER BY
                CASE status WHEN 'needs_human_review' THEN 0 ELSE 1 END ASC,
                CASE priority WHEN 'High' THEN 0 ELSE 1 END ASC,
                created_at ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_case(conn: sqlite3.Connection, case_id: int) -> Optional[dict]:
    """Return full case row or None."""
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def update_case_status(conn: sqlite3.Connection, case_id: int, status: str) -> bool:
    """Update status; return False if row not found."""
    cur = conn.execute(
        "UPDATE cases SET status = ? WHERE id = ?", (status, case_id)
    )
    conn.commit()
    return cur.rowcount > 0


def delete_case(conn: sqlite3.Connection, case_id: int) -> bool:
    """Delete a case; return False if row not found."""
    cur = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    return cur.rowcount > 0
