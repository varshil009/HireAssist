# Project database design discussion
_Exported on 9/26/2026 at 03:00:51 GMT+5:30 from Cursor (3.15.6)_

---

**User**

c:\Users\Varshil\Downloads\instructions.md 

this is the aim of project, here is my plan, discuss the pros and cons with it, 

for backend, I am thinking of using sqlite as database with a 3 tables, candidates, resumes, positions

## for candidates table;

the columns would be 

1. id [would serve as a unique application id and also for saving/searching resume ],

-> personal info:
    2. name, 3. email, 4. phone
-> application related info:
    5. application_id, 6. current_stage (uses integers, 0 -> applied, 1-> screening, 2 -> offered, 3 -> hired)
-> hiring flow info:
    7. stage_i_timestamp [for 0 to 3, we record when the the candidate proceeds for next stage, which can be used for showing application timeline, as well as sql queries to find time spent for application for every stage]

### resumes table;
-> 1. id : a unique resume id [ unique to candidate, which means no version control over resume, user adds it or replaces it, we replace it]
-> 2. application_id : a unique application id corresponding to candidates column, which will be used for search and retrieval of resume from database
-> 3. bin : a blob type column containing binary information of resume

### openings table, 
-> 1. id 
-> 2. pos_id, a unique id pointing to position only
-> 3. pos_title, a position title, can be non unique

now this was database, 

lets talk about python backend, 

we will use FastAPI for python backend, and will add langgraph to it for creating nodes, since this will allow the llm to access database [with restriction but lets keep details later]

langgraph will have 3 nodes, node_llm, which will take query and make sql query, 
return in tool request json format, now the code will take query and execute it, and give back the dimesions of result table to node_llm2, which will be a cyclical node, here, when llm sees no rows returned or an error from search, it can either respond to client with a message whether the requested query doesnt exist or retry if it sees a querieng error, most allowed 3.  when table is there returned by db, the llms will generate intro or corresponding task accordingly and then send its response along with the table retreived from db to frontend; and table will be rendered there. 

and for frontend, take control of it according to backend apis that we will create along the backend, we will use react here for fronted and use tailwind css for ease
i will handover 2 tasks to you or other LLM if you , 
1. creating a mock dataset for sqlite, 
2. creating 20 similar queries along with its actual answer queries, so that we can eval

---

**Cursor**

Reviewing the project instructions and codebase so we can evaluate your plan.


Noting a mismatch: the spec includes Interview, Offer, rejection, and an immutable audit trail—your schema uses four stages and `stage_i_timestamp`. Checking whether the repo has any existing docs.


Your plan omits Interview and rejection from the spec; that affects the schema and eval queries. Which direction should we take?


**Architecture alignment**

> **The assignment spec uses 5 forward stages (Applied → Screening → Interview → Offer → Hired) plus rejection, with an immutable audit trail. Your schema uses 4 stages (0–3, no Interview) and timestamp columns on the candidate row. Which should the implementation target?**
> - Match the spec (5 stages + rejected, append-only stage history table)
> - Keep your simplified 4-stage model and document the deviation in README
> - 5 stages + rejected in DB, but skip Interview in UI for now
>
> Answer: interview counts in screening, so skip that and add rejected as -1

> **Natural-language search must handle typos (e.g. "sharam" → Priya Sharma), ranking, and explain bad queries. Pure LLM-generated SQL in SQLite is flexible but weak on fuzzy rank. Preferred approach?**
> - Stay with LangGraph + LLM SQL (accept limitations; maybe FTS5/trigram helpers in schema)
> - Hybrid: deterministic pipeline APIs for board moves + LLM/SQL only for search, with guardrails
> - LLM outputs structured intent/filters; backend builds parameterized SQL (safer, easier eval)
>
> Answer: instead we can provide an AI/LLM functionality as toggle option for search, bydefault what user type would be a hardcoded sql query on name, position name / position id

Incorporating your clarifications: screening subsumes interview, `rejected = -1`, and default hardcoded search with an optional LLM toggle.


---

**User**

1. okay add offered but not hired integer there since it cannot be determined by llm, if there is an offered flag but not hired flag, 
2. keep a project_strcture.md file where you explain the structure in detail, 
3. yes add rejected timestamp
4. in mock data you gotta create atleast 3 openings, this will not be a single opening mock
5. do whatever you need in colunm naming part
6. i kept langgraph for fallback when error,, since llm will be fed the error and itwill generate the sql query accordingly, and present a reason to user, so instead of langgraph, we keep a conditioned prompt chain, when there seems to be an error on sql query llm will generate reponse accordingly, so i guess it automatically reduces down the query to 2 tries only, but what would you do when 2nd try fails, ? keep hardcoded response created for that, simiarility for fuzzy search, keep hardcoded fallback response using query of user, we will make fuzzy matching realtime,
so i guess instead of toggling, if there are fuzzy matching results we will presnt them and on clicking search, we will invoke full ai search, so no need of toggling

7. for eval set task, there should be one bucked we donot need evals for default search, all queries should be AI natural language only,



---

**Cursor**

Reading the plan file and updating it with your decisions.


Updating the plan with your schema flags, search flow (fuzzy + prompt chain), multi-opening mock data, eval scope, and `project_structure.md`.


Updated the plan with your seven points. Here is the distilled version, including **what happens when the second SQL try fails**.

### Locked-in changes

1. **`offered_flag` / `hired_flag`** on `candidates` (set by the pipeline, never cleared). “Offered but not hired” = `offered_flag = 1 AND hired_flag = 0` so the LLM does not have to infer it from stage alone.

2. **`project_structure.md`** at repo root — detailed tree, module roles, and request flows; README links to it.

