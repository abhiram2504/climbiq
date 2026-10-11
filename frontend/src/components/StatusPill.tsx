import { Check, CircleDashed, Clock3, UploadCloud, X } from "lucide-react";
import type { ProcessingStatus } from "../types/api";

const statusConfig = {
  uploaded: { label: "Ready", icon: UploadCloud, className: "status-neutral" },
  queued: { label: "Queued", icon: Clock3, className: "status-neutral" },
  processing: { label: "Analyzing", icon: CircleDashed, className: "status-working" },
  completed: { label: "Complete", icon: Check, className: "status-complete" },
  failed: { label: "Failed", icon: X, className: "status-error" },
} satisfies Record<ProcessingStatus, { label: string; icon: typeof Check; className: string }>;

export function StatusPill({ status }: { status: ProcessingStatus }) {
  const config = statusConfig[status];
  const Icon = config.icon;
  return (
    <span className={`status-pill ${config.className}`}>
      <Icon size={12} aria-hidden="true" />
      {config.label}
    </span>
  );
}
