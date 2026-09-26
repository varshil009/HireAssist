# HireAssist — project structure

Detailed map of the repository: layout, modules, API surface, data model, search pipeline, eval, and how requests flow. Setup and run steps live in [README.md](README.md). High-level workflow: [Workflow.drawio.png](Workflow.drawio.png) at the repo root.

---

## Top-level tree

```
HireAssist/
├── setup.py                     # One-time: venv, pip, npm install (python setup.py)
├── run.py                       # Start API + frontend (python run.py)
├── main.py                      # Backend only (used by run.py; or python main.py)
├── Workflow.drawio.png          # End-to-end workflow diagram (Draw.io export)
├── README.md
├── project_structure.md         # This file
├── .gitignore                   # Ignores *.db except data/hireassist.db; .env; venv/node_modules
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example             # GEMINI_API, GEMINI_MODEL, GEMINI_RPM, GEMINI_MAX_RETRIES
│   ├── .env                     # Local secrets (not committed); sole config source for Settings
│   ├── app/                     # FastAPI package (import path: app.* when backend/ on PYTHONPATH)
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   └── scripts/
│       ├── seed.py              # Optional: rebuild data/hireassist.db + mock timeline
│       └── check_db.py          # Dev REPL for ad-hoc SQL against the DB file
│
├── frontend/                    # React 18 + Vite + TypeScript + Tailwind
│   ├── index.html
│   ├── vite.config.ts           # Dev proxy /api and /health → :8000
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              # Kanban, search, candidate modal
│       ├── api.ts               # fetch helpers + resume blob open/download
│       ├── stageStyles.tsx      # Stage pill colors
│       └── index.css
│
├── data/
│   ├── README.md
│   └── hireassist.db            # Shipped SQLite (evaluators use as-is; resumes as BLOBs inside)
│
├── eval/
│   ├── queries.json             # 20 NL questions + expected ids (+ optional message checks)
│   ├── run_eval.py              # Live AI eval or --offline reference SQL validation
│   └── print_reference.py       # Dev helper: print id sets from reference SQL
│
└── docs/
    ├── ai_chat_logs.md          # Assignment AI collaboration log
    └── generate_architecture_pdf.py  # Optional PDF generator (if used locally)
```

---

## Runtime entry points

