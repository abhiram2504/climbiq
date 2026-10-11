import { BarChart3, History, LayoutDashboard, Settings2, Upload } from "lucide-react";
import { Brand } from "./Brand";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, current: true, href: "#overview" },
  { label: "Upload", icon: Upload, href: "#upload" },
  { label: "Sessions", icon: History, href: "#sessions" },
  { label: "Comparisons", icon: BarChart3, soon: true },
];

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-line bg-ink px-5 py-6 lg:flex lg:flex-col">
      <Brand />
      <nav className="mt-11 space-y-1" aria-label="Primary navigation">
        {navigation.map(({ label, icon: Icon, current, soon, href }) =>
          soon ? (
            <button key={label} type="button" className="nav-item" disabled>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
              <span className="ml-auto text-[9px] font-bold uppercase tracking-widest text-mist">Soon</span>
            </button>
          ) : (
            <a
              key={label}
              href={href}
              className={`nav-item ${current ? "nav-item-active" : ""}`}
              aria-current={current ? "page" : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </a>
          ),
        )}
      </nav>
      <div className="mt-auto rounded-2xl border border-line bg-panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <Settings2 size={17} className="text-mist" aria-hidden="true" />
          <span className="rounded-full bg-lime/10 px-2 py-1 text-[9px] font-extrabold uppercase tracking-wider text-lime">
            Local
          </span>
        </div>
        <p className="text-sm font-bold text-chalk">Private by default</p>
        <p className="mt-1 text-xs leading-5 text-mist">Videos stay on this machine during development.</p>
      </div>
    </aside>
  );
}
