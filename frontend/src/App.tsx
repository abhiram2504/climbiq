import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Grid3X3,
  Menu,
  Mountain,
  RefreshCw,
  Route,
  WifiOff,
  X,
} from "lucide-react";
import { AccountMenu } from "./components/AccountMenu";
import { Brand } from "./components/Brand";
import { DataSourceNote } from "./components/DataSourceNote";
import { LogbookList } from "./components/LogbookList";
import { LoginPage } from "./components/LoginPage";
import { MountainProjectImport } from "./components/MountainProjectImport";
import { PWAControls } from "./components/PWAControls";
import { ProjectModePanel } from "./components/ProjectModePanel";
import { QuickLogPanel } from "./components/QuickLogPanel";
import { Sidebar } from "./components/Sidebar";
import { StatCard } from "./components/StatCard";
import { useAuth } from "./hooks/useAuth";
import { useLogbook } from "./hooks/useLogbook";
import { useProjects } from "./hooks/useProjects";
import type { AuthStatus, CreateLogbookEntry } from "./types/api";

const ProgressChart = lazy(() =>
  import("./components/ProgressChart").then((module) => ({ default: module.ProgressChart })),
);

const authErrors: Record<string, string> = {
  invalid_state: "That sign-in request is no longer valid. Please try again.",
  expired_flow: "The sign-in request expired. Please try again.",
  authorization_denied: "Google authorization was cancelled.",
  google_verification_failed: "Google could not verify this sign-in. Please try again.",
  unverified_email: "A verified Google email address is required.",
  account_conflict: "That email address is already linked to another Google identity.",
  access_denied: "This private beta is not enabled for that Google account.",
};

function readCallbackMessage(): string | null {
  const parameters = new URLSearchParams(window.location.search);
  const authError = parameters.get("auth_error");
  return authError ? authErrors[authError] || "Google sign-in could not be completed." : null;
}

function clearCallbackParameters() {
  if (window.location.search) window.history.replaceState({}, "", window.location.pathname);
}

function LoadingScreen() {
  return (
    <main className="grid min-h-screen place-items-center bg-ink text-chalk">
      <div className="text-center">
        <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-line border-t-lime" />
        <p className="mt-4 text-sm font-bold text-mist">Opening your logbook…</p>
      </div>
    </main>
  );
}

interface DashboardProps {
  auth: AuthStatus;
  notice: string | null;
  onLogout: () => Promise<void>;
}

