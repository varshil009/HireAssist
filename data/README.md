# Application database

Place the SQLite file here:

**`hireassist.db`**

Evaluators and production runs use this file directly. The API reads it from `data/hireassist.db` (see `backend/app/config.py`). On startup, the app only ensures tables exist (`CREATE IF NOT EXISTS`); it does not wipe or reseed data.

Resume PDFs are stored **inside** the database (`resumes.file_blob`), not as separate files on disk.

Optional: developers can regenerate this file locally with `backend/scripts/seed.py` (not required for evaluation).
