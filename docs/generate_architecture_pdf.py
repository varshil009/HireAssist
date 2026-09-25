"""Generate docs/HireAssist-Architecture.pdf (requires fpdf2)."""
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    raise SystemExit("Install fpdf2: backend\\.venv\\Scripts\\pip install fpdf2")

OUT = Path(__file__).resolve().parent / "HireAssist-Architecture.pdf"
REPO = "https://github.com/your-org/HireAssist"  # Replace with your GitHub URL before submission


class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 10, "HireAssist Architecture", align="C")


def main():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "HireAssist Architecture", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        0,
        6,
        f"GitHub: {REPO}\n\n"
        "Summary:\n"
        "HireAssist is a recruiter-facing mini hiring pipeline. Recruiters manage candidates "
        "across Applied, Screening, Offered, and Hired (plus Rejected), with an immutable "
        "stage_events audit trail. A single search box provides realtime fuzzy name/position "
        "hints and full natural-language search via a two-attempt LLM-to-SQL chain guarded "
        "by read-only SELECT validation.\n\n"
        "Components:\n"
        "- Frontend: React, Vite, Tailwind (Kanban board, candidate detail, search UI)\n"
        "- Backend: FastAPI, SQLite (positions, candidates, stage_events, resumes)\n"
        "- AI: Google Gemini (GEMINI_API / GEMINI_MODEL in backend/.env); SQL generation; max 2 tries\n"
        "- Eval: 20 NL queries in eval/queries.json; run_eval.py\n\n"
        "Data highlights:\n"
        "- offered_flag / hired_flag for 'offered but not hired' queries\n"
        "- rejected_at and current_stage = -1 for rejections\n"
        "- Seed: 3+ job openings, fixed anchor dates for time-based eval\n\n"
        "See project_structure.md and README.md in the repository for module layout and run steps.",
    )
    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
