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

function stageBadge(stage: number) {
  const colors: Record<number, string> = {
    [-1]: "bg-rose-100 text-rose-800",
    0: "bg-slate-200 text-slate-800",
    1: "bg-amber-100 text-amber-900",
    2: "bg-sky-100 text-sky-900",
    3: "bg-emerald-100 text-emerald-900",
  };
  return colors[stage] ?? "bg-gray-100";
}

function ResultsTable({ columns, rows }: { columns: string[]; rows: SearchResponse["rows"] }) {
  if (!columns.length) return null;
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100">
          <tr>
            {columns.map((c) => (
              <th key={c} className="px-3 py-2 text-left font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2">
                  {cell === null ? "—" : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-2">
          <h2 className="text-xl font-semibold">{candidate?.name ?? "Loading…"}</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-800">
            Close
          </button>
        </div>
        {error && <p className="mb-3 text-sm text-rose-600">{error}</p>}
        {candidate && (
          <>
            <p className="text-sm text-slate-600">{candidate.email}</p>
            <p className="text-sm text-slate-600">{candidate.position_title}</p>
            <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs ${stageBadge(candidate.current_stage)}`}>
              {candidate.stage_label}
            </span>
            {candidate.days_in_current_stage != null && candidate.current_stage >= 0 && (
              <p className="mt-2 text-sm">In current stage: {candidate.days_in_current_stage} days</p>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              {canAdvance && (
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
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
                  Advance
                </button>
              )}
              {canReject && (
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-lg border border-rose-300 px-3 py-1.5 text-sm text-rose-700 disabled:opacity-50"
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
            <div className="mt-4">
              <label className="text-sm font-medium">Resume</label>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
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
                <a className="text-sm text-indigo-600 underline" href={resumeUrl(id)} target="_blank" rel="noreferrer">
                  View resume
                </a>
              </div>
            </div>
            <h3 className="mb-2 mt-6 font-medium">History</h3>
            <ul className="space-y-2 text-sm">
              {timeline.map((ev) => (
                <li key={ev.id} className="rounded border border-slate-100 px-3 py-2">
                  {ev.from_label} → {ev.to_label}
                  <span className="block text-xs text-slate-500">{ev.occurred_at}</span>
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

  const visibleColumns = useMemo(
    () => columns.filter((c) => c.stage !== -1).concat(columns.filter((c) => c.stage === -1)),
    [columns],
  );

  const reload = useCallback(async () => {
    setLoadError(null);
    const data = await fetchPipeline();
    setColumns(data.columns);
  }, []);

  useEffect(() => {
    reload().catch((e) => setLoadError(String(e)));
  }, [reload]);

  useEffect(() => {
    const q = searchQ.trim();
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

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">HireAssist</h1>
        <p className="text-slate-600">Mini hiring pipeline for recruiters</p>
      </header>

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="text-sm font-medium text-slate-700">Search candidates</label>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[240px] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Name, stage question, or filters…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
          />
          <button
            type="button"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={searchBusy || !searchQ.trim()}
            onClick={async () => {
              setSearchBusy(true);
              setSearchResult(null);
              try {
                const res = await aiSearch(searchQ.trim());
                setSearchResult(res);
              } catch (e) {
                setSearchResult({
                  ok: false,
                  message: String(e),
                  query: searchQ,
                  columns: [],
                  rows: [],
                });
              } finally {
                setSearchBusy(false);
              }
            }}
          >
            {searchBusy ? "Searching…" : "Search"}
          </button>
        </div>
        {suggestions.length > 0 && (
          <ul className="mt-3 space-y-1 rounded-lg border border-slate-100 bg-slate-50 p-2 text-sm">
            {suggestions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className="w-full rounded px-2 py-1 text-left hover:bg-white"
                  onClick={() => {
                    setSelectedId(s.id);
                  }}
                >
                  {s.name} · {s.stage_label} · {s.position_title}
                </button>
              </li>
            ))}
          </ul>
        )}
        {emptySuggest && searchQ.trim().length >= 2 && suggestions.length === 0 && (
          <p className="mt-2 text-sm text-amber-800">{emptySuggest}</p>
        )}
        {searchResult && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-slate-700">{searchResult.message}</p>
            <ResultsTable columns={searchResult.columns} rows={searchResult.rows} />
          </div>
        )}
      </section>

      {loadError && <p className="mb-4 text-rose-600">{loadError}</p>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {visibleColumns.map((col) => (
          <div key={col.stage} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {col.label}
              <span className="ml-1 text-slate-400">({col.candidates.length})</span>
            </h2>
            <ul className="space-y-2">
              {col.candidates.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(c.id)}
                    className="w-full rounded-lg border border-slate-100 px-3 py-2 text-left text-sm hover:border-indigo-200 hover:bg-indigo-50/50"
                  >
                    <span className="font-medium">{c.name}</span>
                    <span className="block text-xs text-slate-500">{c.position_title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {selectedId != null && (
        <CandidateDetail
          id={selectedId}
          onClose={() => setSelectedId(null)}
          onUpdated={reload}
        />
      )}
    </div>
  );
}
