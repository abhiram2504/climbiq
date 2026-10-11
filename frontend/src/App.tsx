import { useEffect, useState } from "react";
import { Activity, Database, Film, History, Menu, RefreshCw, Upload, WifiOff, X } from "lucide-react";
import { AttemptList } from "./components/AttemptList";
import { Brand } from "./components/Brand";
import { Sidebar } from "./components/Sidebar";
import { StatCard } from "./components/StatCard";
import { UploadPanel } from "./components/UploadPanel";
import { VideoWorkspace } from "./components/VideoWorkspace";
import { useClimbData } from "./hooks/useClimbData";
import type { VideoAttempt } from "./types/api";

export default function App() {
  const { videos, sessions, loading, error, refresh, addVideo, retryVideo } = useClimbData();
  const [selected, setSelected] = useState<VideoAttempt | undefined>();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!selected && videos.length > 0) setSelected(videos[0]);
    if (selected) {
      const updated = videos.find((video) => video.id === selected.id);
      if (updated && updated !== selected) setSelected(updated);
    }
  }, [selected, videos]);

  async function handleUpload(file: File, title?: string) {
    const created = await addVideo(file, title);
    setSelected(created);
  }

  async function handleRetry(videoId: string) {
    const updated = await retryVideo(videoId);
    setSelected(updated);
  }

  return (
    <div className="flex min-h-screen bg-ink text-chalk">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-ink/90 px-4 backdrop-blur-xl sm:px-7 lg:px-9">
          <div className="lg:hidden"><Brand /></div>
          <div className="hidden lg:block">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-mist">Indoor bouldering · Local workspace</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-mist sm:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${error ? "bg-red-400" : "bg-lime"}`} />
              {error ? "API offline" : "API connected"}
            </div>
            <button type="button" className="icon-button" onClick={() => void refresh()} aria-label="Refresh dashboard">
              <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              type="button"
              className="icon-button lg:hidden"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </header>

        {menuOpen && (
          <nav className="sticky top-16 z-10 grid grid-cols-3 gap-2 border-b border-line bg-panel p-3 lg:hidden" aria-label="Mobile navigation">
            <a href="#overview" className="mobile-nav-item" onClick={() => setMenuOpen(false)}>Overview</a>
            <a href="#upload" className="mobile-nav-item" onClick={() => setMenuOpen(false)}><Upload size={14} /> Upload</a>
            <a href="#sessions" className="mobile-nav-item" onClick={() => setMenuOpen(false)}><History size={14} /> Sessions</a>
          </nav>
        )}

        <main id="overview" className="mx-auto max-w-[1540px] scroll-mt-20 px-4 py-7 sm:px-7 lg:px-9 lg:py-9">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow text-lime">Technique workspace</p>
              <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-chalk sm:text-4xl">Read the movement.</h1>
              <p className="mt-2 max-w-xl text-sm leading-6 text-mist">Upload an attempt to extract body landmarks and review the movement with a measured pose overlay.</p>
            </div>
            <p className="hidden text-right text-xs leading-5 text-mist md:block">Single-user MVP<br />Data stays local</p>
          </div>

          {error && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm text-red-200" role="alert">
              <WifiOff size={17} className="mt-0.5 shrink-0" />
              <span><strong>Backend unavailable.</strong> {error}</span>
            </div>
          )}

          <div className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatCard label="Attempts" value={videos.length} detail="Videos in your library" icon={Film} />
            <StatCard label="Sessions" value={sessions.length} detail="Grouped climbing days" icon={Database} />
            <StatCard
              label="Analyzed"
              value={videos.filter((video) => video.status === "completed").length}
              detail="Pose overlays completed"
              icon={Activity}
            />
          </div>

          <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(310px,0.72fr)_minmax(520px,1.28fr)]">
            <div className="space-y-5">
              <div id="upload" className="scroll-mt-20"><UploadPanel onUpload={handleUpload} /></div>
              <div id="sessions" className="scroll-mt-20"><AttemptList videos={videos} selectedId={selected?.id} onSelect={setSelected} /></div>
            </div>
            <VideoWorkspace video={selected} onRetry={handleRetry} />
          </div>
        </main>
      </div>
    </div>
  );
}
