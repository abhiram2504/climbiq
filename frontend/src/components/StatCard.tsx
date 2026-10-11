import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
}

export function StatCard({ label, value, detail, icon: Icon }: StatCardProps) {
  return (
    <article className="card flex min-h-32 flex-col justify-between p-5">
      <div className="flex items-start justify-between">
        <p className="eyebrow">{label}</p>
        <Icon size={18} className="text-mist" aria-hidden="true" />
      </div>
      <div>
        <p className="text-3xl font-extrabold tracking-[-0.05em] text-chalk">{value}</p>
        <p className="mt-1 text-xs text-mist">{detail}</p>
      </div>
    </article>
  );
}
