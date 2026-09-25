"""Print reference result ids for eval authoring."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import settings  # noqa: E402

MONDAY_START = (
    "datetime('now', 'start of day', '-' || ((CAST(strftime('%w', 'now') AS INTEGER) + 6) % 7) || ' days')"
)

CHECKS = [
    ("screening", "SELECT id FROM candidates WHERE current_stage = 1 ORDER BY id"),
    (
        "stuck_screening_7d",
        "SELECT id FROM candidates WHERE current_stage = 1 "
        f"AND datetime(entered_screening_at) <= datetime('now', '-7 days') ORDER BY id",
    ),
    (
        "offered_not_hired",
        "SELECT id FROM candidates WHERE offered_flag = 1 AND hired_flag = 0 ORDER BY id",
    ),
    ("not_rejected", "SELECT id FROM candidates WHERE current_stage != -1 ORDER BY id"),
    (
        "screening_since_monday",
        f"SELECT id FROM candidates WHERE datetime(entered_screening_at) >= {MONDAY_START} ORDER BY id",
    ),
    (
        "offered_since_monday",
        f"SELECT id FROM candidates WHERE datetime(entered_offered_at) >= {MONDAY_START} ORDER BY id",
    ),
    ("priya", "SELECT id FROM candidates WHERE name LIKE '%Priya%' ORDER BY id"),
]

conn = sqlite3.connect(settings.database_path)
for name, sql in CHECKS:
    ids = [r[0] for r in conn.execute(sql).fetchall()]
    print(name, ids)
