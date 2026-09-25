from __future__ import annotations

from ...models.schemas import STAGE_LABELS
from ...utils.datetime_fmt import maybe_format_display_date

# Columns never shown to recruiters in search results
_HIDDEN_ALIASES = frozenset(
    {
        "position_id",
        "offered_flag",
        "hired_flag",
        "rejected_at",
        "entered_applied_at",
        "entered_screening_at",
        "entered_offered_at",
        "entered_hired_at",
        "file_blob",
        "filename",
        "uploaded_at",
        "candidate_id",
    }
)


def _norm_col(name: str) -> str:
    return name.split(".")[-1].lower()


def _find_col(columns: list[str], aliases: tuple[str, ...]) -> int | None:
    normalized = [_norm_col(c) for c in columns]
    for alias in aliases:
        for i, col in enumerate(normalized):
            if col == alias:
                return i
    return None


def _stage_label(value) -> str:
    if value is None:
        return "—"
    try:
        stage = int(value)
    except (TypeError, ValueError):
        return str(value)
    return STAGE_LABELS.get(stage, str(stage))


def _cell(row: list, idx: int | None):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _humanize_rows(columns: list[str], rows: list[list]) -> list[list]:
    stage_cols = {i for i, c in enumerate(columns) if c.lower() == "stage"}
    out: list[list] = []
    for row in rows:
        built = []
        for j, cell in enumerate(row):
            if j in stage_cols:
                built.append(cell)
            else:
                formatted = maybe_format_display_date(cell)
                built.append(formatted if formatted is not None else cell)
        out.append(built)
    return out


def _is_aggregate_result(columns: list[str], rows: list[list]) -> bool:
    if not rows:
        return False
    count_idx = _find_col(columns, ("cnt", "count", "total"))
    name_idx = _find_col(columns, ("name",))
    id_idx = _find_col(columns, ("id",))
    return count_idx is not None and name_idx is None and id_idx is None


def _format_aggregate(columns: list[str], rows: list[list]) -> tuple[list[str], list[list]]:
    stage_idx = _find_col(columns, ("current_stage", "stage"))
    count_idx = _find_col(columns, ("cnt", "count", "total"))
    out_cols: list[str] = []
    out_rows: list[list] = []

    if stage_idx is not None:
        out_cols.append("Stage")
    elif len(columns) == 1:
        out_cols.append(columns[0].replace("_", " ").title())
    else:
        out_cols = [c.replace("_", " ").title() for c in columns if _norm_col(c) not in _HIDDEN_ALIASES]
        if not out_cols:
            out_cols = ["Result"]
        return out_cols, [list(r) for r in rows]

    if count_idx is not None:
        out_cols.append("Count")

    for row in rows:
        out_row: list = []
        if stage_idx is not None:
            out_row.append(_stage_label(_cell(row, stage_idx)))
        if count_idx is not None:
            out_row.append(_cell(row, count_idx))
        out_rows.append(out_row)
    return out_cols, out_rows


def _format_candidate_rows(columns: list[str], rows: list[list]) -> tuple[list[str], list[list]]:
    id_idx = _find_col(columns, ("id",))
    name_idx = _find_col(columns, ("name",))
    email_idx = _find_col(columns, ("email",))
    phone_idx = _find_col(columns, ("phone",))
    stage_idx = _find_col(columns, ("current_stage", "stage"))
    pos_idx = _find_col(columns, ("position_title", "title", "position_code", "position"))

    if id_idx is None and name_idx is None:
        return _strip_noisy_columns(columns, rows)

    out_cols = ["ID", "Name", "Email", "Stage", "Position"]
    include_phone = phone_idx is not None and any(_cell(r, phone_idx) for r in rows)
    if include_phone:
        out_cols.insert(3, "Phone")

    out_rows: list[list] = []
    for row in rows:
        stage_val = _stage_label(_cell(row, stage_idx))
        position = _cell(row, pos_idx)
        if position is not None:
            position = str(position)

        out_row = [
            _cell(row, id_idx),
            _cell(row, name_idx) or "—",
            _cell(row, email_idx) or "—",
            stage_val,
            position or "—",
        ]
        if include_phone:
            out_row.insert(3, _cell(row, phone_idx) or "—")
        out_rows.append(out_row)

    return out_cols, out_rows


def _strip_noisy_columns(columns: list[str], rows: list[list]) -> tuple[list[str], list[list]]:
    keep_indices: list[int] = []
    out_cols: list[str] = []
    for i, col in enumerate(columns):
        key = _norm_col(col)
        if key in _HIDDEN_ALIASES or key.endswith("_at") or "blob" in key:
            continue
        if key == "current_stage":
            keep_indices.append(i)
            out_cols.append("Stage")
        elif key == "title" and "position" not in col.lower():
            keep_indices.append(i)
            out_cols.append("Position")
        else:
            keep_indices.append(i)
            out_cols.append(col.replace("_", " ").title())

    out_rows: list[list] = []
    for row in rows:
        built: list = []
        for j, i in enumerate(keep_indices):
            val = _cell(row, i)
            if out_cols[j] == "Stage":
                val = _stage_label(val)
            else:
                val = maybe_format_display_date(val) if val is not None else val
            built.append(val)
        out_rows.append(built)
    return out_cols, out_rows


def present_search_table(columns: list[str], rows: list[list]) -> tuple[list[str], list[list]]:
    """Reduce raw SQL output to recruiter-facing columns."""
    if not columns:
        return columns, rows
    if _is_aggregate_result(columns, rows):
        out_cols, out_rows = _format_aggregate(columns, rows)
    elif _find_col(columns, ("name",)) is not None or _find_col(columns, ("id",)) is not None:
        out_cols, out_rows = _format_candidate_rows(columns, rows)
    else:
        out_cols, out_rows = _strip_noisy_columns(columns, rows)
    return out_cols, _humanize_rows(out_cols, out_rows)
