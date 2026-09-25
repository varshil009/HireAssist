from __future__ import annotations

import json
import logging
import re

from ...config import settings
from ...models.schemas import SearchResponse, SuggestItem
from .fuzzy import fuzzy_suggest
from .search_display import present_search_table
from .sql_guard import SQLGuardError, execute_readonly_query

logger = logging.getLogger(__name__)

HARD_FAIL_MESSAGE = (
    "We couldn't run a safe search for your question. "
    "Try rephrasing (e.g. name, stage, or 'offered but not hired')."
)

DATETIME_RULES = """
Relative dates use SQLite datetime('now') (assume mock data is centered around September 2026).

Monday 00:00:00 of the current week (%w: 0=Sun … 6=Sat):
  datetime('now', 'start of day', '-' || ((CAST(strftime('%w', 'now') AS INTEGER) + 6) % 7) || ' days')

"Since Monday" / "since this Monday" (on or after that instant):
  datetime(c.entered_screening_at) >= datetime('now', 'start of day', '-' || ((CAST(strftime('%w', 'now') AS INTEGER) + 6) % 7) || ' days')
  (Use entered_offered_at, entered_applied_at, or stage_events.occurred_at when the question targets another transition.)

Any weekday "since {day}" — target T (Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6):
  datetime(column) >= datetime('now', 'start of day', '-' || ((CAST(strftime('%w', 'now') AS INTEGER) - T + 7) % 7) || ' days')

Stuck in screening more than one week (still in screening; screening includes interview):
  c.current_stage = 1 AND datetime(c.entered_screening_at) <= datetime('now', '-7 days')

More than N days in a stage: datetime(entered_*_at) <= datetime('now', '-' || N || ' days') with appropriate current_stage filter.

Compare timestamps with datetime(...) wrappers when using modifiers on 'now'.
"""

SCHEMA_PROMPT = (
    """
SQLite schema for hiring pipeline:

positions(id, position_code UNIQUE, title)

candidates(
  id, name, email, phone, position_id -> positions.id,
  current_stage INTEGER: -1=rejected, 0=applied, 1=screening (includes interview), 2=offered, 3=hired,
  rejected_at, offered_flag 0/1 (set when reached offer, never cleared),
  hired_flag 0/1 (set when hired, never cleared),
  entered_applied_at, entered_screening_at, entered_offered_at, entered_hired_at
)

stage_events(id, candidate_id, from_stage, to_stage, occurred_at) — immutable audit

resumes(id, candidate_id UNIQUE, file_blob, filename, uploaded_at)

Offered but not hired: offered_flag = 1 AND hired_flag = 0
Everyone except rejected: current_stage != -1
"""
    + DATETIME_RULES
    + """
Rules: output ONE SQLite SELECT only. Join positions when filtering by title or position_code.
Always include LIMIT 500.
Prefer selecting: c.id, c.name, c.email, c.phone, c.current_stage, p.title AS position_title (join positions p).
Return only the SQL, no markdown fences.
"""
)


def _extract_sql(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text


def _call_llm(system: str, user: str) -> str:
    if not settings.gemini_api:
        raise RuntimeError("GEMINI_API is not configured in backend/.env")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api)

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
        ),
    )
    return (response.text or "").strip()


def _format_rows_message(query: str, columns: list[str], rows: list[list]) -> str:
    if not settings.gemini_api:
        return f"Found {len(rows)} result(s) for your question."
    try:
        preview = json.dumps({"columns": columns, "rows": rows[:5]}, default=str)[:3000]
        return _call_llm(
            "You are a recruiting assistant. Write one short friendly sentence summarizing results.",
            f"Question: {query}\nResults preview: {preview}\nRow count: {len(rows)}",
        )
    except Exception:
        return f"Found {len(rows)} result(s) for your question."


def _empty_result_message(query: str) -> str:
    if not settings.gemini_api:
        return f"No candidates match your question: {query}"
    try:
        return _call_llm(
            "Explain empty search results briefly and suggest rephrasing.",
            f"The recruiter asked: {query}\nThe SQL query returned zero rows.",
        )
    except Exception:
        return f"No candidates match your question: {query}"


def _nonsense_message(query: str) -> str:
    return (
        f"'{query}' doesn't map to our hiring data. "
        "Try asking about candidate names, stages (applied, screening, offered, hired), "
        "positions, or time-based filters."
    )


def run_ai_search(query: str) -> SearchResponse:
    q = query.strip()
    fuzzy = fuzzy_suggest(q, limit=5) if len(q) <= 40 else []

    if not settings.gemini_api:
        return SearchResponse(
            ok=False,
            message="AI search requires GEMINI_API. Configure it in backend/.env",
            query=q,
            columns=[],
            rows=[],
            fuzzy_suggestions=fuzzy,
        )

    system = "You translate recruiter questions into SQLite SELECT queries." + SCHEMA_PROMPT
    user1 = f"Recruiter question: {q}"
    last_error: str | None = None
    sql_attempts: list[str] = []

    for attempt in range(2):
        try:
            if attempt == 0:
                raw = _call_llm(system, user1)
            else:
                raw = _call_llm(
                    system,
                    f"{user1}\n\nPrevious SQL:\n{sql_attempts[-1]}\n\nError:\n{last_error}\n\nFix the SQL only.",
                )
            sql = _extract_sql(raw)
            sql_attempts.append(sql)
            columns, rows = execute_readonly_query(sql)
            serializable = [[cell if cell is not None else None for cell in row] for row in rows]
            display_columns, display_rows = present_search_table(columns, serializable)
            if not rows:
                return SearchResponse(
                    ok=True,
                    message=_empty_result_message(q),
                    query=q,
                    columns=display_columns,
                    rows=display_rows,
                    fuzzy_suggestions=fuzzy,
                )
            return SearchResponse(
                ok=True,
                message=_format_rows_message(q, display_columns, display_rows),
                query=q,
                columns=display_columns,
                rows=display_rows,
                fuzzy_suggestions=fuzzy,
            )
        except SQLGuardError as e:
            last_error = str(e)
            logger.warning("SQL guard rejected query: %s", last_error)
        except Exception as e:
            last_error = str(e)
            logger.exception("Search SQL execution failed")

    msg = HARD_FAIL_MESSAGE
    if len(q.split()) <= 3 and not fuzzy:
        msg = _nonsense_message(q)

    return SearchResponse(
        ok=False,
        message=msg,
        query=q,
        columns=[],
        rows=[],
        fuzzy_suggestions=fuzzy,
    )
