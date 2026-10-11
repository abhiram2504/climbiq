import { Download, RefreshCw, Share, Smartphone, WifiOff, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

function isStandalone(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches
    || Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
}

export function PWAControls() {
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [installed, setInstalled] = useState(isStandalone);
  const isIOS = useMemo(
    () => /iphone|ipad|ipod/i.test(window.navigator.userAgent),
    [],
  );
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  useEffect(() => {
    const capturePrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    const markInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
      setShowInstructions(false);
    };
    window.addEventListener("beforeinstallprompt", capturePrompt);
    window.addEventListener("appinstalled", markInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", capturePrompt);
      window.removeEventListener("appinstalled", markInstalled);
    };
  }, []);

  async function install() {
    if (installPrompt) {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      if (choice.outcome === "accepted") setInstalled(true);
      setInstallPrompt(null);
      return;
    }
    setShowInstructions(true);
  }

  const dismissUpdate = () => {
    setOfflineReady(false);
    setNeedRefresh(false);
  };

  return (
    <>
      {!installed && (
        <button type="button" className="install-button" onClick={() => void install()}>
          <Download size={15} />
          <span className="hidden sm:inline">Install app</span>
        </button>
      )}

      {showInstructions && (
        <div className="fixed inset-0 z-50 grid place-items-end bg-black/70 p-3 sm:place-items-center" role="dialog" aria-modal="true" aria-labelledby="install-title">
          <div className="card w-full max-w-md p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-lime text-ink">
                <Smartphone size={21} />
              </div>
              <button type="button" className="icon-button" aria-label="Close install instructions" onClick={() => setShowInstructions(false)}>
                <X size={18} />
              </button>
            </div>
            <h2 id="install-title" className="mt-5 text-xl font-extrabold tracking-tight text-chalk">Install ClimbIQ</h2>
            {isIOS ? (
              <p className="mt-2 text-sm leading-6 text-mist">
                In Safari, tap <span className="inline-flex items-center gap-1 font-bold text-chalk"><Share size={15} /> Share</span>, then choose <strong className="text-chalk">Add to Home Screen</strong>.
              </p>
            ) : (
              <p className="mt-2 text-sm leading-6 text-mist">
                Open your browser menu and choose <strong className="text-chalk">Install ClimbIQ</strong> or <strong className="text-chalk">Add to Home Screen</strong>.
              </p>
            )}
            <p className="mt-4 rounded-xl border border-line bg-white/[0.025] p-3 text-xs leading-5 text-mist">
              Installation requires the hosted HTTPS version. Local network addresses may not offer installation on every phone.
            </p>
          </div>
        </div>
      )}

      {(offlineReady || needRefresh) && (
        <div className="fixed bottom-4 left-4 right-4 z-40 mx-auto flex max-w-lg items-center gap-3 rounded-xl border border-line bg-panel p-3 shadow-panel" role="status">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-lime/10 text-lime">
            {needRefresh ? <RefreshCw size={17} /> : <WifiOff size={17} />}
          </div>
          <p className="min-w-0 flex-1 text-xs leading-5 text-mist">
            {needRefresh ? "A new ClimbIQ version is ready." : "ClimbIQ is ready to open offline. Video analysis still requires a connection."}
          </p>
          {needRefresh && (
            <button type="button" className="button-secondary" onClick={() => void updateServiceWorker(true)}>Update</button>
          )}
          <button type="button" className="icon-button shrink-0" aria-label="Dismiss" onClick={dismissUpdate}><X size={16} /></button>
        </div>
      )}
    </>
  );
}