function Dashboard({ auth, notice, onLogout }: DashboardProps) {
  const { entries, summary, loading, error, refresh, addEntry, importTicks, removeEntry } = useLogbook();
  const {
    projects,
    loading: projectsLoading,
    error: projectsError,
    refresh: refreshProjects,
    addProject,
    addDrill,
    setStatus,
  } = useProjects();
  const [menuOpen, setMenuOpen] = useState(false);

  async function addLogbookEntry(payload: CreateLogbookEntry) {
    const entry = await addEntry(payload);
    if (payload.project_id) await refreshProjects(true);
    return entry;
  }

  return (
    <div className="flex min-h-screen bg-ink text-chalk">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-ink/90 px-4 backdrop-blur-xl sm:px-7 lg:px-9">
          <div className="lg:hidden"><Brand /></div>
          <div className="hidden lg:block">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-mist">Outdoor + board climbing · One logbook</p>
          </div>
          <div className="flex items-center gap-2">
            <PWAControls />
            <div className="hidden items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-mist md:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${error ? "bg-red-400" : "bg-lime"}`} />
              {error ? "API offline" : "Synced"}
            </div>
            <button type="button" className="icon-button" onClick={() => void refresh()} aria-label="Refresh logbook">
              <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
            </button>
            <AccountMenu auth={auth} onLogout={onLogout} />
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
          <nav className="sticky top-16 z-10 grid grid-cols-4 gap-2 border-b border-line bg-panel p-3 lg:hidden" aria-label="Mobile navigation">
            <a href="#projects" className="mobile-nav-item" onClick={() => setMenuOpen(false)}>Projects</a>
            <a href="#log" className="mobile-nav-item" onClick={() => setMenuOpen(false)}>Log</a>
            <a href="#progress" className="mobile-nav-item" onClick={() => setMenuOpen(false)}>Progress</a>
            <a href="#history" className="mobile-nav-item" onClick={() => setMenuOpen(false)}>History</a>
          </nav>
        )}

        <main id="overview" className="mx-auto max-w-[1540px] scroll-mt-20 px-4 py-7 sm:px-7 lg:px-9 lg:py-9">
          {notice && <div className="mb-6 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm font-semibold text-red-200" role="alert">{notice}</div>}

          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <p className="eyebrow text-lime">Your climbing record</p>
              <h1 className="mt-2 max-w-3xl text-3xl font-extrabold tracking-[-0.055em] text-chalk sm:text-5xl">Every climb tells the story.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-mist">Bring outdoor routes and MoonBoard sessions into one durable timeline, then watch consistency turn into progress.</p>
            </div>
            <p className="hidden text-right text-xs leading-5 text-mist md:block">Welcome back<br /><span className="font-bold text-chalk">{auth.user?.display_name}</span></p>
          </div>

          {error && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm text-red-200" role="alert">
              <WifiOff size={17} className="mt-0.5 shrink-0" />
              <span><strong>Backend unavailable.</strong> {error}</span>
            </div>
          )}

          <div className="mt-8 grid grid-cols-2 gap-3 xl:grid-cols-4">
            <StatCard label="Total sends" value={summary?.total_sends ?? 0} detail={`${summary?.total_entries ?? 0} logbook entries`} icon={CheckCircle2} />
            <StatCard label="Outdoor" value={summary?.outdoor_sends ?? 0} detail={summary?.hardest_outdoor ? `Top grade ${summary.hardest_outdoor}` : "No sends logged yet"} icon={Mountain} />
            <StatCard label="MoonBoard" value={summary?.moonboard_sends ?? 0} detail={summary?.hardest_moonboard ? `Top grade ${summary.hardest_moonboard}` : "No sends logged yet"} icon={Grid3X3} />
            <StatCard label="Days out" value={summary?.days_climbed ?? 0} detail="Distinct climbing days" icon={CalendarDays} />
          </div>

          <div className="mt-5">
            <ProjectModePanel
              projects={projects}
              loading={projectsLoading}
              error={projectsError}
              onCreate={addProject}
              onAddDrill={addDrill}
              onStatus={setStatus}
            />
          </div>

          <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(330px,0.78fr)_minmax(560px,1.22fr)]">
            <QuickLogPanel projects={projects} onSubmit={addLogbookEntry} />
            <div className="space-y-5">
              <Suspense fallback={<div className="card h-[370px] animate-pulse bg-panel" aria-label="Loading progress chart" />}>
                <ProgressChart data={summary?.progress ?? []} />
              </Suspense>
              <div className="grid gap-5 md:grid-cols-2">
                <MountainProjectImport onImport={importTicks} />
                <DataSourceNote />
              </div>
            </div>
          </div>

          <div className="mt-5">
            <LogbookList entries={entries} onDelete={removeEntry} />
          </div>

          <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-line py-6 text-[11px] text-mist/70">
            <span className="flex items-center gap-2"><Route size={14} /> Your history stays attached to your account.</span>
            <span>ClimbIQ · Climbing logbook</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const { status, loading, error, refresh, signOut } = useAuth();
  const callbackMessage = useMemo(readCallbackMessage, []);

  useEffect(() => {
    clearCallbackParameters();
  }, []);

  if (loading && !status) return <LoadingScreen />;
  if (!status && error) return <LoginPage configured={false} error={error} serverUnavailable onRetry={() => void refresh()} />;
  if (!status?.authenticated) return <LoginPage configured={status?.google_oauth_configured ?? false} error={callbackMessage || error} />;
  return <Dashboard auth={status} notice={callbackMessage} onLogout={signOut} />;
}
