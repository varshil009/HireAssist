const API = "";

export type Candidate = {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  position_id: number;
  position_code?: string | null;
  position_title?: string | null;
  current_stage: number;
  stage_label: string;
  rejected_at: string | null;
  offered_flag: number;
  hired_flag: number;
  entered_applied_at: string;
  entered_screening_at: string | null;
  entered_offered_at: string | null;
  entered_hired_at: string | null;
  days_in_current_stage: number | null;
};

export type PipelineColumn = {
  stage: number;
  label: string;
  candidates: Candidate[];
};

export type Position = {
  id: number;
  position_code: string;
  title: string;
};

export type StageEvent = {
  id: number;
  candidate_id: number;
  from_stage: number;
  to_stage: number;
  from_label: string;
  to_label: string;
  occurred_at: string;
};

export type SuggestItem = {
  id: number;
  name: string;
  current_stage: number;
  stage_label: string;
  position_title: string;
  position_code: string;
  score: number;
};

export type SearchResponse = {
  ok: boolean;
  message: string;
  query: string;
  columns: string[];
  rows: (string | number | null)[][];
  fuzzy_suggestions?: SuggestItem[];
};

export async function fetchPipeline(): Promise<{ columns: PipelineColumn[] }> {
  const r = await fetch(`${API}/api/pipeline`);
  if (!r.ok) throw new Error("Failed to load pipeline");
  return r.json();
}

export async function fetchPositions(): Promise<Position[]> {
  const r = await fetch(`${API}/api/positions`);
  if (!r.ok) throw new Error("Failed to load positions");
  return r.json();
}

export async function createCandidate(body: {
  name: string;
  email: string;
  phone?: string | null;
  position_id: number;
}): Promise<Candidate> {
  const r = await fetch(`${API}/api/pipeline/candidates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    const detail = e.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((x: { msg?: string }) => x.msg).filter(Boolean).join(", ")
          : "Could not add candidate";
    throw new Error(msg);
  }
  return r.json();
}

export async function fetchCandidate(id: number): Promise<Candidate> {
  const r = await fetch(`${API}/api/candidates/${id}`);
  if (!r.ok) throw new Error("Candidate not found");
  return r.json();
}

export async function fetchTimeline(id: number): Promise<StageEvent[]> {
  const r = await fetch(`${API}/api/candidates/${id}/timeline`);
  if (!r.ok) throw new Error("Timeline failed");
  return r.json();
}

export async function advanceCandidate(id: number): Promise<Candidate> {
  const r = await fetch(`${API}/api/candidates/${id}/advance`, { method: "POST" });
  if (!r.ok) {
    const e = await r.json();
    throw new Error(e.detail || "Advance failed");
  }
  return r.json();
}

export async function rejectCandidate(id: number): Promise<Candidate> {
  const r = await fetch(`${API}/api/candidates/${id}/reject`, { method: "POST" });
  if (!r.ok) {
    const e = await r.json();
    throw new Error(e.detail || "Reject failed");
  }
  return r.json();
}

export async function fetchSuggest(q: string): Promise<{
  query: string;
  suggestions: SuggestItem[];
  empty_message: string | null;
}> {
  const r = await fetch(`${API}/api/search/suggest?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error("Suggest failed");
  return r.json();
}

export async function aiSearch(query: string): Promise<SearchResponse> {
  const r = await fetch(`${API}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!r.ok) throw new Error("Search failed");
  return r.json();
}

export async function uploadResume(id: number, file: File): Promise<void> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API}/api/candidates/${id}/resume`, { method: "PUT", body: fd });
  if (!r.ok) throw new Error("Upload failed");
}

export function resumeDownloadFilename(candidateName: string): string {
  const safe =
    candidateName
      .replace(/[^\w\s-]/g, "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .join("_") || "Candidate";
  return `${safe}_RESUME.pdf`;
}

function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(header);
  return match ? decodeURIComponent(match[1].replace(/"/g, "")) : null;
}

export async function openCandidateResume(candidateId: number, candidateName: string): Promise<void> {
  const r = await fetch(`${API}/api/candidates/${candidateId}/resume`);
  if (!r.ok) {
    throw new Error(r.status === 404 ? "No resume on file for this candidate." : "Could not load resume.");
  }
  const raw = await r.blob();
  const type = r.headers.get("Content-Type")?.split(";")[0] || "application/pdf";
  const blob = raw.type && raw.type !== "application/octet-stream" ? raw : new Blob([raw], { type });
  const filename =
    filenameFromContentDisposition(r.headers.get("Content-Disposition")) ||
    resumeDownloadFilename(candidateName);
  const url = URL.createObjectURL(blob);
  const tab = window.open(url, "_blank", "noopener,noreferrer");
  if (!tab) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000);
}

export function resumeUrl(id: number): string {
  return `${API}/api/candidates/${id}/resume`;
}
