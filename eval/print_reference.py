"""Print reference result ids for eval authoring."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import settings  # noqa: E402

conn = sqlite3.connect(settings.database_path)
conn.row_factory = sqlite3.Row

CHECKS = [
    ("screening", "SELECT id FROM candidates WHERE current_stage = 1 ORDER BY id"),
    (
        "stuck_screening_7d",
        "SELECT id FROM candidates WHERE current_stage = 1 "
        "AND entered_screening_at <= '2025-09-17T12:00:00+00:00' ORDER BY id",
    ),
    (
        "offered_not_hired",
        "SELECT id FROM candidates WHERE offered_flag = 1 AND hired_flag = 0 ORDER BY id",
    ),
    ("not_rejected", "SELECT id FROM candidates WHERE current_stage != -1 ORDER BY id"),
    (
        "screening_since_monday",
        "SELECT id FROM candidates WHERE entered_screening_at >= '2025-09-22T00:00:00+00:00' ORDER BY id",
    ),
    ("priya", "SELECT id FROM candidates WHERE name LIKE '%Priya%' ORDER BY id"),
    ("pos_102", "SELECT c.id FROM candidates c JOIN positions p ON p.id = c.position_id WHERE p.position_code = 'POS-102' ORDER BY c.id"),
]

for name, sql in CHECKS:
    ids = [r[0] for r in conn.execute(sql).fetchall()]
    print(name, ids)
