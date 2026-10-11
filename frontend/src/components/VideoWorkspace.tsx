import { Activity, ScanLine } from "lucide-react";
import { formatDate } from "../lib/format";
import { absoluteApiUrl } from "../services/api";
import type { VideoAttempt } from "../types/api";
import { StatusPill } from "./StatusPill";

export function VideoWorkspace({ video }: { video?: VideoAttempt }) {
  return (
    <section className="card overflow-hidden" aria-labelledby="workspace-title">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <p className="eyebrow">Review</p>
          <h2 id="workspace-title" className="mt-1 max-w-md truncate text-lg font-extrabold tracking-tight text-chalk">
            {video?.original_filename ?? "Select an attempt"}
          </h2>
        </div>
        {video && <StatusPill status={video.status} />}
      </div>
      <div className="p-5">
        {video ? (
          <>
            <div className="overflow-hidden rounded-xl border border-line bg-black">
              <video
                key={video.id}
                className="aspect-video w-full object-contain"
                src={absoluteApiUrl(video.stream_url)}
                controls
                preload="metadata"
              >
                Your browser cannot play this video container or codec.
              </video>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-mist">Uploaded {formatDate(video.created_at)}</p>
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mist">
                <ScanLine size={14} aria-hidden="true" /> Pose overlay arrives in Phase 2
              </span>
            </div>
            <div className="mt-5 rounded-xl border border-dashed border-line bg-white/[0.018] px-4 py-5">
              <div className="flex gap-3">
                <Activity size={18} className="mt-0.5 shrink-0 text-lime" aria-hidden="true" />
                <div>
                  <p className="text-sm font-bold text-chalk">Movement analysis not started</p>
                  <p className="mt-1 text-xs leading-5 text-mist">
                    Phase 2 will add pose landmarks and annotated video. Phase 3 will calculate joint angles and motion intervals from those measurements.
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="grid min-h-[420px] place-items-center text-center">
            <div>
              <ScanLine size={30} className="mx-auto text-mist" aria-hidden="true" />
              <p className="mt-4 text-sm font-bold text-chalk">Your review space is ready</p>
              <p className="mt-1 text-xs text-mist">Upload or select an attempt to play it here.</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
