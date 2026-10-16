import { ExternalLink, Grid3X3, Mountain, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type { ClimbDiscipline, LogbookEntry } from "../types/api";

interface LogbookListProps {
  entries: LogbookEntry[];
  onDelete: (entryId: string) => Promise<void>;
}

type Filter = "all" | ClimbDiscipline;

const dateFormatter = new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" });

export function LogbookList({ entries, onDelete }: LogbookListProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const [deleting, setDeleting] = useState<string | null>(null);
  const visible = useMemo(
    () => entries.filter((entry) => filter === "all" || entry.climb.discipline === filter),
    [entries, filter],
  );

  async function remove(entryId: string) {
    const entry = entries.find((item) => item.id === entryId);
    if (!window.confirm(`Remove ${entry?.climb.name || "this climb"} from your logbook?`)) return;
    setDeleting(entryId);
    try {
      await onDelete(entryId);
    } finally {
      setDeleting(null);
    }
  }

  return (
    <section id="history" className="card scroll-mt-24 overflow-hidden">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line p-5 sm:p-6">
        <div>
          <p className="eyebrow text-lime">Unified history</p>
          <h2 className="mt-2 text-xl font-extrabold tracking-[-0.04em]">Climbing timeline</h2>
        </div>
        <div className="flex gap-1 rounded-lg bg-ink p-1">
          {(["all", "outdoor", "moonboard"] as Filter[]).map((value) => (
            <button key={value} type="button" className={`filter-button ${filter === value ? "filter-button-active" : ""}`} onClick={() => setFilter(value)}>
              {value === "all" ? "All" : value === "outdoor" ? "Outdoor" : "MoonBoard"}
            </button>
          ))}
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="grid min-h-56 place-items-center p-8 text-center">
          <div>
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-white/[0.04] text-mist"><Mountain size={21} /></div>
            <p className="mt-4 text-sm font-extrabold">No climbs here yet</p>
            <p className="mt-1 text-xs text-mist">Log one above or import your Mountain Project history.</p>
          </div>
        </div>
      ) : (
        <div className="divide-y divide-line">
          {visible.map((entry) => {
            const moonboard = entry.climb.discipline === "moonboard";
            const context = moonboard
              ? [entry.climb.board_name, entry.climb.board_angle ? `${entry.climb.board_angle}°` : null].filter(Boolean).join(" · ")
              : entry.climb.location;
            return (
              <article key={entry.id} className="group grid gap-3 p-4 transition hover:bg-white/[0.018] sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center sm:px-6">
                <div className={`grid h-10 w-10 place-items-center rounded-xl ${moonboard ? "bg-sky-400/10 text-sky-300" : "bg-lime/10 text-lime"}`}>
                  {moonboard ? <Grid3X3 size={18} /> : <Mountain size={18} />}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-extrabold text-chalk">{entry.climb.name}</p>
                    <span className="grade-pill">{entry.climb.grade}</span>
                    <span className={`result-pill ${entry.outcome === "send" ? "result-send" : "result-attempt"}`}>{entry.outcome}</span>
                    {entry.climb.is_benchmark && <span className="benchmark-pill">Benchmark</span>}
                  </div>
                  <p className="mt-1 truncate text-xs text-mist">{dateFormatter.format(new Date(`${entry.climbed_on}T12:00:00`))}{context ? ` · ${context}` : ""}{entry.ascent_type ? ` · ${entry.ascent_type}` : ""}</p>
                  {entry.notes && <p className="mt-2 line-clamp-2 text-xs leading-5 text-mist/80">{entry.notes}</p>}
                </div>
                <div className="flex items-center gap-1 justify-self-end">
                  {entry.climb.external_url && <a className="icon-button" href={entry.climb.external_url} target="_blank" rel="noreferrer" aria-label={`Open ${entry.climb.name} source`}><ExternalLink size={15} /></a>}
                  <button className="icon-button opacity-70 hover:border-red-300/40 hover:text-red-200 sm:opacity-0 sm:group-hover:opacity-100" type="button" aria-label={`Delete ${entry.climb.name} log`} disabled={deleting === entry.id} onClick={() => void remove(entry.id)}><Trash2 size={15} /></button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
