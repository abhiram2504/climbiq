import { BarChart3, BookOpen, FileUp, LayoutDashboard, PlusCircle, Target } from "lucide-react";
import { Brand } from "./Brand";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, current: true, href: "#overview" },
  { label: "Projects", icon: Target, href: "#projects" },
  { label: "Log a climb", icon: PlusCircle, href: "#log" },
  { label: "Progress", icon: BarChart3, href: "#progress" },
  { label: "Timeline", icon: BookOpen, href: "#history" },
  { label: "Import", icon: FileUp, href: "#import" },
];

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-line bg-ink px-5 py-6 lg:flex lg:flex-col">
      <Brand />
      <nav className="mt-11 space-y-1" aria-label="Primary navigation">
        {navigation.map(({ label, icon: Icon, current, href }) => (
          <a
            key={label}
            href={href}
            className={`nav-item ${current ? "nav-item-active" : ""}`}
            aria-current={current ? "page" : undefined}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </a>
        ))}
      </nav>
      <div className="mt-auto rounded-2xl border border-line bg-panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <BookOpen size={17} className="text-mist" aria-hidden="true" />
          <span className="rounded-full bg-lime/10 px-2 py-1 text-[9px] font-extrabold uppercase tracking-wider text-lime">Yours</span>
        </div>
        <p className="text-sm font-bold text-chalk">One climbing history</p>
        <p className="mt-1 text-xs leading-5 text-mist">Outdoor days and board sessions share one timeline without losing their source.</p>
      </div>
    </aside>
  );
}
