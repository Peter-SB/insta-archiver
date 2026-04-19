"""SQLite database operations for job tracking.

Uses a simple jobs table to track download/transcribe pipeline status.
URL is NOT unique — allows re-processing the same post via "Add Anyway".
Thread-local connections for safe concurrent access from API and worker threads.
"""

import sqlite3
import threading
from datetime import datetime, timezone

from app import config

_local = threading.local()

# Whitelist of columns that can be updated via update_job_status(**fields).
# Prevents SQL injection through dynamic column names.
_ALLOWED_UPDATE_FIELDS = {"note_path", "error_message", "account_name"}


def _get_connection() -> sqlite3.Connection:
    """Get or create a thread-local SQLite connection."""
    if not hasattr(_local, "connection") or _local.connection is None:
        _local.connection = sqlite3.connect(config.DB_PATH, timeout=30)
        _local.connection.row_factory = sqlite3.Row
    return _local.connection


def close_connection() -> None:
    """Close the thread-local database connection. Used in tests and shutdown."""
    if hasattr(_local, "connection") and _local.connection:
        _local.connection.close()
        _local.connection = None


def init_db() -> None:
    """Create the jobs table if it does not exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            url           TEXT    NOT NULL,
            shortcode     TEXT    NOT NULL,
            account_name  TEXT,
            status        TEXT    NOT NULL DEFAULT 'waiting',
            folder        TEXT    NOT NULL DEFAULT 'Insta Archive',
            save_video    INTEGER NOT NULL DEFAULT 0,
            note_path     TEXT,
            error_message TEXT,
            created_at    TEXT    NOT NULL
        )
    """)
    conn.commit()


def create_job(url: str, shortcode: str, folder: str, save_video: bool = False) -> int:
    """Insert a new job with status 'waiting'. Returns the new job ID."""
    conn = _get_connection()
    cursor = conn.execute(
        "INSERT INTO jobs (url, shortcode, folder, save_video, status, created_at) VALUES (?, ?, ?, ?, 'waiting', ?)",
        (url, shortcode, folder, int(save_video), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_jobs() -> list[dict]:
    """Return all jobs, newest first."""
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def get_next_waiting_job() -> dict | None:
    """Return the oldest job with status 'waiting', or None if queue is empty."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM jobs WHERE status = 'waiting' ORDER BY id ASC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def update_job_status(job_id: int, status: str, **fields) -> None:
    """Update a job's status and optional extra fields.

    Only fields in _ALLOWED_UPDATE_FIELDS may be passed as kwargs.
    Raises ValueError for disallowed field names (prevents SQL injection).
    """
    for key in fields:
        if key not in _ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field '{key}' is not an allowed update field")

    set_parts = ["status = ?"]
    values: list = [status]
    for key, value in fields.items():
        set_parts.append(f"{key} = ?")
        values.append(value)
    values.append(job_id)

    conn = _get_connection()
    conn.execute(f"UPDATE jobs SET {', '.join(set_parts)} WHERE id = ?", values)
    conn.commit()


def job_exists_for_url(url: str) -> bool:
    """Check if any job (regardless of status) already exists for this URL."""
    conn = _get_connection()
    row = conn.execute("SELECT 1 FROM jobs WHERE url = ? LIMIT 1", (url,)).fetchone()
    return row is not None