3. **`rejected_at`** plus `current_stage = -1`.

4. **Mock data: ≥3 `positions`**, candidates spread across them.

5. **Canonical column names** in the plan (`position_code`, `entered_screening_at`, `file_blob`, etc.) — implementation follows that semantics.

6. **Search (no toggle, no LangGraph)**  
   - **Live:** `GET /search/suggest` → fuzzy on name / position.  
   - **No fuzzy hits:** hardcoded hint using the user’s query (press Search for full NL search).  
   - **Search button:** 2-step **prompt chain** (attempt 1 → on SQL/guard error, attempt 2 with error text).  
   - **After 2nd failure:** no third LLM SQL. Return a **fixed, friendly `message`**, empty table, and optionally **reuse fuzzy suggestions** so the user is not stuck. Log the real error server-side only.  
   - **Successful SQL but 0 rows:** LLM (or template) explains why — not the same as hard fail.

7. **Eval:** one bucket — **20 natural-language queries**, all through **`POST /search`**; no eval bucket for default/fuzzy suggest.

### Second-try failure (your question)

Use a **stable hardcoded response** (same copy every time for supportability), not another model call. Optionally append fuzzy matches when the query looks name-like. That keeps the UI honest (“we couldn’t safely answer this”) while still meeting the spec’s “don’t just show nothing” spirit.

Full detail is in the updated plan file. Say when you want to **execute** the plan and we can start scaffolding the repo.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing the HireAssist plan: starting with the database schema and FastAPI pipeline.


Fixing the seed script's extra candidates loop and running the seed.


Creating the frontend, eval set, and documentation.


HireAssist is implemented per the updated plan. Here is what you have and how to run it.

### Backend (`backend/`)
- **SQLite schema**: `positions`, `candidates` (stages `-1..3`, `rejected_at`, `offered_flag`, `hired_flag`, `entered_*_at`), `stage_events`, `resumes`
- **Pipeline service**: advance/reject rules, append-only audit, flag updates only in `pipeline.py`
- **Search**: `GET /api/search/suggest` (fuzzy), `POST /api/search` (2-try LLM SQL + `sql_guard` readonly SELECT)
- **APIs**: pipeline board, candidate detail/timeline, resume upload/download, positions list

### Frontend (`frontend/`)
- Kanban by stage (including Rejected)
- Candidate modal: history, days in stage, advance/reject, resume
- Search: live fuzzy suggestions; **Search** runs AI NL search and renders message + table

### Data & eval
- **Seed**: `python -m backend.scripts.seed` — 3 openings, 23 candidates, anchor **2025-09-24 UTC**
- **`eval/queries.json`**: 20 NL-only queries
- **`eval/run_eval.py --offline`**: 20/20 reference checks pass

### Docs
- [project_structure.md](project_structure.md)
- [README.md](README.md)
- [docs/HireAssist-Architecture.pdf](docs/HireAssist-Architecture.pdf) — update the GitHub URL in `docs/generate_architecture_pdf.py` before submit
- [docs/ai_chat_logs.md](docs/ai_chat_logs.md)

### Run locally

