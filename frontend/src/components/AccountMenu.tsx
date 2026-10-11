import { ChevronDown, LogOut, Mail, Unplug } from "lucide-react";
import { useState } from "react";
import { authRedirectUrl } from "../services/api";
import type { AuthStatus } from "../types/api";

interface AccountMenuProps {
  auth: AuthStatus;
  onLogout: () => Promise<void>;
  onDisconnectGmail: () => Promise<void>;
}

export function AccountMenu({ auth, onLogout, onDisconnectGmail }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const user = auth.user!;

  async function run(action: () => Promise<void>) {
    setWorking(true);
    try {
      await action();
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        className="flex items-center gap-2 rounded-xl border border-line px-2 py-1.5 text-left transition hover:border-mist"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label="Open account menu"
      >
        {user.picture_url ? <img src={user.picture_url} alt="" referrerPolicy="no-referrer" className="h-7 w-7 rounded-lg" /> : <span className="grid h-7 w-7 place-items-center rounded-lg bg-lime text-xs font-black text-ink">{user.display_name.slice(0, 1).toUpperCase()}</span>}
        <span className="hidden max-w-32 truncate text-xs font-bold sm:block">{user.display_name}</span>
        <ChevronDown size={14} className="text-mist" />
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-2xl border border-line bg-panel p-3 shadow-panel">
          <div className="px-2 pb-3 pt-1">
            <p className="truncate text-sm font-extrabold text-chalk">{user.display_name}</p>
            <p className="mt-1 truncate text-xs text-mist">{user.email}</p>
          </div>
          {auth.google_oauth_configured && <div className="rounded-xl border border-line bg-ink/60 p-3">
            <div className="flex items-start gap-3">
              <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${auth.gmail.connected ? "bg-lime/10 text-lime" : "bg-white/5 text-mist"}`}><Mail size={17} /></div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-extrabold text-chalk">Gmail</p>
                <p className="mt-1 truncate text-[11px] text-mist">{auth.gmail.connected ? auth.gmail.email : "Not connected"}</p>
              </div>
              <span className={`mt-1 h-2 w-2 rounded-full ${auth.gmail.connected ? "bg-lime" : "bg-mist/40"}`} />
            </div>
            {auth.gmail.connected ? (
              <button disabled={working} type="button" className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-bold text-mist transition hover:text-chalk disabled:opacity-50" onClick={() => void run(onDisconnectGmail)}><Unplug size={14} /> Disconnect Gmail</button>
            ) : (
              <a className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-lime px-3 py-2 text-xs font-extrabold text-ink transition hover:bg-[#d8ff78]" href={authRedirectUrl("/gmail/connect")}><Mail size={14} /> Connect Gmail</a>
            )}
          </div>}
          {auth.google_oauth_configured && <button disabled={working} type="button" className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold text-mist transition hover:bg-white/[0.04] hover:text-chalk disabled:opacity-50" onClick={() => void run(onLogout)}><LogOut size={14} /> Sign out</button>}
        </div>
      )}
    </div>
  );
}
