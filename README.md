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

## Decisions and trade-offs

| Decision                                                                                                       | Rationale                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Proceeded with both fuzzy search and AI search**                                                             | Common searches involving a candidate's first or last name should not require artificial intelligence. Therefore, fuzzy matching was added for straightforward name-based searches, while detailed natural-language queries are handled through the AI search flow when the user clicks **Search**.                                                                                                                                                                                                                                |
| **LLM calls for natural-language search**                                                                      | Natural-language queries can involve multiple conditions and require reasoning to interpret the user's intent. An LLM is therefore used to understand these queries and translate them into an appropriate database search.                                                                                                                                                                                                                                                                                                        |
| **Used SQLite3 for the database**                                                                              | SQLite3 is a lightweight, built-in Python database option that avoids the additional setup and infrastructure of a separate database server.                                                                                                                                                                                                                                                                                                                                                                                       |
| **Stored resumes as BLOBs**                                                                                    | Using a NoSQL database for file storage would add additional weight and complexity to the project. Storing resumes as BLOBs keeps the implementation within the existing SQLite database.                                                                                                                                                                                                                                                                                                                                          |
| **LLM calls use rate limits and exponential retries**                                                          | During testing, Gemini occasionally returned HTTP 500 errors due to high demand. Exponential backoff and retries help recover from temporary failures, while rate limiting helps prevent excessive requests and hitting requests-per-minute (RPM) limits.                                                                                                                                                                                                                                                                          |
| **Database contains five tables: `candidates`, `resumes`, `positions`, `stage_events`, and `sqlite_sequence`** | The `candidates` table contains most of the information required for the hiring workflow. Since resumes are stored as BLOBs, they are kept in a separate `resumes` table. The `positions` table stores unique position IDs and names. The `stage_events` table maintains the audit trail; once a stage event is recorded, it cannot be edited, preserving the one-directional progression of the hiring workflow. `sqlite_sequence` is SQLite's internal metadata table used for tracking automatically generated sequence values. |
| **Evaluated the LLM using AI-generated queries and their corresponding answers**                               | Evaluating the LLM's generated query along with the results produced by executing that query provides confidence that the generated answers are accurate and grounded in the database.                                                                                                                                                                                                                                                                                                                                             |



### Where we disagreed with AI
| What AI was doing                                                                                                                                                                    | What I did                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **AI used a shortcut for the View Resume option** — it simply opened the resume file that had been provided to the application.                                                      | I instructed it to retrieve the resume as a BLOB from the database, reconstruct the file from the stored binary data, and provide it as a downloadable PDF.                                                                                                                                                                                                                                                              |
| **AI suggested using keyword-based search** — for example, checking whether the query contained words such as `"interview"` or `"hiring"` and using those keywords to apply filters. | I determined that this approach would not work reliably because user queries can be complex. For example, a recruiter might enter `Hired candidates that applied on Data Analyst position` or `Who applied in August 2026`. These are detailed natural-language queries where simply matching keywords would not capture the user's intended conditions. I therefore used the language model to interpret these queries. |
| **Fuzzy matching was applied to the entire candidate name.**                                                                                                                         | I changed the matching logic to compare the query against the candidate's first and last names separately. This improves accuracy because partial inputs such as `pri` can otherwise receive a low similarity score when compared against the full name `Priya Sharma` and be incorrectly filtered out by the similarity threshold.                                                                                      |


## With more time
- An agentic workflow with complex and multi hop query handling, where recruiter can talk with AI to discuss candidates' resume impact and even compare them according to `Expected Salary`, `YoE`, `Fields of Expertise`, `Education` etc. 
- LLM Evaluation on big dataset.
- Clickable filters on table resulted from user query
- Role-based auth and multi-recruiter tenancy

