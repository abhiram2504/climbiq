import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { FileVideo2, LoaderCircle, UploadCloud, X } from "lucide-react";
import { formatBytes } from "../lib/format";

interface UploadPanelProps {
  onUpload: (file: File, title?: string) => Promise<unknown>;
}

const MAX_CLIENT_SIZE = 250 * 1024 * 1024;

export function UploadPanel({ onUpload }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState("");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    const extension = candidate.name.split(".").pop()?.toLowerCase();
    if (!extension || !["mp4", "mov"].includes(extension)) {
      setError("Choose an MP4 or MOV video.");
      return;
    }
    if (candidate.size > MAX_CLIENT_SIZE) {
      setError("This video is larger than the default 250 MB limit.");
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
    setError(null);
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  function clearSelection() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function submit() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await onUpload(file, sessionTitle);
      clearSelection();
      setSessionTitle("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="card overflow-hidden" aria-labelledby="upload-title">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <p className="eyebrow">New attempt</p>
          <h2 id="upload-title" className="mt-1 text-lg font-extrabold tracking-tight text-chalk">Add climbing footage</h2>
        </div>
        <span className="rounded-lg border border-line px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-mist">MP4 / MOV</span>
      </div>

      <div className="p-5">
        {!file ? (
          <div
            className={`drop-zone ${dragging ? "drop-zone-active" : ""}`}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-lime/10 text-lime">
              <UploadCloud size={22} aria-hidden="true" />
            </div>
            <p className="mt-4 text-sm font-bold text-chalk">Drop a climbing video here</p>
            <p className="mt-1 text-xs text-mist">or choose a file up to 250 MB</p>
            <button type="button" className="button-secondary mt-5" onClick={() => inputRef.current?.click()}>
              Browse files
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="relative overflow-hidden rounded-xl border border-line bg-black">
              {previewUrl && <video className="aspect-video w-full object-contain" src={previewUrl} controls preload="metadata" />}
              <button
                type="button"
                onClick={clearSelection}
                className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-lg bg-black/70 text-white backdrop-blur hover:bg-black"
                aria-label="Remove selected video"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/[0.025] p-3">
              <FileVideo2 size={18} className="shrink-0 text-lime" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold text-chalk">{file.name}</p>
                <p className="text-xs text-mist">{formatBytes(file.size)}</p>
              </div>
            </div>
            <label className="block">
              <span className="eyebrow">Session name <span className="normal-case tracking-normal text-mist">(optional)</span></span>
              <input
                className="field mt-2"
                value={sessionTitle}
                maxLength={160}
                onChange={(event) => setSessionTitle(event.target.value)}
                placeholder="e.g. Moonboard limit session"
              />
            </label>
            <button type="button" className="button-primary w-full" onClick={() => void submit()} disabled={uploading}>
              {uploading ? <LoaderCircle size={17} className="animate-spin" /> : <UploadCloud size={17} />}
              {uploading ? "Uploading…" : "Upload & analyze"}
            </button>
          </div>
        )}
        {error && <p role="alert" className="mt-3 text-sm font-semibold text-red-300">{error}</p>}
        <input ref={inputRef} type="file" accept="video/mp4,video/quicktime,.mp4,.mov" className="sr-only" onChange={handleInput} />
      </div>
    </section>
  );
}
