import { Database, FileSpreadsheet, Grid3X3 } from "lucide-react";

export function DataSourceNote() {
  return (
    <section className="card p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/[0.04] text-mist"><Database size={18} /></div>
        <div>
          <p className="eyebrow">Data sources</p>
          <h2 className="mt-2 text-base font-extrabold">Built to keep your history portable</h2>
        </div>
      </div>
      <div className="mt-5 space-y-3 text-xs leading-5 text-mist">
        <div className="flex gap-3"><FileSpreadsheet size={16} className="mt-0.5 shrink-0 text-lime" /><p><strong className="text-chalk">Mountain Project:</strong> import your official tick-list CSV. ClimbIQ stores the route link and your log, without scraping the catalog.</p></div>
        <div className="flex gap-3"><Grid3X3 size={16} className="mt-0.5 shrink-0 text-sky-300" /><p><strong className="text-chalk">MoonBoard 2016 · 40°:</strong> manual logging works now. Catalog search will plug into the same model once a production-safe data source is cleared.</p></div>
      </div>
    </section>
  );
}
