from __future__ import annotations

from datetime import datetime, timezone

from ..db.database import get_connection
from ..models.schemas import STAGE_LABELS, CandidateOut, StageEventOut

TERMINAL_STAGES = {-1, 3}
NEXT_STAGE = {0: 1, 1: 2, 2: 3}
REJECTABLE_FROM = {0, 1, 2}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _days_in_stage(entered_at: str | None) -> float | None:
    if not entered_at:
        return None
    start = datetime.fromisoformat(entered_at.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - start
    return round(delta.total_seconds() / 86400, 2)


def _entered_field_for_stage(stage: int) -> str | None:
    return {
        0: "entered_applied_at",
        1: "entered_screening_at",
        2: "entered_offered_at",
        3: "entered_hired_at",
    }.get(stage)


def _current_stage_entered_at(row: dict, stage: int) -> str | None:
    field = _entered_field_for_stage(stage)
    if not field:
        return None
    return row.get(field)


def row_to_candidate(row) -> CandidateOut:
    d = dict(row)
    stage = d["current_stage"]
    entered = _current_stage_entered_at(d, stage)
    return CandidateOut(
        id=d["id"],
        name=d["name"],
        email=d["email"],
        phone=d.get("phone"),
        position_id=d["position_id"],
        position_code=d.get("position_code"),
        position_title=d.get("position_title"),
        current_stage=stage,
        stage_label=STAGE_LABELS.get(stage, str(stage)),
        rejected_at=d.get("rejected_at"),
        offered_flag=d["offered_flag"],
        hired_flag=d["hired_flag"],
        entered_applied_at=d["entered_applied_at"],
        entered_screening_at=d.get("entered_screening_at"),
        entered_offered_at=d.get("entered_offered_at"),
        entered_hired_at=d.get("entered_hired_at"),
        days_in_current_stage=_days_in_stage(entered) if stage >= 0 else None,
    )


CANDIDATE_SELECT = """
SELECT c.*, p.position_code, p.title AS position_title
FROM candidates c
JOIN positions p ON p.id = c.position_id
"""


def list_pipeline() -> dict[int, list[CandidateOut]]:
    columns: dict[int, list[CandidateOut]] = {0: [], 1: [], 2: [], 3: [], -1: []}
    with get_connection() as conn:
        rows = conn.execute(
            CANDIDATE_SELECT + " ORDER BY c.current_stage, c.name"
        ).fetchall()
    for row in rows:
        cand = row_to_candidate(row)
        columns.setdefault(cand.current_stage, []).append(cand)
    return columns


def get_candidate(candidate_id: int) -> CandidateOut | None:
    with get_connection() as conn:
        row = conn.execute(
            CANDIDATE_SELECT + " WHERE c.id = ?",
            (candidate_id,),
        ).fetchone()
    return row_to_candidate(row) if row else None


def create_candidate(name: str, email: str, phone: str | None, position_id: int) -> CandidateOut:
    now = _utc_now_iso()
    with get_connection() as conn:
        pos = conn.execute("SELECT id FROM positions WHERE id = ?", (position_id,)).fetchone()
        if not pos:
            raise ValueError("Invalid position_id")
        cur = conn.execute(
            """
            INSERT INTO candidates (
                name, email, phone, position_id, current_stage,
                entered_applied_at
            ) VALUES (?, ?, ?, ?, 0, ?)
            """,
            (name, email, phone, position_id, now),
        )
        cid = cur.lastrowid
        conn.execute(
            """
            INSERT INTO stage_events (candidate_id, from_stage, to_stage, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (cid, -99, 0, now),
        )
    created = get_candidate(cid)
    assert created
    return created


def get_timeline(candidate_id: int) -> list[StageEventOut]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM stage_events
            WHERE candidate_id = ?
            ORDER BY occurred_at ASC, id ASC
            """,
            (candidate_id,),
        ).fetchall()
    out: list[StageEventOut] = []
    for row in rows:
        fs, ts = row["from_stage"], row["to_stage"]
        out.append(
            StageEventOut(
                id=row["id"],
                candidate_id=row["candidate_id"],
                from_stage=fs,
                to_stage=ts,
                from_label="Start" if fs == -99 else STAGE_LABELS.get(fs, str(fs)),
                to_label=STAGE_LABELS.get(ts, str(ts)),
                occurred_at=row["occurred_at"],
            )
        )
    return out


def advance_candidate(candidate_id: int) -> CandidateOut:
    now = _utc_now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if not row:
            raise ValueError("Candidate not found")
        stage = row["current_stage"]
        if stage in TERMINAL_STAGES:
            raise ValueError("Cannot advance from terminal stage")
        if stage not in NEXT_STAGE:
            raise ValueError("Invalid stage for advance")
        new_stage = NEXT_STAGE[stage]
        updates = ["current_stage = ?"]
        params: list = [new_stage]
        field = _entered_field_for_stage(new_stage)
        if field:
            updates.append(f"{field} = COALESCE({field}, ?)")
            params.append(now)
        if new_stage == 2:
            updates.append("offered_flag = 1")
        if new_stage == 3:
            updates.append("hired_flag = 1")
        params.append(candidate_id)
        conn.execute(
            f"UPDATE candidates SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.execute(
            """
            INSERT INTO stage_events (candidate_id, from_stage, to_stage, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (candidate_id, stage, new_stage, now),
        )
    updated = get_candidate(candidate_id)
    assert updated
    return updated


def reject_candidate(candidate_id: int) -> CandidateOut:
    now = _utc_now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if not row:
            raise ValueError("Candidate not found")
        stage = row["current_stage"]
        if stage in TERMINAL_STAGES:
            raise ValueError("Cannot reject from terminal stage")
        if stage not in REJECTABLE_FROM:
            raise ValueError("Cannot reject from this stage")
        if row["rejected_at"]:
            raise ValueError("Already rejected")
        conn.execute(
            """
            UPDATE candidates
            SET current_stage = -1, rejected_at = ?
            WHERE id = ?
            """,
            (now, candidate_id),
        )
        conn.execute(
            """
            INSERT INTO stage_events (candidate_id, from_stage, to_stage, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (candidate_id, stage, -1, now),
        )
    updated = get_candidate(candidate_id)
    assert updated
    return updated


def upsert_resume(candidate_id: int, file_blob: bytes, filename: str | None) -> None:
    now = _utc_now_iso()
    with get_connection() as conn:
        cand = conn.execute("SELECT id FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not cand:
            raise ValueError("Candidate not found")
        existing = conn.execute(
            "SELECT id FROM resumes WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE resumes SET file_blob = ?, filename = ?, uploaded_at = ?
                WHERE candidate_id = ?
                """,
                (file_blob, filename, now, candidate_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO resumes (candidate_id, file_blob, filename, uploaded_at)
                VALUES (?, ?, ?, ?)
                """,
                (candidate_id, file_blob, filename, now),
            )


def get_resume(candidate_id: int) -> tuple[bytes, str | None] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT file_blob, filename FROM resumes WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
    if not row:
        return None
    return row["file_blob"], row["filename"]
