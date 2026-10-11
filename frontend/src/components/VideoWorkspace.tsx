import { Activity, AlertTriangle, CheckCircle2, LoaderCircle, RefreshCw, ScanLine } from "lucide-react";
import { useEffect, useState } from "react";
import { formatDate } from "../lib/format";
import { absoluteApiUrl } from "../services/api";
import type { VideoAttempt } from "../types/api";
import { StatusPill } from "./StatusPill";

interface VideoWorkspaceProps {
  video?: VideoAttempt;
  onRetry: (videoId: string) => Promise<unknown>;
}

export function VideoWorkspace({ video, onRetry }: VideoWorkspaceProps) {
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const showingAnnotated = Boolean(video?.status === "completed" && video.annotated_url);
  const videoUrl = video
    ? absoluteApiUrl(showingAnnotated && video.annotated_url ? video.annotated_url : video.stream_url)
    : "";

  useEffect(() => {
    setRetryError(null);
    setRetrying(false);
  }, [video?.id]);

  async function retry() {
    if (!video) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetry(video.id);
    } catch (caught) {
      setRetryError(caught instanceof Error ? caught.message : "Could not restart processing.");
    } finally {
      setRetrying(false);
    }
  }

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
                key={`${video.id}:${video.annotated_url ?? "source"}`}
                className="aspect-video w-full object-contain"
                src={videoUrl}
                controls
                preload="metadata"
              >
                Your browser cannot play this video container or codec.
              </video>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-mist">Uploaded {formatDate(video.created_at)}</p>
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mist">
                <ScanLine size={14} aria-hidden="true" /> {showingAnnotated ? "Pose overlay" : "Original video"}
              </span>
            </div>
            {(video.status === "queued" || video.status === "processing") && (
              <div className="mt-5 rounded-xl border border-lime/20 bg-lime/[0.035] px-4 py-5">
                <div className="flex gap-3">
                  <LoaderCircle size={18} className="mt-0.5 shrink-0 animate-spin text-lime" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-bold text-chalk">
                      {video.status === "queued" ? "Waiting to analyze pose" : "Detecting body landmarks"}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-mist">
                      Keep the app running while ClimbIQ builds the annotated review video.
                    </p>
                    {video.progress_percent !== null && (
                      <div className="mt-3">
                        <div className="mb-1 flex justify-between text-[10px] font-bold uppercase tracking-wider text-mist">
                          <span>Processing</span><span>{video.progress_percent}%</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full bg-lime transition-all" style={{ width: `${video.progress_percent}%` }} />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            {video.status === "completed" && (
              <div className="mt-5 rounded-xl border border-lime/20 bg-lime/[0.035] px-4 py-5">
                <div className="flex gap-3">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-lime" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-bold text-chalk">Pose extraction complete</p>
                    <p className="mt-1 text-xs leading-5 text-mist">
                      The player shows the measured pose overlay. Joint angles and technique observations arrive in Phase 3.
                    </p>
                  </div>
                </div>
              </div>
            )}
            {video.status === "failed" && (
              <div className="mt-5 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-5">
                <div className="flex gap-3">
                  <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-300" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-bold text-chalk">Pose processing failed</p>
                    <p className="mt-1 break-words text-xs leading-5 text-mist">
                      {video.error_message || "ClimbIQ could not process this video."}
                    </p>
                    <button type="button" className="button-secondary mt-3" onClick={() => void retry()} disabled={retrying}>
                      {retrying ? <LoaderCircle size={15} className="animate-spin" /> : <RefreshCw size={15} />}
                      {retrying ? "Restarting…" : "Retry processing"}
                    </button>
                    {retryError && <p role="alert" className="mt-2 text-xs font-semibold text-red-300">{retryError}</p>}
                  </div>
                </div>
              </div>
            )}
            {video.status === "uploaded" && (
              <div className="mt-5 rounded-xl border border-dashed border-line bg-white/[0.018] px-4 py-5">
                <div className="flex gap-3">
                  <Activity size={18} className="mt-0.5 shrink-0 text-lime" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-bold text-chalk">Ready for pose processing</p>
                    <p className="mt-1 text-xs leading-5 text-mist">Start processing to build the landmark track and overlay.</p>
                    <button type="button" className="button-secondary mt-3" onClick={() => void retry()} disabled={retrying}>
                      {retrying ? <LoaderCircle size={15} className="animate-spin" /> : <ScanLine size={15} />}
                      {retrying ? "Starting…" : "Analyze pose"}
                    </button>
                    {retryError && <p role="alert" className="mt-2 text-xs font-semibold text-red-300">{retryError}</p>}
                  </div>
                </div>
              </div>
            )}
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
