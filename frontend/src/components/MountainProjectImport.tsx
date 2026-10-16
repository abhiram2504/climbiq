import { CheckCircle2, FileUp, LoaderCircle, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";
import type { ImportLogbookResponse } from "../types/api";

interface MountainProjectImportProps {
  onImport: (file: File) => Promise<ImportLogbookResponse>;
}

export function MountainProjectImport({ onImport }: MountainProjectImportProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [working, setWorking] = useState(false);
  const [result, setResult] = useState<ImportLogbookResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function chooseFile(file?: File) {
    if (!file) return;
    setWorking(true);
    setError(null);
    setResult(null);
    try {
      setResult(await onImport(file));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not import this CSV.");
    } finally {
      setWorking(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section id="import" className="card scroll-mt-24 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sky-400/10 text-sky-300">
          <FileUp size={19} />
        </div>
        <div>
          <p className="eyebrow text-sky-300">Bring your history</p>
          <h2 className="mt-2 text-lg font-extrabold tracking-[-0.035em]">Mountain Project CSV</h2>
          <p className="mt-2 text-xs leading-5 text-mist">Export your ticks from Mountain Project, then import the file here. Re-imports safely skip rows already in your logbook.</p>
        </div>
      </div>

      <input ref={inputRef} className="sr-only" type="file" accept=".csv,text/csv" onChange={(event) => void chooseFile(event.target.files?.[0])} />
      <button type="button" className="button-secondary mt-5 w-full" disabled={working} onClick={() => inputRef.current?.click()}>
        {working ? <LoaderCircle size={16} className="animate-spin" /> : <FileUp size={16} />}
        {working ? "Importing…" : "Choose tick export"}
      </button>

      {result && (
        <div className="mt-4 rounded-xl border border-lime/20 bg-lime/[0.06] p-3 text-xs text-lime" role="status">
          <p className="flex items-center gap-2 font-extrabold"><CheckCircle2 size={15} /> Imported {result.imported} · Skipped {result.skipped}</p>
          {result.errors.length > 0 && <p className="mt-2 text-amber-100">{result.errors.length} rows need review.</p>}
        </div>
      )}
      {error && <p className="mt-4 rounded-xl border border-red-400/20 bg-red-400/5 p-3 text-xs text-red-200" role="alert">{error}</p>}

      <p className="mt-4 flex items-center gap-2 text-[11px] leading-5 text-mist"><ShieldCheck size={14} className="shrink-0 text-lime" /> Uses your exported history—no password or scraping.</p>
    </section>
  );
}
