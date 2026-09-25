"""
Run NL search eval against seeded DB.

Usage (from repo root):
  backend\\.venv\\Scripts\\python eval\\run_eval.py           # live AI if GEMINI_API set in backend/.env
  backend\\.venv\\Scripts\\python eval\\run_eval.py --offline  # validate reference_sql + expected ids only

Live mode calls POST /search logic via run_ai_search and compares candidate id sets extracted from result tables.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.db.database import init_db  # noqa: E402
from app.services.search.ai_chain import run_ai_search  # noqa: E402
from app.services.search.sql_guard import execute_readonly_query  # noqa: E402


def load_queries() -> list[dict]:
    path = Path(__file__).parent / "queries.json"
    return json.loads(path.read_text(encoding="utf-8"))


def extract_candidate_ids(columns: list[str], rows: list[list]) -> list[int]:
    if not columns or not rows:
        return []
    lower = [c.lower() for c in columns]
    idx = None
    for key in ("id", "candidate_id", "c.id"):
        if key in lower:
            idx = lower.index(key)
            break
    if idx is None:
        for i, name in enumerate(lower):
            if name == "id" or name.endswith(".id") or name == "candidate_id":
                idx = i
                break
    if idx is None:
        return []
    ids: list[int] = []
    for row in rows:
        try:
            ids.append(int(row[idx]))
        except (TypeError, ValueError, IndexError):
            continue
    return sorted(set(ids))


def ids_from_reference_sql(sql: str | None) -> list[int]:
    if not sql:
        return []
    columns, rows = execute_readonly_query(sql)
    if "count" in " ".join(columns).lower():
        return []
    return extract_candidate_ids(columns, rows)


def run_offline(queries: list[dict]) -> int:
    failures = 0
    for q in queries:
        ref = q.get("reference_sql")
        expected = sorted(q.get("expected_candidate_ids") or [])
        if ref:
            got = ids_from_reference_sql(ref)
            if got != expected:
                print(f"FAIL {q['id']} reference mismatch expected={expected} got={got}")
                failures += 1
            else:
                print(f"OK   {q['id']} reference ids")
        else:
            print(f"SKIP {q['id']} no reference_sql")
    return failures


def run_live(queries: list[dict]) -> int:
    failures = 0
    for q in queries:
        nl = q["natural_language"]
        expected = sorted(q.get("expected_candidate_ids") or [])
        sub = q.get("expected_message_substring")
        resp = run_ai_search(nl)
        got = extract_candidate_ids(resp.columns, resp.rows)
        if sub:
            if sub.lower() not in resp.message.lower():
                print(f"FAIL {q['id']} message expected substring '{sub}' in '{resp.message}'")
                failures += 1
            elif expected and got != expected:
                print(f"FAIL {q['id']} ids expected={expected} got={got}")
                failures += 1
            else:
                print(f"OK   {q['id']} message+ids")
            continue
        if got != expected:
            print(f"FAIL {q['id']} expected={expected} got={got} ok={resp.ok}")
            failures += 1
        else:
            print(f"OK   {q['id']}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Validate reference SQL only")
    args = parser.parse_args()
    init_db()
    queries = load_queries()
    if args.offline:
        failed = run_offline(queries)
    else:
        if not settings.gemini_api:
            print("GEMINI_API not set in backend/.env; running --offline reference validation instead.")
            failed = run_offline(queries)
        else:
            failed = run_live(queries)
    print(f"\n{len(queries) - failed}/{len(queries)} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
