import { useEffect, useMemo, useState } from "react";
import { Activity, Database, Film, History, Menu, RefreshCw, Upload, WifiOff, X } from "lucide-react";
import { AccountMenu } from "./components/AccountMenu";
import { AttemptList } from "./components/AttemptList";
import { Brand } from "./components/Brand";
import { LoginPage } from "./components/LoginPage";
import { PWAControls } from "./components/PWAControls";
import { Sidebar } from "./components/Sidebar";
import { StatCard } from "./components/StatCard";
import { UploadPanel } from "./components/UploadPanel";
import { VideoWorkspace } from "./components/VideoWorkspace";
import { useAuth } from "./hooks/useAuth";
import { useClimbData } from "./hooks/useClimbData";
import type { AuthStatus, VideoAttempt } from "./types/api";

const authErrors: Record<string, string> = {
  invalid_state: "That sign-in request is no longer valid. Please try again.",
  expired_flow: "The sign-in request expired. Please try again.",
  authorization_denied: "Google authorization was cancelled.",
  google_verification_failed: "Google could not verify this sign-in. Please try again.",
  unverified_email: "A verified Google email address is required.",
  account_conflict: "That email address is already linked to another Google identity.",
  access_denied: "This private beta is not enabled for that Google account.",
  session_changed: "Your session changed while Gmail was being connected. Please try again.",
  google_account_mismatch: "Connect the same Google account you used to sign in.",
  invalid_flow: "That authorization request was not recognized.",
};

const gmailErrors: Record<string, string> = {
  scope_not_granted: "Read-only Gmail access was not granted.",
  offline_access_not_granted: "Google did not grant durable Gmail access. Please reconnect.",
};

function readCallbackMessage(): string | null {
  const parameters = new URLSearchParams(window.location.search);
  const authError = parameters.get("auth_error");
  const gmailError = parameters.get("gmail_error");
  if (authError) return authErrors[authError] || "Google sign-in could not be completed.";
  if (gmailError) return gmailErrors[gmailError] || "Gmail could not be connected.";
  if (parameters.get("gmail") === "connected") return "Gmail connected with read-only access.";
  return null;
}

function clearCallbackParameters() {
  if (window.location.search) window.history.replaceState({}, "", window.location.pathname);
}

function LoadingScreen() {
  return (
    <main className="grid min-h-screen place-items-center bg-ink text-chalk">
      <div className="text-center">
        <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-line border-t-lime" />
        <p className="mt-4 text-sm font-bold text-mist">Opening your workspace…</p>
      </div>
    </main>
  );
}

interface DashboardProps {
  auth: AuthStatus;
  notice: string | null;
  onLogout: () => Promise<void>;
  onDisconnectGmail: () => Promise<void>;
}

function Dashboard({ auth, notice, onLogout, onDisconnectGmail }: DashboardProps) {
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
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-mist">Indoor bouldering · Private workspace</p>
          </div>
          <div className="flex items-center gap-2">
            <PWAControls />
            <div className="hidden items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-mist md:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${error ? "bg-red-400" : "bg-lime"}`} />
              {error ? "API offline" : "API connected"}
            </div>
            <button type="button" className="icon-button" onClick={() => void refresh()} aria-label="Refresh dashboard">
              <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
            </button>
            <AccountMenu auth={auth} onLogout={onLogout} onDisconnectGmail={onDisconnectGmail} />
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
          {notice && (
            <div
              className={`mb-6 rounded-xl border px-4 py-3 text-sm font-semibold ${notice.includes("connected") ? "border-lime/20 bg-lime/[0.06] text-lime" : "border-red-400/20 bg-red-400/5 text-red-200"}`}
              role={notice.includes("connected") ? "status" : "alert"}
            >
              {notice}
            </div>
          )}
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow text-lime">Technique workspace</p>
              <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.055em] text-chalk sm:text-4xl">Read the movement.</h1>
              <p className="mt-2 max-w-xl text-sm leading-6 text-mist">Upload an attempt to extract body landmarks and review the movement with a measured pose overlay.</p>
            </div>
            <p className="hidden text-right text-xs leading-5 text-mist md:block">Signed in as<br /><span className="font-bold text-chalk">{auth.user?.email}</span></p>
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
            <StatCard label="Analyzed" value={videos.filter((video) => video.status === "completed").length} detail="Pose overlays completed" icon={Activity} />
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

export default function App() {
  const { status, loading, error, refresh, signOut, removeGmail } = useAuth();
  const callbackMessage = useMemo(readCallbackMessage, []);

  useEffect(() => {
    clearCallbackParameters();
    if (callbackMessage?.includes("connected")) void refresh();
  }, [callbackMessage, refresh]);

  if (loading && !status) return <LoadingScreen />;
  if (!status && error) {
    return (
      <LoginPage
        configured={false}
        error={error}
        serverUnavailable
        onRetry={() => void refresh()}
      />
    );
  }
  if (!status?.authenticated) {
    return <LoginPage configured={status?.google_oauth_configured ?? false} error={callbackMessage || error} />;
  }
  return <Dashboard auth={status} notice={callbackMessage} onLogout={signOut} onDisconnectGmail={removeGmail} />;
}
