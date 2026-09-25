"""
Idempotent seed for HireAssist mock data.
Run from repo root: python -m backend.scripts.seed
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# Real resume bytes for every seeded candidate (place file in repo data/).
DEFAULT_RESUME_FILE = ROOT / "data" / "VARSHIL_PRAJAPATI_CV25.pdf"

from app.config import settings  # noqa: E402
from app.db.database import SCHEMA, ensure_db_dir  # noqa: E402

# Fixed anchor so eval queries referencing "last Monday" stay stable.
ANCHOR = datetime(2025, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
LAST_MONDAY = datetime(2025, 9, 22, 0, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def load_seed_resume(resume_path: Path = DEFAULT_RESUME_FILE) -> tuple[bytes, str]:
    if not resume_path.is_file():
        raise FileNotFoundError(
            f"Seed resume not found at {resume_path}. "
            "Add your PDF under data/ (e.g. VARSHIL_PRAJAPATI_CV25.pdf) and re-run seed."
        )
    return resume_path.read_bytes(), resume_path.name


def reset_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM resumes;
        DELETE FROM stage_events;
        DELETE FROM candidates;
        DELETE FROM positions;
        DELETE FROM sqlite_sequence;
        """
    )


def seed() -> None:
    ensure_db_dir()
    with sqlite3.connect(settings.database_path) as conn:
        conn.executescript(SCHEMA)
        reset_db(conn)

        positions = [
            ("POS-101", "Senior Backend Engineer"),
            ("POS-102", "Product Designer"),
            ("POS-103", "Data Analyst"),
        ]
        conn.executemany(
            "INSERT INTO positions (position_code, title) VALUES (?, ?)",
            positions,
        )

        # id 1,2,3 for positions

        def cand(
            name,
            email,
            phone,
            pos_id,
            stage,
            *,
            applied=None,
            screening=None,
            offered=None,
            hired=None,
            rejected=None,
            offered_flag=0,
            hired_flag=0,
        ):
            applied = applied or iso(ANCHOR - timedelta(days=30))
            cur = conn.execute(
                """
                INSERT INTO candidates (
                    name, email, phone, position_id, current_stage,
                    rejected_at, offered_flag, hired_flag,
                    entered_applied_at, entered_screening_at,
                    entered_offered_at, entered_hired_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    phone,
                    pos_id,
                    stage,
                    rejected,
                    offered_flag,
                    hired_flag,
                    applied,
                    screening,
                    offered,
                    hired,
                ),
            )
            cid = cur.lastrowid
            events = [(-99, 0, applied)]
            if screening:
                events.append((0, 1, screening))
            if offered:
                events.append((1, 2, offered))
            if hired:
                events.append((2, 3, hired))
            if rejected and stage == -1:
                prev = 0
                if offered:
                    prev = 2
                elif screening:
                    prev = 1
                events.append((prev, -1, rejected))
            for fs, ts, at in events:
                conn.execute(
                    """
                    INSERT INTO stage_events (candidate_id, from_stage, to_stage, occurred_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (cid, fs, ts, at),
                )
            return cid

        ids: dict[str, int] = {}

        ids["priya"] = cand(
            "Priya Sharma",
            "priya.sharma@example.com",
            "555-0101",
            1,
            1,
            screening=iso(ANCHOR - timedelta(days=5)),
        )
        ids["amit"] = cand(
            "Amit Patel",
            "amit.patel@example.com",
            "555-0102",
            1,
            1,
            screening=iso(ANCHOR - timedelta(days=10)),
        )
        ids["stuck1"] = cand(
            "Sara Nguyen",
            "sara.nguyen@example.com",
            "555-0103",
            2,
            1,
            screening=iso(ANCHOR - timedelta(days=12)),
        )
        ids["stuck2"] = cand(
            "James O'Brien",
            "james.obrien@example.com",
            "555-0104",
            3,
            1,
            screening=iso(ANCHOR - timedelta(days=9)),
        )
        ids["recent_screen"] = cand(
            "Lina Cho",
            "lina.cho@example.com",
            "555-0105",
            1,
            1,
            screening=iso(LAST_MONDAY + timedelta(hours=10)),
        )
        ids["offer_open"] = cand(
            "Marcus Lee",
            "marcus.lee@example.com",
            "555-0106",
            1,
            2,
            screening=iso(ANCHOR - timedelta(days=20)),
            offered=iso(ANCHOR - timedelta(days=3)),
            offered_flag=1,
        )
        ids["offer_rejected"] = cand(
            "Elena Rossi",
            "elena.rossi@example.com",
            "555-0107",
            2,
            -1,
            screening=iso(ANCHOR - timedelta(days=25)),
            offered=iso(ANCHOR - timedelta(days=8)),
            rejected=iso(ANCHOR - timedelta(days=2)),
            offered_flag=1,
        )
        ids["hired"] = cand(
            "Noah Kim",
            "noah.kim@example.com",
            "555-0108",
            3,
            3,
            screening=iso(ANCHOR - timedelta(days=40)),
            offered=iso(ANCHOR - timedelta(days=15)),
            hired=iso(ANCHOR - timedelta(days=5)),
            offered_flag=1,
            hired_flag=1,
        )
        ids["applied_rej"] = cand(
            "Tom Walsh",
            "tom.walsh@example.com",
            "555-0109",
            1,
            -1,
            rejected=iso(ANCHOR - timedelta(days=4)),
        )
        ids["screen_rej"] = cand(
            "Fatima Ali",
            "fatima.ali@example.com",
            "555-0110",
            2,
            -1,
            screening=iso(ANCHOR - timedelta(days=18)),
            rejected=iso(ANCHOR - timedelta(days=6)),
        )
        ids["recent_offer"] = cand(
            "Olivia Chen",
            "olivia.chen@example.com",
            "555-0111",
            3,
            2,
            screening=iso(ANCHOR - timedelta(days=14)),
            offered=iso(LAST_MONDAY + timedelta(days=1)),
            offered_flag=1,
        )
        ids["applied_only"] = cand(
            "Raj Singh",
            "raj.singh@example.com",
            "555-0112",
            1,
            0,
        )
        ids["designer"] = cand(
            "Maya Johnson",
            "maya.johnson@example.com",
            "555-0113",
            2,
            1,
            screening=iso(ANCHOR - timedelta(days=2)),
        )
        ids["analyst"] = cand(
            "Chris Rivera",
            "chris.rivera@example.com",
            "555-0114",
            3,
            0,
        )
        ids["multi_offer"] = cand(
            "Daniel Park",
            "daniel.park@example.com",
            "555-0115",
            1,
            2,
            screening=iso(ANCHOR - timedelta(days=22)),
            offered=iso(ANCHOR - timedelta(days=7)),
            offered_flag=1,
        )

        cand("Ivy Thompson", "ivy.t@example.com", "555-0116", 2, 0)
        cand(
            "Henry Wu",
            "henry.w@example.com",
            "555-0117",
            3,
            1,
            screening=iso(ANCHOR - timedelta(days=1)),
        )
        cand(
            "Zoe Martinez",
            "zoe.m@example.com",
            "555-0118",
            1,
            2,
            screening=iso(ANCHOR - timedelta(days=12)),
            offered=iso(ANCHOR - timedelta(days=6)),
            offered_flag=1,
        )
        cand(
            "Paul Becker",
            "paul.b@example.com",
            "555-0119",
            2,
            3,
            screening=iso(ANCHOR - timedelta(days=30)),
            offered=iso(ANCHOR - timedelta(days=12)),
            hired=iso(ANCHOR - timedelta(days=10)),
            offered_flag=1,
            hired_flag=1,
        )
        cand(
            "Nina Shah",
            "nina.sh@example.com",
            "555-0120",
            3,
            -1,
            screening=iso(ANCHOR - timedelta(days=11)),
            offered=iso(ANCHOR - timedelta(days=5)),
            rejected=iso(ANCHOR - timedelta(days=1)),
            offered_flag=1,
        )
        cand("Omar Hassan", "omar.h@example.com", "555-0121", 1, 0)
        cand(
            "Grace Lin",
            "grace.lin@example.com",
            "555-0122",
            2,
            1,
            screening=iso(LAST_MONDAY + timedelta(hours=14)),
        )
        cand(
            "Victor Santos",
            "victor.s@example.com",
            "555-0123",
            3,
            2,
            screening=iso(ANCHOR - timedelta(days=16)),
            offered=iso(ANCHOR - timedelta(days=4)),
            offered_flag=1,
        )

        # One resume blob per candidate (same file, real PDF bytes)
        resume_blob, resume_filename = load_seed_resume()
        all_ids = [r[0] for r in conn.execute("SELECT id FROM candidates").fetchall()]
        for cid in all_ids:
            conn.execute(
                """
                INSERT INTO resumes (candidate_id, file_blob, filename, uploaded_at)
                VALUES (?, ?, ?, ?)
                """,
                (cid, resume_blob, resume_filename, iso(ANCHOR)),
            )
        print(f"Attached resume '{resume_filename}' ({len(resume_blob)} bytes) to {len(all_ids)} candidates")

        conn.commit()
        print(f"Seeded database at {settings.database_path}")
        print(f"Anchor date (UTC): {iso(ANCHOR)}; last Monday: {iso(LAST_MONDAY)}")
        print("Named candidate ids:", ids)


if __name__ == "__main__":
    seed()
