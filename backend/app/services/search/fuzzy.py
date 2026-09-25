from __future__ import annotations

from ...config import settings
from ...db.database import get_connection
from ...models.schemas import STAGE_LABELS, SuggestItem


def _fetch_search_pool() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.current_stage,
                   p.title AS position_title, p.position_code
            FROM candidates c
            JOIN positions p ON p.id = c.position_id
            """
        ).fetchall()
    return [dict(r) for r in rows]


def _score(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100


def _name_match_score(query: str, full_name: str) -> float:
    """Best score vs full name, first name, or last name (either part can match)."""
    q = query.strip()
    if not q or not full_name.strip():
        return 0.0

    parts = full_name.split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    scores = [_score(q, full_name)]
    scores.append(_score(q, first))
    if last and last.lower() != first.lower():
        scores.append(_score(q, last))

    for token in q.split():
        if len(token) < 2:
            continue
        scores.append(_score(token, first))
        if last:
            scores.append(_score(token, last))
        scores.append(_score(token, full_name))

    print(first, _score(token, first), last, _score(token, last), full_name)

    return max(scores)


def fuzzy_suggest(query: str, limit: int = 8) -> list[SuggestItem]:
    q = query.strip()
    if not q:
        return []
    pool = _fetch_search_pool()
    scored: list[tuple[float, dict]] = []
    for row in pool:
        label = f"{row['name']} | {row['position_title']} | {row['position_code']}"
        score = max(
            _name_match_score(q, row["name"]),
            _score(q, label),
            _score(q, row["position_title"]),
            _score(q, row["position_code"]),
        )
        if score >= settings.fuzzy_min_score:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[SuggestItem] = []
    for score, row in scored[:limit]:
        stage = row["current_stage"]
        out.append(
            SuggestItem(
                id=row["id"],
                name=row["name"],
                current_stage=stage,
                stage_label=STAGE_LABELS.get(stage, str(stage)),
                position_title=row["position_title"],
                position_code=row["position_code"],
                score=float(score),
            )
        )
    return out


def empty_suggest_message(query: str) -> str:
    return (
        f"No close name or position matches for '{query}'. "
        "Press Search for a full question search."
    )
