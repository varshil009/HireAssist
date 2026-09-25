from __future__ import annotations

import re


def candidate_resume_filename(name: str) -> str:
    """Build download name: {Name}_RESUME.pdf (spaces -> underscores)."""
    cleaned = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    token = "_".join(cleaned.split()) or "Candidate"
    return f"{token}_RESUME.pdf"
