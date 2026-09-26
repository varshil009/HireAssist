import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..config import settings

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    position_id INTEGER NOT NULL REFERENCES positions(id),
    current_stage INTEGER NOT NULL DEFAULT 0,
    rejected_at TEXT,
    offered_flag INTEGER NOT NULL DEFAULT 0,
    hired_flag INTEGER NOT NULL DEFAULT 0,
    entered_applied_at TEXT NOT NULL,
    entered_screening_at TEXT,
    entered_offered_at TEXT,
    entered_hired_at TEXT
);

CREATE TABLE IF NOT EXISTS stage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    from_stage INTEGER NOT NULL,
    to_stage INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL UNIQUE REFERENCES candidates(id),
    file_blob BLOB NOT NULL,
    filename TEXT,
    uploaded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(current_stage);
CREATE INDEX IF NOT EXISTS idx_candidates_position ON candidates(position_id);
CREATE INDEX IF NOT EXISTS idx_stage_events_candidate ON stage_events(candidate_id);

CREATE TRIGGER IF NOT EXISTS stage_events_immutable
BEFORE UPDATE ON stage_events
BEGIN
    SELECT RAISE(ABORT, 'stage events are immutable');
END;

CREATE TRIGGER IF NOT EXISTS stage_events_no_delete
BEFORE DELETE ON stage_events
BEGIN
    SELECT RAISE(ABORT, 'stage events cannot be deleted');
END;
"""


def ensure_db_dir() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    ensure_db_dir()
    with sqlite3.connect(settings.database_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_connection(*, read_only: bool = False):
    ensure_db_dir()
    uri = f"file:{settings.database_path}?mode={'ro' if read_only else 'rwc'}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        if not read_only:
            conn.commit()
    finally:
        conn.close()
