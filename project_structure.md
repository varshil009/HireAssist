# HireAssist — project structure

This document describes the repository layout, module responsibilities, and how requests flow through the system. See [README.md](README.md) for setup and run instructions.

## Top-level tree

```
HireAssist/
├── main.py                  # Start API from repo root (python main.py)
├── backend/                 # FastAPI application
│   ├── app/
│   ├── scripts/seed.py      # Optional: regenerate hireassist.db locally (not used in eval)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # React + Vite + Tailwind UI
├── data/                    # hireassist.db (shipped for evaluators; see data/README.md)
│   └── README.md
├── eval/                    # NL query eval set + runner
├── docs/                    # Architecture PDF, AI chat logs
├── project_structure.md     # This file
└── README.md
```

## Backend (`backend/app`)

| Path | Role |
|------|------|
| [main.py](backend/app/main.py) | FastAPI app, CORS, router registration, DB init on startup |
| [config.py](backend/app/config.py) | Settings from `backend/.env` only: DB path, `GEMINI_API`, `GEMINI_MODEL`, fuzzy threshold |
| [db/database.py](backend/app/db/database.py) | SQLite schema DDL, read/write and read-only connections |
| [models/schemas.py](backend/app/models/schemas.py) | Pydantic request/response models |
| [services/pipeline.py](backend/app/services/pipeline.py) | **Only place** that mutates stages, flags, timestamps, and `stage_events` |
| [services/search/fuzzy.py](backend/app/services/search/fuzzy.py) | Realtime fuzzy suggestions (difflib scoring) |
| [services/search/sql_guard.py](backend/app/services/search/sql_guard.py) | SELECT-only validation, table allowlist, LIMIT injection |
| [services/search/ai_chain.py](backend/app/services/search/ai_chain.py) | Two-try LLM SQL prompt chain + user messaging |
| [routers/pipeline.py](backend/app/routers/pipeline.py) | `GET /api/pipeline`, `POST /api/pipeline/candidates` |
| [routers/candidates.py](backend/app/routers/candidates.py) | Detail, timeline, advance, reject, resume upload/download |
| [routers/positions.py](backend/app/routers/positions.py) | `GET /api/positions` |
| [routers/search.py](backend/app/routers/search.py) | `GET /api/search/suggest`, `POST /api/search` |

### Pipeline rules (enforced in `pipeline.py`)

- Stages: `-1` rejected, `0` applied, `1` screening, `2` offered, `3` hired.
- Advance: `0→1→2→3` only; no skip or reverse.
- Reject from `0`, `1`, or `2` → `-1`; set `rejected_at` once.
- On first entry to offered: `offered_flag = 1`. On hire: `hired_flag = 1`. Flags are never cleared.
- Every transition appends an immutable row to `stage_events`.

### Database tables

- **positions** — `position_code`, `title` (mock has ≥3 openings).
- **candidates** — profile, `current_stage`, flags, `entered_*_at`, `rejected_at`.
- **stage_events** — append-only audit trail.
- **resumes** — one blob per candidate (replace on upload). Downloads use `{CandidateName}_RESUME.pdf`.

## Frontend (`frontend/src`)

| Path | Role |
|------|------|
| [main.tsx](frontend/src/main.tsx) | React entry |
| [App.tsx](frontend/src/App.tsx) | Pipeline board, search UI, candidate modal |
| [api.ts](frontend/src/api.ts) | Fetch wrappers for backend API |

### UI behaviour

- Kanban columns by stage (including Rejected).
- Search input debounces **fuzzy suggestions** via `/api/search/suggest`.
- **Search** button calls `/api/search` (AI SQL chain).
- Candidate modal: timeline, advance/reject, resume upload/view.

Vite dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`.

## Eval (`eval/`)

| Path | Role |
|------|------|
| [queries.json](eval/queries.json) | 20 natural-language questions + expected candidate id sets |
| [run_eval.py](eval/run_eval.py) | Live AI eval (needs `GEMINI_API` in `backend/.env`) or `--offline` reference SQL check |
| [print_reference.py](eval/print_reference.py) | Helper to print id sets from seed data |

Eval compares **sorted candidate id sets** extracted from result tables (column named `id` or `candidate_id`).

## Request flows

### Advance candidate

```
Browser → POST /api/candidates/{id}/advance
       → pipeline.advance_candidate()
       → UPDATE candidates + INSERT stage_events
```

### Fuzzy suggest (while typing)

```
Browser → GET /api/search/suggest?q=
       → fuzzy.fuzzy_suggest()  (in-memory score over all candidates)
```

### AI search (Search button)

```
Browser → POST /api/search { query }
       → ai_chain.run_ai_search()
            → LLM generates SQL (attempt 1)
            → sql_guard + readonly execute
            → on error: LLM retry (attempt 2)
            → on 2nd failure: hardcoded message + optional fuzzy hints
       → JSON { message, columns, rows }
```

## Configuration

Copy [backend/.env.example](backend/.env.example) to `backend/.env` (settings are read **only** from this file, not from shell environment):

- `GEMINI_API` — required for AI search and live eval
- `GEMINI_MODEL` — optional (default `gemini-2.0-flash`)
- Database defaults to `data/hireassist.db` at repo root.

## Database file (`data/hireassist.db`)

Evaluation and normal runs use a **prebuilt SQLite file** at [data/hireassist.db](data/hireassist.db). See [data/README.md](data/README.md). Startup runs `CREATE IF NOT EXISTS` only; it does not reseed.

Optional local regeneration (developers):

```bash
backend\.venv\Scripts\python -m backend.scripts.seed
```

Mock timeline is anchored to **2026-09-25 UTC** when regenerating. Time-based eval SQL uses SQLite `datetime('now')`.
