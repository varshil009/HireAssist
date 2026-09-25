import { useCallback, useEffect, useMemo, useState } from "react";
import {
  advanceCandidate,
  aiSearch,
  Candidate,
  fetchCandidate,
  fetchPipeline,
  fetchSuggest,
  fetchTimeline,
  PipelineColumn,
  rejectCandidate,
  resumeUrl,
  SearchResponse,
  StageEvent,
  SuggestItem,
  uploadResume,
} from "./api";

import { StagePill, STAGE_COLUMN_BORDER, stageFromLabel } from "./stageStyles";

function extractCandidateId(columns: string[], row: SearchResponse["rows"][number]): number | null {
  const lower = columns.map((c) => c.toLowerCase());
  let idx = lower.findIndex((c) => c === "id" || c === "candidate_id" || c.endsWith(".id"));
  if (idx === -1 && lower[0] === "id") idx = 0;
  if (idx === -1) return null;
  const raw = row[idx];
  if (raw === null || raw === undefined) return null;
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}

function ResultsTable({
  columns,
  rows,
  onOpenCandidate,
}: {
  columns: string[];
  rows: SearchResponse["rows"];
  onOpenCandidate: (id: number) => void;
}) {
  if (!columns.length) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-md ring-1 ring-slate-900/5">
      <div className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-indigo-50/50 px-4 py-2 text-xs text-slate-500">
        Click a row to view full candidate profile
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-slate-100/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
              {columns.map((c) => (
                <th key={c} className="px-4 py-3">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const candidateId = extractCandidateId(columns, row);
              const clickable = candidateId !== null;
              return (
                <tr
                  key={i}
                  className={`border-t border-slate-100 transition-colors ${
                    clickable
                      ? "cursor-pointer hover:bg-indigo-50/80 active:bg-indigo-100/60"
                      : "hover:bg-slate-50/50"
                  } ${i % 2 === 0 ? "bg-white" : "bg-slate-50/40"}`}
                  onClick={() => {
                    if (candidateId !== null) onOpenCandidate(candidateId);
                  }}
                  onKeyDown={(e) => {
                    if (clickable && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onOpenCandidate(candidateId!);
                    }
                  }}
                  tabIndex={clickable ? 0 : undefined}
                  role={clickable ? "button" : undefined}
                >
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-2.5 text-slate-800">
                      {columns[j] === "Stage" && cell !== null ? (
                        <StagePill label={String(cell)} />
                      ) : cell === null ? (
                        "—"
                      ) : (
                        String(cell)
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CandidateDetail({
  id,
  onClose,
  onUpdated,
}: {
  id: number;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [timeline, setTimeline] = useState<StageEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    const [c, t] = await Promise.all([fetchCandidate(id), fetchTimeline(id)]);
    setCandidate(c);
    setTimeline(t);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  const canAdvance = candidate && candidate.current_stage >= 0 && candidate.current_stage < 3;
  const canReject = candidate && candidate.current_stage >= 0 && candidate.current_stage <= 2;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/20 bg-white p-6 shadow-2xl shadow-indigo-900/20"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-indigo-600">Candidate</p>
            <h2 className="text-2xl font-bold text-slate-900">{candidate?.name ?? "Loading…"}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            ✕
          </button>
        </div>
        {error && <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        {candidate && (
          <>
            <div className="space-y-1 text-sm text-slate-600">
              <p>{candidate.email}</p>
              {candidate.phone && <p>{candidate.phone}</p>}
              <p>{candidate.position_title}</p>
            </div>
            <StagePill label={candidate.stage_label} stage={candidate.current_stage} className="mt-3" />
            {candidate.days_in_current_stage != null && candidate.current_stage >= 0 && (
              <p className="mt-3 text-sm text-slate-600">
                In current stage: <strong>{candidate.days_in_current_stage}</strong> days
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              {canAdvance && (
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-indigo-500/25 disabled:opacity-50"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await advanceCandidate(id);
                      await load();
                      onUpdated();
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Advance stage
                </button>
              )}
              {canReject && (
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await rejectCandidate(id);
                      await load();
                      onUpdated();
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Reject
                </button>
              )}
            </div>
            <div className="mt-5 rounded-xl border border-slate-100 bg-slate-50/50 p-3">
              <label className="text-sm font-semibold text-slate-700">Resume</label>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="text-xs file:mr-2 file:rounded-lg file:border-0 file:bg-indigo-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    setBusy(true);
                    try {
                      await uploadResume(id, f);
                    } catch (err) {
                      setError(String(err));
                    } finally {
                      setBusy(false);
                    }
                  }}
                />
                <a
                  className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                  href={resumeUrl(id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  View resume →
                </a>
              </div>
            </div>
            <h3 className="mb-2 mt-6 text-sm font-semibold text-slate-800">Stage history</h3>
            <ul className="space-y-2">
              {timeline.map((ev) => (
                <li
                  key={ev.id}
                  className="rounded-xl border border-slate-100 bg-white px-3 py-2 text-sm shadow-sm"
                >
                  <span className="font-medium text-slate-800">
                    {ev.from_label === "Start" ? (
                      ev.from_label
                    ) : (
                      <StagePill label={ev.from_label} stage={stageFromLabel(ev.from_label) ?? undefined} />
                    )}{" "}
                    →{" "}
                    <StagePill label={ev.to_label} stage={ev.to_stage} />
                  </span>
                  <span className="mt-0.5 block text-xs text-slate-500">{ev.occurred_at}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [columns, setColumns] = useState<PipelineColumn[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [suggestions, setSuggestions] = useState<SuggestItem[]>([]);
  const [emptySuggest, setEmptySuggest] = useState<string | null>(null);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [searchBusy, setSearchBusy] = useState(false);
  const [showFuzzy, setShowFuzzy] = useState(true);

  const visibleColumns = useMemo(
    () => columns.filter((c) => c.stage !== -1).concat(columns.filter((c) => c.stage === -1)),
    [columns],
  );

  const reload = useCallback(async () => {
    setLoadError(null);
    const data = await fetchPipeline();
    setColumns(data.columns);
  }, []);

  const runSearch = useCallback(async () => {
    const q = searchQ.trim();
    if (!q || searchBusy) return;
    setShowFuzzy(false);
    setSuggestions([]);
    setEmptySuggest(null);
    setSearchBusy(true);
    setSearchResult(null);
    try {
      const res = await aiSearch(q);
      setSearchResult(res);
    } catch (e) {
      setSearchResult({
        ok: false,
        message: String(e),
        query: q,
        columns: [],
        rows: [],
      });
    } finally {
      setSearchBusy(false);
    }
  }, [searchQ, searchBusy]);

  useEffect(() => {
    reload().catch((e) => setLoadError(String(e)));
  }, [reload]);

  useEffect(() => {
    const q = searchQ.trim();
    // Re-enable fuzzy only when the user edits the query (not when Search toggles showFuzzy).
    setShowFuzzy(true);
    if (q.length < 2) {
      setSuggestions([]);
      setEmptySuggest(null);
      return;
    }
    const t = setTimeout(() => {
      fetchSuggest(q)
        .then((r) => {
          setSuggestions(r.suggestions);
          setEmptySuggest(r.empty_message);
        })
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

  const fuzzyOpen = showFuzzy && searchQ.trim().length >= 2;

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-8 sm:px-6">
      <header className="mb-10 text-center">
        <h1 className="bg-gradient-to-r from-indigo-700 via-violet-700 to-indigo-600 bg-clip-text text-4xl font-bold tracking-tight text-transparent">
          HireAssist
        </h1>
        <p className="mt-2 text-slate-600">Find candidates with smart search.</p>
      </header>

      <section className="glass-panel mb-10 rounded-2xl p-5 sm:p-6">
        <label className="text-sm font-semibold text-slate-800">Search candidates</label>
        <p className="mt-0.5 text-xs text-slate-500">Type for quick matches, then press Enter or Search for AI lookup.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm shadow-inner shadow-slate-900/5 outline-none ring-indigo-500/0 transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
            placeholder="Name, stage, position, or a full question…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void runSearch();
              }
            }}
          />
          <button
            type="button"
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30 transition hover:from-indigo-500 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={searchBusy || !searchQ.trim()}
            onClick={() => void runSearch()}
          >
            {searchBusy ? "Searching…" : "Search"}
          </button>
        </div>
        {fuzzyOpen && suggestions.length > 0 && (
          <ul className="mt-3 overflow-hidden rounded-xl border border-indigo-100 bg-white shadow-sm">
            {suggestions.map((s) => (
              <li key={s.id} className="border-b border-slate-50 last:border-0">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left text-sm transition hover:bg-indigo-50/70"
                  onClick={() => {
                    setShowFuzzy(false);
                    setSuggestions([]);
                    setSelectedId(s.id);
                  }}
                >
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-medium text-slate-900">{s.name}</span>
                    <StagePill label={s.stage_label} stage={s.current_stage} />
                    <span className="text-slate-500">{s.position_title}</span>
                  </span>
                  <span className="text-xs text-indigo-500">Open</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {fuzzyOpen && emptySuggest && suggestions.length === 0 && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-100">
            {emptySuggest}
          </p>
        )}
        {searchResult && (
          <div className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <p
              className={`rounded-lg px-3 py-2 text-sm ${
                searchResult.ok ? "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-100" : "bg-slate-100 text-slate-700"
              }`}
            >
              {searchResult.message}
            </p>
            <ResultsTable
              columns={searchResult.columns}
              rows={searchResult.rows}
              onOpenCandidate={(id) => setSelectedId(id)}
            />
          </div>
        )}
      </section>

      {loadError && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-rose-700 ring-1 ring-rose-100">{loadError}</p>
      )}

      <h2 className="mb-4 text-lg font-semibold text-slate-800">Pipeline board</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {visibleColumns.map((col) => (
          <div
            key={col.stage}
            className={`glass-panel rounded-2xl border-t-4 p-4 ${STAGE_COLUMN_BORDER[col.stage] ?? "border-t-slate-300"}`}
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <StagePill label={col.label} stage={col.stage} className="text-sm uppercase tracking-wide" />
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                {col.candidates.length}
              </span>
            </div>
            <ul className="space-y-2">
              {col.candidates.length === 0 && (
                <li className="rounded-lg border border-dashed border-slate-200 py-6 text-center text-xs text-slate-400">
                  Empty
                </li>
              )}
              {col.candidates.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(c.id)}
                    className="group w-full rounded-xl border border-slate-100 bg-white/90 px-3 py-2.5 text-left text-sm shadow-sm transition hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/10"
                  >
                    <span className="font-semibold text-slate-900 group-hover:text-indigo-700">{c.name}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{c.position_title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {selectedId != null && (
        <CandidateDetail id={selectedId} onClose={() => setSelectedId(null)} onUpdated={reload} />
      )}
    </div>
  );
}
