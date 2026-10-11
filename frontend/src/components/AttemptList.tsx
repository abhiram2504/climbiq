import { ChevronRight, Film, Mountain } from "lucide-react";
import { formatBytes, formatDate } from "../lib/format";
import type { VideoAttempt } from "../types/api";
import { StatusPill } from "./StatusPill";

interface AttemptListProps {
  videos: VideoAttempt[];
  selectedId?: string;
  onSelect: (video: VideoAttempt) => void;
}

export function AttemptList({ videos, selectedId, onSelect }: AttemptListProps) {
  return (
    <section className="card overflow-hidden" aria-labelledby="history-title">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <p className="eyebrow">Library</p>
          <h2 id="history-title" className="mt-1 text-lg font-extrabold tracking-tight text-chalk">Recent attempts</h2>
        </div>
        <span className="text-xs font-semibold text-mist">{videos.length} total</span>
      </div>
      {videos.length === 0 ? (
        <div className="grid min-h-64 place-items-center px-6 text-center">
          <div>
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl border border-line text-mist">
              <Mountain size={21} aria-hidden="true" />
            </div>
            <p className="mt-4 text-sm font-bold text-chalk">No attempts yet</p>
            <p className="mt-1 max-w-xs text-xs leading-5 text-mist">Upload your first bouldering video to start a private movement record.</p>
          </div>
        </div>
      ) : (
        <div className="divide-y divide-line">
          {videos.slice(0, 8).map((video) => (
            <button
              type="button"
              key={video.id}
              onClick={() => onSelect(video)}
              className={`group flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-white/[0.025] ${selectedId === video.id ? "bg-white/[0.035]" : ""}`}
            >
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/[0.045] text-mist group-hover:text-lime">
                <Film size={18} aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-bold text-chalk">{video.original_filename}</p>
                  <StatusPill status={video.status} />
                </div>
                <p className="mt-1 text-xs text-mist">{formatDate(video.created_at)} · {formatBytes(video.size_bytes)}</p>
              </div>
              <ChevronRight size={16} className="text-mist transition group-hover:translate-x-0.5 group-hover:text-chalk" aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
