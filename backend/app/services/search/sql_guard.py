from __future__ import annotations

import re

from ...config import settings

ALLOWED_TABLES = frozenset({"candidates", "positions", "resumes", "stage_events"})

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


class SQLGuardError(Exception):
    pass


def validate_select_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise SQLGuardError("Empty SQL")
    if ";" in cleaned:
        raise SQLGuardError("Multiple statements are not allowed")
    upper = cleaned.upper()
    if not upper.startswith("SELECT"):
        raise SQLGuardError("Only SELECT queries are allowed")
    if FORBIDDEN.search(cleaned):
        raise SQLGuardError("Forbidden SQL keyword detected")
    if "LIMIT" not in upper:
        cleaned = f"{cleaned} LIMIT {settings.sql_row_limit}"
    for match in re.finditer(r"\b(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", cleaned, re.IGNORECASE):
        table = match.group(2).lower()
        if table not in ALLOWED_TABLES:
            raise SQLGuardError(f"Table '{table}' is not allowed")
    return cleaned


def execute_readonly_query(sql: str) -> tuple[list[str], list[list]]:
    from ...db.database import get_connection

    safe_sql = validate_select_sql(sql)
    with get_connection(read_only=True) as conn:
        cur = conn.execute(safe_sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
    return columns, rows
