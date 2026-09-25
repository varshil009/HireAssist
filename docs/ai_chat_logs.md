# AI chat logs (HireAssist)

This file summarizes the Cursor AI-assisted design session used to build HireAssist. Export your full Cursor transcript into this folder if required by the assignment submission checklist.

## Session topics

1. **Schema** — SQLite tables for `positions`, `candidates`, `stage_events`, `resumes`; stages `-1..3`; `offered_flag`, `hired_flag`, `rejected_at`, and set-once `entered_*_at` timestamps.
2. **Search UX** — Realtime fuzzy suggestions on keystrokes; full NL→SQL only when the user clicks **Search** (no AI toggle).
3. **LLM integration** — Two-step conditioned prompt chain (not LangGraph); readonly SQL guard; hardcoded message after the second failure.
4. **Mock data** — Seed script with three openings and ~25 candidates anchored to 2025-09-24 UTC for stable eval dates.
5. **Eval** — Twenty natural-language queries in `eval/queries.json` with expected candidate id sets; `eval/run_eval.py` supports live AI or `--offline` reference SQL validation.

## Disagreement with AI (documented for assignment)

- **AI proposed:** LangGraph with cyclical LLM nodes and up to three SQL retries for every search path.
- **We chose:** Explicit pipeline flags, fuzzy pre-search, and a **two-try** prompt chain with **hardcoded failure copy** for clearer UX and eval reproducibility.

## Implementation agent

Implementation was completed via Cursor Agent following the approved plan (`HireAssist plan (updated)`).
