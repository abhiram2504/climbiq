import { ArrowRight, BookOpenCheck, Check, LockKeyhole, RefreshCw } from "lucide-react";
import { authRedirectUrl } from "../services/api";
import { Brand } from "./Brand";

interface LoginPageProps {
  configured: boolean;
  error?: string | null;
  serverUnavailable?: boolean;
  onRetry?: () => void;
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.9h5.4a4.7 4.7 0 0 1-2 3v2.6h3.3c1.9-1.8 2.9-4.4 2.9-7.5Z" />
      <path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.3l-3.3-2.6c-.9.6-2.1 1-3.4 1a5.9 5.9 0 0 1-5.5-4.1H3.1v2.7A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.5 14a6 6 0 0 1 0-3.9V7.4H3.1a10 10 0 0 0 0 9.3L6.5 14Z" />
      <path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.9 1.5l2.9-2.9A9.7 9.7 0 0 0 12 2a10 10 0 0 0-8.9 5.4l3.4 2.7A5.9 5.9 0 0 1 12 6Z" />
    </svg>
  );
}

export function LoginPage({ configured, error, serverUnavailable = false, onRetry }: LoginPageProps) {
  return (
    <main className="relative grid min-h-screen overflow-hidden bg-ink text-chalk lg:grid-cols-[1.1fr_0.9fr]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(200,255,61,0.09),transparent_30rem)]" />
      <section className="relative flex min-h-[46vh] flex-col justify-between border-b border-line p-7 sm:p-10 lg:min-h-screen lg:border-b-0 lg:border-r lg:p-14">
        <Brand />
        <div className="my-14 max-w-2xl lg:my-0">
          <p className="eyebrow text-lime">Your climbing history</p>
          <h1 className="mt-5 max-w-xl text-5xl font-extrabold leading-[0.98] tracking-[-0.065em] sm:text-6xl">
            Outside or on the board.<br />It all counts.
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-mist">
            Keep outdoor routes, MoonBoard attempts, sends, projects, and progress together in one durable logbook.
          </p>
        </div>
        <div className="hidden items-center gap-6 text-xs font-bold uppercase tracking-[0.14em] text-mist sm:flex">
          <span className="flex items-center gap-2"><Check size={14} className="text-lime" /> Private workspace</span>
          <span className="flex items-center gap-2"><Check size={14} className="text-lime" /> Portable history</span>
        </div>
      </section>

      <section className="relative flex items-center justify-center p-6 sm:p-10">
        <div className="card w-full max-w-md p-6 sm:p-8">
          <div className="grid h-12 w-12 place-items-center rounded-xl border border-lime/20 bg-lime/[0.07] text-lime">
            <LockKeyhole size={22} />
          </div>
          <h2 className="mt-6 text-2xl font-extrabold tracking-[-0.04em]">
            {serverUnavailable ? "Workspace unavailable" : "Welcome to ClimbIQ"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-mist">
            {serverUnavailable
              ? "ClimbIQ could not reach the logbook server. Your saved history is unaffected."
              : "Sign in with Google to open your climbing logbook."}
          </p>

          {error && <div className="mt-5 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm text-red-200" role="alert">{error}</div>}

          {serverUnavailable ? (
            <button
              className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-lime px-4 py-3.5 text-sm font-extrabold text-ink transition hover:bg-[#d8ff78]"
              type="button"
              onClick={onRetry}
            >
              <RefreshCw size={17} /> Try again
            </button>
          ) : configured ? (
            <a
              className="mt-7 flex w-full items-center justify-between rounded-xl border border-line bg-white px-4 py-3.5 text-sm font-extrabold text-[#171918] transition hover:bg-[#f1f3ed]"
              href={authRedirectUrl("/google/login")}
            >
              <span className="flex items-center gap-3"><GoogleMark /> Continue with Google</span>
              <ArrowRight size={17} />
            </a>
          ) : (
            <button
              className="mt-7 flex w-full items-center justify-between rounded-xl border border-line bg-white/5 px-4 py-3.5 text-sm font-extrabold text-mist"
              type="button"
              disabled
            >
              <span className="flex items-center gap-3"><GoogleMark /> Continue with Google</span>
              <ArrowRight size={17} />
            </button>
          )}

          {!configured && !serverUnavailable && (
            <p className="mt-4 rounded-xl border border-amber-300/15 bg-amber-300/[0.05] px-4 py-3 text-xs leading-5 text-amber-100">
              Google sign-in needs server credentials. Add them to your environment, then restart the backend.
            </p>
          )}

          {!serverUnavailable && <div className="mt-7 flex gap-3 border-t border-line pt-6 text-xs leading-5 text-mist">
            <BookOpenCheck size={17} className="mt-0.5 shrink-0 text-lime" />
            <p>Your outdoor and board records are isolated to your account and can be imported without sharing provider passwords.</p>
          </div>}
        </div>
      </section>
    </main>
  );
}
