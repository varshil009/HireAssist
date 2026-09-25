# HireAssist

Mini hiring pipeline web app: manage candidates across stages, immutable history, fuzzy name hints, and natural-language search powered by a guarded LLM→SQL prompt chain.

**Repository layout:** see [project_structure.md](project_structure.md).

## Prerequisites

- Python **3.9+** (3.9 recommended on Windows; 3.14 may lack pydantic wheels)
- Node.js 18+
- Google Gemini API key (for AI search; set `GEMINI_API` in `backend/.env`)

## Quick start

### 1. Database

Copy or build **`data/hireassist.db`** . The app uses this file as-is; no seed step is required.

```powershell
# Optional: regenerate data locally 
# backend\.venv\Scripts\python -m backend.scripts.seed
```

### 2. Backend

```powershell
cd backend
py -3.9 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# Edit backend/.env: GEMINI_API and optional GEMINI_MODEL
cd ..
python main.py
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 4. Eval (optional)

```powershell
# Validate expected result sets against reference SQL (no API key)
backend\.venv\Scripts\python eval\run_eval.py --offline

# Live NL→SQL eval (needs GEMINI_API; respects GEMINI_RPM / retries in backend/.env)
backend\.venv\Scripts\python eval\run_eval.py
```

**Eval metrics:** each query **passes** only on an **exact set match** of candidate IDs vs `expected_candidate_ids` in `eval/queries.json` (plus optional `expected_message_substring`). The summary **query accuracy** is passed/total. Per-query **set precision, recall, and F1** are printed for analysis but do not change pass/fail.

## Architecture summary

- **SQLite** stores positions, candidates (with `offered_flag` / `hired_flag`), append-only `stage_events`, and resume blobs.
- **FastAPI** exposes pipeline CRUD, resume upload, fuzzy suggest, and AI search.
- **Search:** realtime fuzzy matches while typing; **Search** runs a **two-attempt** Gemini prompt chain that generates read-only SQL. Second failure returns a fixed user message (no third attempt).
- **React + Tailwind** Kanban board and search UI.

Detailed diagram and module map: [project_structure.md](project_structure.md).  
PDF overview: [docs/HireAssist-Architecture.pdf](docs/HireAssist-Architecture.pdf).

## Decisions and trade-offs

| Decision | Why |
|----------|-----|
| Screening includes interview | Matches assignment flow in fewer columns; documented deviation. |
| Explicit `offered_flag` / `hired_flag` | Lets NL queries like “offered but not hired” map to SQL without inferring from stage alone. |
| No LangGraph | Simpler two-prompt chain with predictable retry and failure copy. |
| Fuzzy suggest without AI | Fast typo-friendly hints; AI only on explicit Search. |
| Append-only `stage_events` | Satisfies immutable audit trail requirement. |
| Python 3.9 venv | Reliable wheels on Windows without Rust/MSVC build chain. |

### Where we disagreed with AI

Initial suggestion was **always-on LangGraph** with up to three SQL retries. We replaced it with a **fixed two-try prompt chain** and **hardcoded failure text** so empty/error UX and eval boundaries stay predictable.

## With more time

- Role-based auth and multi-recruiter tenancy
- FTS5 or trigram index for name search at scale
- Streaming LLM responses and query explanation UI
- Drag-free bulk actions and email notifications
- CI running `eval/run_eval.py --offline` plus scheduled live eval

## AI chat logs

Planning and implementation notes: [docs/ai_chat_logs.md](docs/ai_chat_logs.md).

## Assignment deliverables

- GitHub repo (this repository)
- [docs/HireAssist-Architecture.pdf](docs/HireAssist-Architecture.pdf) — architecture summary + repo link
- README (this file) — run instructions, decisions, future work