```powershell
cd "D:\AI Agents\naicos assignment\HireAssist\backend"
py -3.9 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # set OPENAI_API_KEY
cd ..
backend\.venv\Scripts\python -m backend.scripts.seed
cd backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Use **Python 3.9** for the backend venv on your machine (3.14 lacks pydantic wheels without MSVC). AI search needs `OPENAI_API_KEY` in `backend/.env`; fuzzy suggest and the pipeline work without it.

---

**User**

1. what stage_events for and also sqlite_sequence for, 
2. for 23 mock application we have 16 resumes only, 
3. use my resume from data that i just added and add it there as binary for each one

---

**Cursor**

Checking the database setup, seed logic, and resume files you added.


Updating the seed script to attach your PDF to every candidate and adjusting `.gitignore` so the resume can be tracked.


Fixing seed reset: stale `sqlite_sequence` was assigning position IDs 4–6 while candidates still referenced 1–3.


Here are direct answers to your three points, plus what changed in the repo.

### 1. `stage_events` and `sqlite_sequence`

**`stage_events`** is the **immutable audit trail** for the hiring pipeline. Each time a candidate moves (including the initial “start → Applied” on create), the app **appends** one row: `from_stage`, `to_stage`, `occurred_at`. That supports:

- Full **history** on the candidate detail screen (never edit old rows)
- Time-based search (“moved to screening since Monday”) via events or the `entered_*_at` columns

The **`entered_*_at` columns** on `candidates` are for convenience (e.g. “days in current stage”); **`stage_events`** is the record that history was never rewritten.

**`sqlite_sequence`** is **SQLite internal metadata**, not part of your app design. For tables defined with `AUTOINCREMENT`, SQLite keeps the **next ID** there. After you delete all rows but don’t reset that table, new `positions` rows can get ids **4, 5, 6** while seed data still uses `position_id` **1, 2, 3** → foreign key errors. The seed script now runs `DELETE FROM sqlite_sequence` on reset so ids start clean again.

---

### 2. Why 23 applications but only 16 resumes

The old seed logic was intentional: **~60% coverage** — it skipped any candidate whose `id % 3 == 0` (ids 3, 6, 9, 12, 15, 18, 21 → **7 skipped**, **16 resumes**). That matched the plan’s “~60% with resumes,” not a bug.

---

### 3. Your PDF for every candidate

Your file is at `data/VARSHIL_PRAJAPATI_CV25.pdf` (~147 KB). **`backend/scripts/seed.py`** now:

- Reads that file as **binary**
- Inserts it into **`resumes.file_blob`** for **all 23** candidates (same filename on each row)

Re-seed confirmed: **23 candidates, 23 resumes**, each blob **146769 bytes**.

`.gitignore` was adjusted so **`data/hireassist.db`** stays ignored but **`data/*.pdf`** can be committed for teammates.

Re-run after any reset:

```powershell
backend\.venv\Scripts\python -m backend.scripts.seed
```

---

**User**

fix relative imports so that i can run the main.py from root of HireAssist

---

**Cursor**

Fixing inconsistent imports: standardizing the `app` package on relative imports and adding a root `main.py` entry point.


Here’s what was fixed:

### Problem
`backend/app/main.py` used broken flat imports (`from db.database`, `from routers`), while other modules still used `from app....`. Running from the repo root didn’t put `backend` on `PYTHONPATH`, so imports failed.

### Solution
1. **`app` package** — Added `__init__.py` under `backend/app/` and subpackages.
2. **Relative imports** inside `app`:
   - `main.py` → `from .db.database`, `from .routers import ...`
   - Routers → `from ..models`, `from ..services`
   - `services/search/*` → `from ...config`, `from ...db`, etc.
3. **Root entrypoint** — [`main.py`](main.py) at the HireAssist root adds `backend/` to `sys.path` and runs uvicorn on `app.main:app`.
4. **Config** — Loads `.env` from `backend/.env` or repo root `.env` regardless of cwd.

### How to run (from `HireAssist/`)

```powershell
python main.py
```

Or:

```powershell
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Do **not** run `python backend/app/main.py` directly (that skips the path setup). Use root **`main.py`** or uvicorn with **`--app-dir backend`**.

Seed/eval scripts still use `from app....` with `sys.path` pointing at `backend/` — unchanged and still valid.

---

**User**

switch openai to gemini llm, use GEMINI_API and GEMINI_MODEL keys, load from .env file only

---

**Cursor**

Switching the LLM to Gemini with `GEMINI_API` and `GEMINI_MODEL`, loading settings only from `backend/.env`.


Switched AI search from OpenAI to **Google Gemini**. Summary of changes:

### Config ([`backend/app/config.py`](backend/app/config.py))
- **`GEMINI_API`** and **`GEMINI_MODEL`** (default `gemini-2.0-flash`) via Pydantic `validation_alias`
- Settings load **only** from [`backend/.env`](backend/.env) — `settings_customise_sources` uses dotenv + init kwargs, **not** process environment variables
- Removed repo-root `.env` and all OpenAI fields

### LLM calls ([`backend/app/services/search/ai_chain.py`](backend/app/services/search/ai_chain.py))
- Uses `google.generativeai` with `system_instruction` + `generate_content`
- Errors/messages refer to **`GEMINI_API`** in `backend/.env`

### Dependencies
- Replaced `openai` with **`google-generativeai==0.8.4`** in [`backend/requirements.txt`](backend/requirements.txt)

### Docs / eval
- Updated [`backend/.env.example`](backend/.env.example), README, `project_structure.md`, `eval/run_eval.py`, PDF generator text

### Your `backend/.env`

```env
GEMINI_API=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

Reinstall deps:

```powershell
cd backend
.venv\Scripts\pip install -r requirements.txt
```

---

**User**

for fuzzy matching, try putting score by splitting first name and last name, if score of any one is higher it should be considered

---

**Cursor**

Updating fuzzy scoring to compare against first and last name parts and removing a debug print.


Updated fuzzy matching in [`backend/app/services/search/fuzzy.py`](backend/app/services/search/fuzzy.py):

### `_name_match_score`
For each candidate name split into **first** (first token) and **last** (last token when there are multiple):
- Scores the query against **full name**, **first**, and **last**
- Also scores each **query token** (length ≥ 2) against first, last, and full name
- Uses **`max(...)`** so a strong match on either name part counts (e.g. typo `"sharam"` → `"Sharma"`)

The overall suggestion score is still the max of name score, combined label, position title, and position code.

Removed a leftover **`print`** debug line from that loop.

---

**User**

1. when user clicks on search the fuzzy matching results should disappear, 
2. the table returned from db should have a clickable row for more user information
3. while typing "enter" button should also trigger search click effect
4. make ui more attractive

---

**Cursor**

Implementing search UX improvements and a visual refresh in the frontend.


Here’s what changed in [`frontend/src/App.tsx`](frontend/src/App.tsx) and styling:

### 1. Fuzzy list hides on Search
- `showFuzzy` is set to `false` when **Search** or **Enter** runs; suggestions and the empty fuzzy message are cleared.
- Fuzzy UI only shows when `showFuzzy` is true (typing again after a search turns it back on).

### 2. Clickable search result rows
- `extractCandidateId()` finds an `id` / `candidate_id` column.
- Rows with a valid id are clickable (hover, keyboard Enter/Space) and open the same **CandidateDetail** modal as the board.

### 3. Enter triggers search
- Search input `onKeyDown` calls the shared `runSearch()` on **Enter** (same as the Search button).

### 4. UI refresh
- Page gradient, **DM Sans**, glass-style panels
- Gradient header and primary buttons
- Search area with focus rings and clearer result message styling
- Pipeline columns with colored top borders, counts, empty states
- Upgraded modal (backdrop blur, layout, file input styling)
- Search table with header hint, zebra rows, hover on clickable rows

Refresh the Vite dev server to see it live.

---

**User**

nice, but the table shown after search shows all columns from database, show only concerned info in table

---

**Cursor**

Checking how search results are built and what the LLM typically returns.


Adding backend normalization to show recruiter-friendly columns while preserving `id` for row clicks.


Search results are normalized on the **backend** before they reach the UI.

### New module: [`search_display.py`](backend/app/services/search/search_display.py)
After each successful SQL query, rows are mapped to recruiter-facing columns:

| Result type | Columns shown |
|-------------|----------------|
| **Candidate lists** | **ID**, **Name**, **Email**, **Phone** (only if present), **Stage** (label, not `-1…3`), **Position** |
| **Aggregates** (e.g. counts by stage) | **Stage**, **Count** |
| **Other** | Drops flags, timestamps, `position_id`, blobs, etc. |

`current_stage` is shown as Applied / Screening / Offered / Hired / Rejected. **ID** stays in the table so row clicks still open the candidate modal.

### Also
- [`ai_chain.py`](backend/app/services/search/ai_chain.py) uses `present_search_table()` for all successful searches.
- The Gemini schema hint now asks for `c.id, name, email, phone, current_stage, position_title` so raw SQL is already leaner.

Restart the API and run a search again — you should see the slim table instead of full DB columns.

---

**User**

good, now for the display timestamps should be in human readable formay, date  int, month in words and year int

---

**Cursor**

Adding shared date formatting and applying it across API responses and search results.


Timestamps are now shown as **`22 September 2025`** (day number, full month name, year).

### Shared helper — [`backend/app/utils/datetime_fmt.py`](backend/app/utils/datetime_fmt.py)
- `format_display_date()` — ISO/datetime → `"22 September 2025"`
- `maybe_format_display_date()` — only formats ISO-like strings; leaves other values as-is

### Where it’s applied
1. **Candidate API** ([`pipeline.py`](backend/app/services/pipeline.py)) — `entered_*_at`, `rejected_at` in responses (days-in-stage still computed from raw DB values internally).
2. **Stage history** — each `occurred_at` in the timeline is formatted.
3. **Search results table** ([`search_display.py`](backend/app/services/search/search_display.py)) — any ISO date cells in the result grid are humanized after column shaping.

Restart the API and refresh the UI to see formatted dates in search tables and candidate history.

---

**User**

now , add background colors like this, 
applied sky blue, 
screening yellow, 
offered light green
hired green with check mark emoji or ascii character
rejected red
not to names, but to stage name only
in tables displayed, in pipeline board, in fuzzy search results ,

remove Manage your pipeline and find candidates with smart search. and keep Find candidates with smart search only, bring hireassit ttile div to centre

---

**Cursor**

Adding shared stage pill styling and updating the header layout.


Here’s what changed:

### Stage colors ([`frontend/src/stageStyles.tsx`](frontend/src/stageStyles.tsx))
Shared **`StagePill`** — background only on the **stage label**, not candidate names:

| Stage | Style |
|--------|--------|
| Applied | Sky blue (`bg-sky-300`) |
| Screening | Yellow (`bg-yellow-300`) |
| Offered | Light green (`bg-lime-200`) |
| Hired | Green (`bg-green-600`) + **✓** |
| Rejected | Red (`bg-red-400`) |

Used on:
- **Search table** — `Stage` column cells  
- **Pipeline board** — column stage titles (count badge stays neutral)  
- **Fuzzy suggestions** — stage pill between name and position  
- **Candidate modal** — current stage + colored pills on history transitions  

### Header
- Centered **HireAssist** block  
- Subtitle is only: **“Find candidates with smart search.”**  
- Removed the “Recruiting workspace” chip and the longer subtitle  

Refresh the frontend to see the updates.

---

**User**

update the dataset, the years you have put are 2025 in most, so questions like who has been stuck in screening more than a week just gives all results, make data scentered around 25th september 2026, also for questions like who moved to interview since monday, use datetime, when user mentions since monday, its monday for current week, so update prompt in such a way that llm can do that, for example it can do WHERE 
  AND datetime(e.stage_i_timestamp) >= datetime(
      'now',
      '-' || ((strftime('%w', 'now') + 6) % 7) || ' days'
  ); to get the concerned info,
this can apply to any day, 



---

**Cursor**

Updating the seed data to center on 25 September 2026 and enhancing the AI schema prompt with relative SQLite datetime patterns.


Updating the seed anchor to September 2026, tuning screening dates, and expanding the LLM prompt with relative datetime patterns.


Here’s what was updated:

### Seed data ([`backend/scripts/seed.py`](backend/scripts/seed.py))
- **Anchor “today”:** **25 September 2026 UTC** (Monday of that week: **22 Sep 2026**).
- All `entered_*_at` / events are derived from that anchor.
- **Stuck in screening > 7 days:** only **Amit, Sara, James** (ids 2, 3, 4) — in screening with `entered_screening_at` more than 7 days before “now”.
- **Priya** and others stay in screening but entered within the last 7 days (not “stuck”).
- **Since Monday (screening):** Lina, Maya, Henry, Grace (ids 5, 13, 17, 22).
- **Offered since Monday:** only **Olivia** (id 11); Marcus/Victor offers moved **before** this Monday.
- Resume file: uses your PDF when present; otherwise a tiny placeholder so seed still runs.

Re-seed:

```powershell
backend\.venv\Scripts\python -m backend.scripts.seed
```

### LLM prompt ([`backend/app/services/search/ai_chain.py`](backend/app/services/search/ai_chain.py))
Added **`DATETIME_RULES`** for SQLite relative time, including:
- **Monday start of current week:**  
  `datetime('now', 'start of day', '-' || ((CAST(strftime('%w', 'now') AS INTEGER) + 6) % 7) || ' days')`
- **“Since Monday”** on `entered_screening_at` / `entered_offered_at` / `occurred_at`
- **Any weekday “since {day}”** with target `T` (Sun=0 … Sat=6)
- **Stuck in screening > 1 week:**  
  `current_stage = 1 AND datetime(entered_screening_at) <= datetime('now', '-7 days')`

### Eval ([`eval/queries.json`](eval/queries.json))
- q03, q04, q15 use **relative** `datetime('now', …)` SQL and natural wording like **“since Monday”** (no fixed 2025 dates).

**Note:** Relative queries use the machine’s **`datetime('now')`**. They match the mock data best when the system date is around **25 Sep 2026** (same as your assignment timeline). Offline eval passes on that timeline.

---

**User**

the fuzzy match results go away when i click the search but come back when results of sql comes, persist the flag that prevents fuzzy match to be displayed

---

**Cursor**

Fixing the effect that re-enables fuzzy when `showFuzzy` is set to `false` after Search (it was in the dependency array).


The bug came from the suggest `useEffect` depending on **`showFuzzy`**. After Search set `showFuzzy` to `false`, the effect ran again and immediately called **`setShowFuzzy(true)`** because the query was still at least 2 characters—so fuzzy results returned when the SQL request finished.

**Fix:** depend only on **`searchQ`**. Fuzzy is turned off in **`runSearch`** and stays off until the user **changes the input** (which re-runs the effect and sets `showFuzzy` back to `true`). Removed `!searchBusy` from `fuzzyOpen` so loading state doesn’t control fuzzy visibility; **`showFuzzy`** does.

---

**User**

why have you added 2 candidates that are offered and then rejected, remove them, do not touch other data, maybe make their rejected before offer

---

**Cursor**

Updating Elena Rossi and Nina Shah to reject from screening before offer, and adjusting eval expectations for q05 and q10.


Updated **Elena Rossi** (id 7) and **Nina Shah** (id 20) only:

- Both are still **rejected** (`current_stage = -1`).
- They now go **Applied → Screening → Rejected** (no offer step).
- **`offered_flag` stays 0** (no `entered_offered_at`).

Everyone else in the seed is unchanged.

Eval expectations were adjusted so they stay consistent:
- **q05** (offered but not hired): ids **7** and **20** removed → `[6, 11, 15, 18, 23]`
- **q10** (rejected after offer): now **empty** `[]`

Re-seed locally:

```powershell
backend\.venv\Scripts\python -m backend.scripts.seed
```

---

**User**

hey, since i have now removed my resume, 

so on view resume, fetch concerned application ids resume blob, and save that blob as pdf and download it or maybe open it in new tab just like you did with my resume file

---

**Cursor**

Implementing client-side fetch of the resume blob and opening it in a new tab (with download fallback).


**View resume** now loads the stored blob for that candidate id (application id) and opens it in the browser.

### Frontend ([`frontend/src/api.ts`](frontend/src/api.ts))
- **`openCandidateResume(candidateId)`** calls `GET /api/candidates/{id}/resume`
- Builds a **`Blob`** (defaults to `application/pdf`)
- Opens a **new tab** via `URL.createObjectURL`
- If pop-ups are blocked, **downloads** using the filename from `Content-Disposition` (e.g. `resume_candidate_7.pdf`)

The candidate modal **View resume →** button uses this instead of a plain link.

### Backend ([`backend/app/routers/candidates.py`](backend/app/routers/candidates.py))
- Serves resumes as **`application/pdf`** by default so the browser can render them inline.

### Note on your removed file
Resumes live in the **database** (`resumes.file_blob`), not on disk. If you removed `data/VARSHIL_PRAJAPATI_CV25.pdf` and re-seeded, rows may still hold the old blob or a small placeholder until you:

1. Put your PDF back under `data/` and run **`python -m backend.scripts.seed`**, or  
2. **Upload** a PDF in the candidate modal (replaces the blob for that id).

After that, **View resume** opens/downloads that candidate’s PDF from the API.

---

**User**

on view resume, the file name should be of actual name of candidate with _RESUME.pdf;
my plan is to get rid of these seed scripts, so for evaluator final application will onlt contain .db file that will be used directly

---

**Cursor**

Setting resume filenames to `{CandidateName}_RESUME.pdf` and updating docs for a `.db`-only evaluator workflow.


Here’s what changed:

### Resume filename (`{Name}_RESUME.pdf`)
- **Backend** ([`resume_names.py`](backend/app/utils/resume_names.py)): builds names like `Priya_Sharma_RESUME.pdf` from the candidate’s name (non-alphanumeric stripped, spaces → `_`).
- **GET `/api/candidates/{id}/resume`**: joins `candidates.name`, sets `Content-Disposition: inline; filename="…_RESUME.pdf"`.
- **Frontend** ([`openCandidateResume(id, candidateName)`](frontend/src/api.ts)): uses that header, or the same pattern from the modal name, for tab open / download fallback.

Example: **Priya Sharma** → `Priya_Sharma_RESUME.pdf`, **James O'Brien** → `James_OBrien_RESUME.pdf`.

### `.db`-only workflow (no seed for evaluators)
- **[`data/README.md`](data/README.md)** — evaluators use **`data/hireassist.db`** only; resumes live in the DB as blobs.
- **[README.md](README.md)** — quick start assumes the DB is already present; seed is commented as **developers only**.
- **[`.gitignore`](.gitignore)** — `!data/hireassist.db` so you can **commit** the DB for submission (other `*.db` files stay ignored).
- **[`project_structure.md`](project_structure.md)** — updated to match.

`backend/scripts/seed.py` is still there if you want to rebuild the DB locally; evaluators only need **`data/hireassist.db`** + `.env` + run the app.

**Before submit:** ensure your final `data/hireassist.db` is in the repo (or wherever evaluators expect it). Re-seed once if you want that file to reflect the latest data, then commit it.

---

**User**

we have limit of 15 rpm for gemini, so in llm calls, add time.sleep accordingly and retries, with exponential wait, max 3, what are metrics being used for eval, precision ? or accuracy ?

---

**Cursor**

Implementing Gemini rate limiting with exponential backoff and documenting eval metrics.


Here’s the current state:

### Gemini rate limiting (15 RPM)
All Gemini calls go through `generate_content_with_limits` in `backend/app/services/search/gemini_limits.py`:

- **RPM spacing:** `time.sleep` so calls are at least `60 / GEMINI_RPM` seconds apart (~4s at 15 RPM), with a thread lock so concurrent requests don’t burst.
- **Retries:** up to **`GEMINI_MAX_RETRIES`** (default **3**), with **exponential backoff** (`base * 2^attempt`) on retryable errors (429, quota, rate limit, 503, etc.).
- Wired from `ai_chain.py`; tunable in `backend/.env`: `GEMINI_RPM=15`, `GEMINI_MAX_RETRIES=3`.

### Eval metrics — precision or accuracy?
**Primary metric is query accuracy (exact set match), not precision alone.**

| What | Meaning |
|------|--------|
| **Pass/fail** | Predicted candidate ID set must **exactly** match `expected_candidate_ids` (sorted set equality). Some queries also require `expected_message_substring` in the API message. |
| **Query accuracy** | `passed_queries / total_queries` — this is the headline score. |
| **Set precision / recall / F1** | Logged **per query** for analysis (partial overlap). They **do not** decide pass/fail. |

So it’s **not** “precision@k” as the main score; it’s **strict set accuracy** per question, with P/R/F1 as diagnostic extras.

Also fixed: `eval/run_eval.py` now ends with `sys.exit(1 if failed else 0)` under a proper `if __name__ == "__main__"` block, and the README eval section documents these metrics.

---

**User**

in main, import warning and ignore them all

---

**Cursor**

`main.py` now imports `warnings` and calls `warnings.filterwarnings("ignore")` before the backend path is set and uvicorn starts, so warnings are suppressed when you run `python main.py`.

---

**User**

remove print statements, just add warning / error debugging prints

---

**Cursor**

Removing debug prints from app code and switching eval output to logging (warnings/errors only). Configuring `main.py` to suppress noisy logs.


Changes made:

**`main.py`**
- `logging.basicConfig(level=WARNING)` so only warnings and errors show from the app.
- Uvicorn started with `log_level="warning"`.
- Still using `warnings.filterwarnings("ignore")`.

**`backend/app/services/search/fuzzy.py`**
- Removed the stray debug `print` in `_name_match_score` (it could also crash if `token` was never set).

**`eval/run_eval.py`**
- Replaced `print` with `logging`: **`error`** for failures, **`warning`** for skips, fallback to offline, and final accuracy/summary.
- Passing queries are silent (no OK lines).

Interactive helpers (`check_db.py`, `print_reference.py`, `seed.py`) still use `print` for normal CLI output. Say if you want those switched to logging too.

---

**User**

now update project_strucyire, make it more detailed, accprding to projet
i have updated readme, do not change it, unless you add something
i have also added, workflow diagram in root, so add that in readme

---

**Cursor**

Updating `project_structure.md` and adding a minimal README link to the workflow diagram.


### `project_structure.md`
Expanded to match the repo as it exists now:

- Full top-level tree including **`Workflow.drawio.png`**, scripts, utils, and config
- Runtime entry points (`main.py`, uvicorn, Vite, eval)
- Backend: settings (`.env`-only), schema/stages, **`pipeline.py`** rules, full search stack (`fuzzy`, `sql_guard`, `gemini_limits`, `ai_chain`, `search_display`)
- Complete **API route table** under `/api`
- Frontend file roles and search UX behavior
- Eval assets, **metrics**, and id extraction
- Five **request flows** (Kanban, fuzzy, AI search, advance/reject, resume BLOB)
- Configuration table (`GEMINI_RPM`, retries, etc.) and links to related docs

### `README.md` (addition only)
One new bullet under **Architecture summary** linking to **[Workflow.drawio.png](Workflow.drawio.png)**. Everything else in your README is unchanged.

---

**User**

give me our database schema

---

**Cursor**

HireAssist uses **SQLite** at `data/hireassist.db`. DDL is defined in `backend/app/db/database.py`.

### `positions`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `position_code` | TEXT | NOT NULL, UNIQUE |
| `title` | TEXT | NOT NULL |

### `candidates`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `name` | TEXT | NOT NULL |
| `email` | TEXT | NOT NULL |
| `phone` | TEXT | nullable |
| `position_id` | INTEGER | NOT NULL → `positions(id)` |
| `current_stage` | INTEGER | NOT NULL, DEFAULT `0` |
| `rejected_at` | TEXT | nullable (ISO timestamp when rejected) |
| `offered_flag` | INTEGER | NOT NULL, DEFAULT `0` (0/1, sticky once set) |
| `hired_flag` | INTEGER | NOT NULL, DEFAULT `0` (0/1, sticky once set) |
| `entered_applied_at` | TEXT | NOT NULL |
| `entered_screening_at` | TEXT | nullable |
| `entered_offered_at` | TEXT | nullable |
| `entered_hired_at` | TEXT | nullable |

**`current_stage` values:** `-1` rejected, `0` applied, `1` screening, `2` offered, `3` hired.

### `stage_events` (append-only audit)
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `candidate_id` | INTEGER | NOT NULL → `candidates(id)` |
| `from_stage` | INTEGER | NOT NULL |
| `to_stage` | INTEGER | NOT NULL |
| `occurred_at` | TEXT | NOT NULL |

### `resumes`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `candidate_id` | INTEGER | NOT NULL, UNIQUE → `candidates(id)` |
| `file_blob` | BLOB | NOT NULL |
| `filename` | TEXT | nullable |
| `uploaded_at` | TEXT | NOT NULL |

### Indexes
- `idx_candidates_stage` on `candidates(current_stage)`
- `idx_candidates_position` on `candidates(position_id)`
- `idx_stage_events_candidate` on `stage_events(candidate_id)`

### Other
- `PRAGMA foreign_keys = ON` on connect.
- SQLite also has internal **`sqlite_sequence`** for AUTOINCREMENT ids (not created in app DDL).

Raw SQL from the app:

```7:51:backend/app/db/database.py
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    position_id INTEGER NOT NULL REFERENCES positions(id),
    current_stage INTEGER NOT NULL DEFAULT 0,
    rejected_at TEXT,
    offered_flag INTEGER NOT NULL DEFAULT 0,
    hired_flag INTEGER NOT NULL DEFAULT 0,
    entered_applied_at TEXT NOT NULL,
    entered_screening_at TEXT,
    entered_offered_at TEXT,
    entered_hired_at TEXT
);

CREATE TABLE IF NOT EXISTS stage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    from_stage INTEGER NOT NULL,
    to_stage INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL UNIQUE REFERENCES candidates(id),
    file_blob BLOB NOT NULL,
    filename TEXT,
    uploaded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(current_stage);
CREATE INDEX IF NOT EXISTS idx_candidates_position ON candidates(position_id);
CREATE INDEX IF NOT EXISTS idx_stage_events_candidate ON stage_events(candidate_id);
"""
```

---

**User**

update requirements.txt according to venv

---

**Cursor**

Syncing `requirements.txt` with the venv: replacing obsolete `google-generativeai` with `google-genai` and pinning all installed packages.


Updated `backend/requirements.txt` from `pip freeze` on `backend/.venv`.

**Notable fixes vs the old file:**
- **`google-generativeai`** removed — the app uses **`google-genai==1.47.0`** (`ai_chain.py`).
- **`uvicorn[standard]`** replaced with **`uvicorn==0.32.1`** plus its extras already in the venv (`httptools`, `watchfiles`, `websockets`).
- Added transitive pins (e.g. `google-auth`, `tenacity`, `python-dotenv`) so a fresh `pip install -r requirements.txt` matches your venv.

Also present in the venv and pinned: **`fpdf2` / `pillow`** (seed PDFs), **`openai`** (installed but not used by the API code). Say if you want a slimmer top-level-only requirements file instead of a full freeze.

---

**User**

in read me make instrcutions clear, in root of repo, open powershell/terminal, and then the backend steps, again open another terminal, go into frontend and then its steps...

---

**Cursor**

Updated **Quick start** in `README.md`:

- States you need **two terminals** and work from the **repo root** (with example `cd` paths).
- **Terminal 1:** root → one-time `backend/` venv, pip, `.env` → back to root → `python main.py` (keep running); notes API URL and `/health`.
- **Terminal 2:** root → `frontend/` → `npm install` / `npm run dev`; notes UI URL and API proxy.
- **Eval:** run from repo root with `backend\.venv\Scripts\python eval\...`.
- Fixed optional seed hint to `backend\.venv\Scripts\python scripts\seed.py` (from `backend/` after venv exists).

Rest of the README is unchanged.

---

**User**

hmm, okay for user, lets not give them all these tasks, make 2 files, setup.py and run.py, 
setup will be for creating venv and pip install requirements and npm install and run will start both servers, 
so user need to do, 
python setup.py and then python run.py, 

---

**Cursor**

Creating `setup.py` and `run.py` at the repo root and simplifying the README quick start.


Added two repo-root scripts and simplified the docs.

### `setup.py`
- Requires Python 3.9+ and `npm` on PATH  
- Creates `backend/.venv` (if missing)  
- `pip install -r backend/requirements.txt`  
- Copies `backend/.env.example` → `backend/.env` only when `.env` does not exist  
- Runs `npm install` in `frontend/`  

### `run.py`
- Checks venv and `frontend/node_modules`  
- Starts **`main.py`** (API on :8000) and **`npm run dev`** (UI on :5173)  
- **Ctrl+C** stops both  

### User flow
```powershell
cd path\to\HireAssist
python setup.py
# edit backend/.env → GEMINI_API
python run.py
```

`README.md` Quick start and `project_structure.md` entry points are updated to match. Manual two-terminal steps are still mentioned as optional.

---

**User**

shouldnt that be after setup.py, ,venv/scripts/activate then run.py ?

---

**Cursor**

Updating the flow so we activate the backend venv after setup, then run `run.py` from that environment.


Yes — that’s the intended flow now.

**Why:** `setup.py` uses your system Python to create `backend/.venv`. After that, backend code (and `run.py`) should run **inside** that venv so dependencies and paths match.

**Order:**
1. `python setup.py` (repo root, any Python 3.9+)
2. Edit `backend/.env`
3. `backend\.venv\Scripts\activate` (repo root on Windows)
4. `python run.py`

`run.py` now checks that the active interpreter is `backend/.venv` and prints the activate command if you skip step 3. With the venv active, it starts `main.py` with that same Python plus `npm run dev`.

README, `setup.py` completion message, and `project_structure.md` are updated to match. Eval commands assume the venv is activated too (`python eval\run_eval.py`).

---

**User**

while doing pip install, ...?
maybe cuz my pc have original 3.14 python ?

Creating virtualenv at D:\AI Agents\naicos-test\HireAssist\backend\.venv
>>> C:\Python314\python.exe -m venv D:\AI Agents\naicos-test\HireAssist\backend\.venv
>>> D:\AI Agents\naicos-test\HireAssist\backend\.venv\Scripts\python.exe -m pip install --upgrade pip

Building wheels for collected packages: pydantic-core
  Building wheel for pydantic-core (pyproject.toml) ... error
  error: subprocess-exited-with-error

  × Building wheel for pydantic-core (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [36 lines of output]
      Running `maturin pep517 build-wheel -i D:\AI Agents\naicos-test\HireAssist\backend\.venv\Scripts\python.exe --compatibility off`
      ðŸ“¦ Including license file `LICENSE`
      ðŸ\x8d¹ Building a mixed python/rust project
      ðŸ\x90\x8d Found CPython 3.14 at D:\AI Agents\naicos-test\HireAssist\backend\.venv\Scripts\python.exe
      ðŸ”— Found pyo3 bindings
      ðŸ“¡ Using build options features, bindings from pyproject.toml
         Compiling proc-macro2 v1.0.86
         Compiling unicode-ident v1.0.12
         Compiling target-lexicon v0.12.14
         Compiling cc v1.0.101
         Compiling once_cell v1.19.0
         Compiling autocfg v1.3.0
         Compiling stable_deref_trait v1.2.0
         Compiling heck v0.5.0
         Compiling litemap v0.7.3
         Compiling writeable v0.5.5
         Compiling version_check v0.9.5
         Compiling libc v0.2.155
      error: linker `link.exe` not found
        |
        = note: program not found

      note: the msvc targets depend on the msvc linker but `link.exe` was not found

      note: please ensure that Visual Studio 2017 or later, or Build Tools for Visual Studio were installed with the Visual C++ option.

      note: VS Code is a different product, and is not sufficient.

      error: could not compile `proc-macro2` (build script) due to 1 previous error
      warning: build failed, waiting for other jobs to finish...
      error: could not compile `target-lexicon` (build script) due to 1 previous error
      error: could not compile `libc` (build script) due to 1 previous error
      ðŸ’¥ maturin failed
        Caused by: Failed to build a native library through cargo
        Caused by: Cargo build finished with "exit code: 101": `"cargo" "rustc" "--profile" "release" "--features" "pyo3/extension-module" "--message-format" "json-render-diagnostics" "--manifest-path" "C:\\Users\\Varshil\\AppData\\Local\\Temp\\pip-install-eai87j5l\\pydantic-core_c6d2290378234f05bb12b0ce93ec0385\\Cargo.toml" "--lib" "--crate-type" "cdylib"`
      Error: command ['maturin', 'pep517', 'build-wheel', '-i', 'D:\\AI Agents\\naicos-test\\HireAssist\\backend\\.venv\\Scripts\\python.exe', '--compatibility', 'off'] returned non-zero exit status 1
      [end of output]

  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for pydantic-core
Failed to build pydantic-core
error: failed-wheel-build-for-install

× Failed to build installable wheels for some pyproject.toml based projects
╰─> pydantic-core
Traceback (most recent call last):
  File "D:\AI Agents\naicos-test\HireAssist\setup.py", line 87, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "D:\AI Agents\naicos-test\HireAssist\setup.py", line 68, in main
    run([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\AI Agents\naicos-test\HireAssist\setup.py", line 33, in run
    subprocess.check_call(cmd, cwd=cwd or ROOT)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\subprocess.py", line 419, in check_call
    raise CalledProcessError(retcode, cmd)
subprocess.CalledProcessError: Command '['D:\\AI Agents\\naicos-test\\HireAssist\\backend\\.venv\\Scripts\\python.exe', '-m', 'pip', 'install', '-r', 'D:\\AI Agents\\naicos-test\\HireAssist\\backend\\requirements.txt']' returned non-zero exit status 1.

---

**Cursor**

Python 3.14 lacks pre-built `pydantic-core` wheels, so pip tries to compile Rust and fails without MSVC. Updating `setup.py` to prefer Python 3.9–3.12 via the Windows `py` launcher when the default interpreter is too new.


Yes — that failure is because **`setup.py` used your default `C:\Python314\python.exe`** to create `.venv`, so pip installed into **Python 3.14**.

For 3.14 there’s often **no prebuilt wheel for `pydantic-core`**, so pip tries to **build from Rust**. That needs **`link.exe`** (Visual Studio C++ Build Tools). Without it, you get exactly that error. It’s not a broken `requirements.txt`.

### Fix on your machine

1. **Remove the bad venv** (3.14):
   ```powershell
   Remove-Item -Recurse -Force backend\.venv
   ```

2. **Run setup with Python 3.9–3.12** (install 3.9 from [python.org](https://www.python.org/downloads/) if needed):
   ```powershell
   py -3.9 setup.py
   ```
   Or: `py -3.11 setup.py`, etc.

3. Then:
   ```powershell
   backend\.venv\Scripts\activate
   python run.py
   ```

### What we changed in the repo

`setup.py` now detects **3.14+** and on Windows tries **`py -3.12` / `3.11` / `3.10` / `3.9` / `3.13`** automatically when you run `python setup.py`. If an old **3.14 `.venv` already exists**, it tells you to delete it and rerun. README now recommends **`py -3.9 setup.py`** when default `python` is 3.14.

**Alternative (not recommended for this project):** install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with “Desktop development with C++” and keep 3.14 — still slower and less reliable than using 3.9–3.12.