| Command | Purpose |
|---------|---------|
| `python setup.py` (repo root) | Create `backend/.venv`, `pip install -r requirements.txt`, `npm install` in `frontend/`, seed `.env` from example if missing. |
| `python run.py` (repo root) | After `backend\.venv\Scripts\activate` — start backend (`main.py`) and `npm run dev`; Ctrl+C stops both. |
| `python main.py` (repo root) | Backend API only (warnings-only logging, uvicorn :8000). |
| `uvicorn app.main:app --app-dir backend --reload` | Same app without `main.py` wrapper. |
| `npm run dev` in `frontend/` | Vite on `:5173`, proxies API to backend. |
| `backend\.venv\Scripts\python eval\run_eval.py [--offline]` | Eval harness (see [Eval](#eval-eval)). |

---

## Backend package (`backend/app`)

### Application shell

| File | Responsibility |
|------|----------------|
| [main.py](backend/app/main.py) | `FastAPI` app, CORS for localhost:5173, `init_db()` on startup, mounts routers under `/api`, `GET /health`. |
| [config.py](backend/app/config.py) | `Settings` via pydantic-settings: reads **only** [backend/.env](backend/.env) (not process env). Keys: `database_path` → `data/hireassist.db`, `GEMINI_API`, `GEMINI_MODEL`, `GEMINI_RPM` (default 15), `GEMINI_MAX_RETRIES` (default 3), `sql_row_limit` (500), `fuzzy_min_score` (60). |

### Database layer

| File | Responsibility |
|------|----------------|
| [db/database.py](backend/app/db/database.py) | DDL for four app tables + indexes; `init_db()` runs `CREATE IF NOT EXISTS`; `get_connection(read_only=)` uses SQLite URI mode `ro`/`rwc`. |

**Tables (application)**

| Table | Columns (high level) | Notes |
|-------|----------------------|--------|
| `positions` | `id`, `position_code` (unique), `title` | Job openings referenced by candidates. |
| `candidates` | identity, `position_id`, `current_stage`, flags, timestamps | Single source of truth for stage; see pipeline rules below. |
| `stage_events` | `candidate_id`, `from_stage`, `to_stage`, `occurred_at` | Append-only audit; SQLite triggers block UPDATE/DELETE. |
| `resumes` | `candidate_id` (unique), `file_blob`, `filename`, `uploaded_at` | One row per candidate; PDF bytes in DB. |

SQLite also maintains internal **`sqlite_sequence`** for `AUTOINCREMENT` ids.

**Candidate stage model**

| `current_stage` | Label | Meaning |
|-----------------|-------|---------|
| `-1` | Rejected | Terminal; set `rejected_at` once. |
| `0` | Applied | Entry stage. |
| `1` | Screening | Includes interview in product language. |
| `2` | Offered | Sets `offered_flag = 1` on first entry (sticky). |
| `3` | Hired | Sets `hired_flag = 1` (sticky). |

Timestamp columns: `entered_applied_at` (required), `entered_screening_at`, `entered_offered_at`, `entered_hired_at`. Eval time phrases assume mock data near **September 2026** and SQLite `datetime('now')` (see `DATETIME_RULES` in ai_chain).

### Domain service — pipeline

| File | Responsibility |
|------|----------------|
| [services/pipeline.py](backend/app/services/pipeline.py) | **Only module** that mutates candidates, flags, timestamps, and `stage_events`. |

**Rules enforced here**

- Advance: `0 → 1 → 2 → 3` only; no skip, no reverse.
- Reject from stages `0`, `1`, or `2` → `-1`; `rejected_at` set once.
- `offered_flag` / `hired_flag` set on first reach of offer/hire; never cleared (supports “offered but not hired”).
- Each transition inserts one `stage_events` row.
- Resume upsert replaces blob; download name from [utils/resume_names.py](backend/app/utils/resume_names.py) (`{Name}_RESUME.pdf`).
- Pipeline list computes `days_in_current_stage` for Kanban cards.

### Search stack

| File | Responsibility |
|------|----------------|
| [services/search/fuzzy.py](backend/app/services/search/fuzzy.py) | Loads all candidates + positions; scores query vs full name, **first name**, **last name**, position title/code (difflib `SequenceMatcher`); returns top matches ≥ `fuzzy_min_score`. |
| [services/search/sql_guard.py](backend/app/services/search/sql_guard.py) | SELECT-only, single statement, keyword blocklist, table allowlist (`candidates`, `positions`, `resumes`, `stage_events`); injects `LIMIT` if missing; executes on read-only connection. |
| [services/search/gemini_limits.py](backend/app/services/search/gemini_limits.py) | RPM spacing (`60/gemini_rpm` between calls), up to `gemini_max_retries` with exponential backoff on 429/quota/503-style errors. |
| [services/search/ai_chain.py](backend/app/services/search/ai_chain.py) | NL→SQL: system prompt includes schema + `DATETIME_RULES`; **2 attempts** (second includes prior SQL + error); optional LLM summary for non-empty/empty results; hard-coded failure message after 2 failures; attaches fuzzy hints on failure paths. |
| [services/search/search_display.py](backend/app/services/search/search_display.py) | Shapes raw SQL columns into recruiter table (ID, Name, Email, Stage, Position); hides internal flags/timestamps/blobs; humanizes dates via `datetime_fmt`. |

### HTTP routers (all prefixed `/api` in [main.py](backend/app/main.py))

| Router | Endpoints |
|--------|-----------|
| [routers/pipeline.py](backend/app/routers/pipeline.py) | `GET /pipeline` — Kanban columns in order Applied → … → Rejected; `POST /pipeline/candidates` — create candidate. |
| [routers/candidates.py](backend/app/routers/candidates.py) | `GET /candidates/{id}`, `GET /candidates/{id}/timeline`, `POST …/advance`, `POST …/reject`, `PUT …/resume` (upload), `GET …/resume` (inline PDF blob). |
| [routers/positions.py](backend/app/routers/positions.py) | `GET /positions` — list openings. |
| [routers/search.py](backend/app/routers/search.py) | `GET /search/suggest?q=` — fuzzy only; `POST /search` — body `{ query }` → `run_ai_search`. |

### Models and utilities

| File | Responsibility |
|------|----------------|
| [models/schemas.py](backend/app/models/schemas.py) | Pydantic DTOs: `CandidateOut`, `PipelineOut`, `SearchResponse`, `SuggestItem`, etc.; `STAGE_LABELS` map. |
| [utils/datetime_fmt.py](backend/app/utils/datetime_fmt.py) | ISO → display dates for UI/search tables. |
| [utils/resume_names.py](backend/app/utils/resume_names.py) | Sanitized `{Name}_RESUME.pdf` for `Content-Disposition`. |

### Optional scripts (`backend/scripts`)

| Script | Use |
|--------|-----|
| `seed.py` | Regenerate mock positions/candidates/events/resumes; anchor date 2026-09-25 UTC for relative eval queries. Not used in normal eval flow. |
| `check_db.py` | Interactive SQL shell for debugging. |

---

## Frontend (`frontend/src`)

| File | Responsibility |
|------|----------------|
| [main.tsx](frontend/src/main.tsx) | React root mount. |
| [App.tsx](frontend/src/App.tsx) | Pipeline board; debounced fuzzy dropdown on search input; **Search** / Enter → `POST /api/search`; results table with stage styling; candidate modal (timeline, advance/reject, resume upload/view). |
| [api.ts](frontend/src/api.ts) | Typed fetch wrappers; `openCandidateResume` fetches BLOB, opens tab or download with `{Name}_RESUME.pdf`. |
| [stageStyles.tsx](frontend/src/stageStyles.tsx) | Tailwind classes for stage badges. |
| [index.css](frontend/src/index.css) | Tailwind base + app styles. |

**Search UX (client)**

- Typing triggers `/api/search/suggest` (fuzzy); dropdown hidden after explicit search until query changes.
- Fuzzy is for quick name/position matches; full NL questions use AI search on button/Enter.
- API base URL is relative (`""`) so Vite proxy handles `/api`.

---

## Eval (`eval/`)

| Asset | Role |
|-------|------|
| [queries.json](eval/queries.json) | 20 natural-language cases: `natural_language`, `expected_candidate_ids`, optional `reference_sql`, optional `expected_message_substring`. |
| [run_eval.py](eval/run_eval.py) | **`--offline`:** run `reference_sql` through `sql_guard`, compare id sets. **Live:** `run_ai_search()` per query (needs `GEMINI_API`; inherits RPM/retry from backend settings). Logging: errors on fail, warnings for summary metrics. Exit code 1 if any failure. |
| [print_reference.py](eval/print_reference.py) | Prints expected id sets from reference SQL (dev). |

**Metrics**

- **Pass/fail:** exact sorted set match of candidate ids extracted from result columns (`id`, `candidate_id`, or `*.id`).
- **Query accuracy:** passed / total (reported at end).
- **Set precision / recall / F1:** logged per query for analysis; do not change pass/fail.
- Message-only cases: substring must appear in `SearchResponse.message`.

**Id extraction:** shared logic in `run_eval.py` → `extract_candidate_ids()`; live path uses displayed columns after `present_search_table` (still includes `ID` when present).

---

## Request and data flows

### 1. Load Kanban

```
Browser → GET /api/pipeline
       → pipeline.list_pipeline()
       → grouped candidates by current_stage
```

### 2. Fuzzy suggest (while typing)

```
Browser → GET /api/search/suggest?q=
       → fuzzy_suggest() over in-memory pool (all candidates)
       → SuggestOut { suggestions, empty_message? }
```

### 3. AI search (Search button / Enter)

```
Browser → POST /api/search { query }
       → run_ai_search()
            → (optional) fuzzy_suggest for short queries / failure hints
            → Gemini: SQL attempt 1 (generate_content_with_limits)
            → validate_select_sql + readonly execute
            → on guard/exec error: Gemini attempt 2 with error context
            → present_search_table()
            → optional Gemini: one-line result summary (or empty/nonsense messaging)
       → SearchResponse { ok, message, columns, rows, fuzzy_suggestions }
```

### 4. Advance / reject

```
Browser → POST /api/candidates/{id}/advance|reject
       → pipeline.advance_candidate | reject_candidate
       → UPDATE candidates + INSERT stage_events
```

### 5. Resume view

```
Browser → GET /api/candidates/{id}/resume
       → pipeline.get_resume() → BLOB + download filename
       → Response inline application/pdf
Frontend reconstructs blob URL / download as {Name}_RESUME.pdf
```

---

## Configuration reference

Copy [backend/.env.example](backend/.env.example) → `backend/.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API` | (empty) | Required for AI search and live eval. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model id for `google.genai`. |
| `GEMINI_RPM` | `15` | Min seconds between calls ≈ `60/RPM`. |
| `GEMINI_MAX_RETRIES` | `3` | Retries per Gemini call on transient errors. |

Database path is fixed in code to repo `data/hireassist.db` unless overridden in settings class default (env does not expose `DATABASE_PATH` in current `.env.example`).

---

## Dependencies (summary)

**Backend** ([requirements.txt](backend/requirements.txt)): FastAPI, uvicorn, pydantic-settings, google-genai, email-validator, etc.

**Frontend** (`package.json`): React, Vite, TypeScript, Tailwind.

---

## Related docs

| Document | Content |
|----------|---------|
| [README.md](README.md) | Quick start, decisions, trade-offs |
| [Workflow.drawio.png](Workflow.drawio.png) | Visual workflow |
| [data/README.md](data/README.md) | DB file placement and BLOB resumes |
| [docs/ai_chat_logs.md](docs/ai_chat_logs.md) | AI-assisted development log |
