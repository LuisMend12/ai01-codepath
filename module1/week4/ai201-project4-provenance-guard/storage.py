"""SQLite-backed storage for submissions + the structured audit log."""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "provenance.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            llm_score REAL NOT NULL,
            stylometric_score REAL NOT NULL,
            confidence REAL NOT NULL,
            attribution TEXT NOT NULL,
            label TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            content_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            attribution TEXT,
            confidence REAL,
            llm_score REAL,
            stylometric_score REAL,
            status TEXT,
            appeal_reasoning TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_submission(content_id, creator_id, text, llm_score, stylometric_score,
                     confidence, attribution, label):
    timestamp = _now()
    conn = get_connection()
    conn.execute(
        """INSERT INTO submissions
           (content_id, creator_id, text, timestamp, llm_score,
            stylometric_score, confidence, attribution, label, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'classified')""",
        (content_id, creator_id, text, timestamp, llm_score,
         stylometric_score, confidence, attribution, label),
    )
    conn.execute(
        """INSERT INTO audit_log
           (timestamp, content_id, creator_id, event_type, attribution,
            confidence, llm_score, stylometric_score, status, appeal_reasoning)
           VALUES (?, ?, ?, 'classification', ?, ?, ?, ?, 'classified', NULL)""",
        (timestamp, content_id, creator_id, attribution, confidence,
         llm_score, stylometric_score),
    )
    conn.commit()
    conn.close()
    return timestamp


def get_submission(content_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM submissions WHERE content_id = ?", (content_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def file_appeal(content_id, creator_reasoning):
    submission = get_submission(content_id)
    if submission is None:
        return None

    timestamp = _now()
    conn = get_connection()
    conn.execute(
        "UPDATE submissions SET status = 'under_review' WHERE content_id = ?",
        (content_id,),
    )
    conn.execute(
        """INSERT INTO audit_log
           (timestamp, content_id, creator_id, event_type, attribution,
            confidence, llm_score, stylometric_score, status, appeal_reasoning)
           VALUES (?, ?, ?, 'appeal', ?, ?, ?, ?, 'under_review', ?)""",
        (timestamp, content_id, submission["creator_id"], submission["attribution"],
         submission["confidence"], submission["llm_score"],
         submission["stylometric_score"], creator_reasoning),
    )
    conn.commit()
    conn.close()
    return timestamp


def get_log(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
