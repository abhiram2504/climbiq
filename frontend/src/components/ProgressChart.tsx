import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ProgressPoint } from "../types/api";

interface ProgressChartProps {
  data: ProgressPoint[];
}

const monthFormatter = new Intl.DateTimeFormat("en", { month: "short" });

export function ProgressChart({ data }: ProgressChartProps) {
  const chartData = data.map((point) => ({
    ...point,
    label: monthFormatter.format(new Date(`${point.period}-02T12:00:00`)),
  }));

  return (
    <section id="progress" className="card scroll-mt-24 p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow text-lime">Last 12 months</p>
          <h2 className="mt-2 text-xl font-extrabold tracking-[-0.04em]">Your climbing rhythm</h2>
          <p className="mt-2 text-xs leading-5 text-mist">Sends by discipline, with unfinished attempts kept visible.</p>
        </div>
        <BarChart3 size={19} className="text-mist" />
      </div>
      <div className="mt-6 h-64 w-full" aria-label="Monthly climbing progress chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 0, left: -28, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#292e2c" strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fill: "#9ba5a0", fontSize: 10 }} tickLine={false} axisLine={false} interval={1} />
            <YAxis allowDecimals={false} tick={{ fill: "#9ba5a0", fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "#151818", border: "1px solid #292e2c", borderRadius: 12, color: "#f1f3ed", fontSize: 12 }} cursor={{ fill: "rgba(255,255,255,0.025)" }} />
            <Bar dataKey="outdoor" name="Outdoor sends" stackId="sends" fill="#c8ff3d" radius={[3, 3, 0, 0]} />
            <Bar dataKey="moonboard" name="MoonBoard sends" stackId="sends" fill="#5fd7ff" radius={[3, 3, 0, 0]} />
            <Bar dataKey="attempts" name="Attempts" fill="#565e5a" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-[10px] font-bold uppercase tracking-wider text-mist">
        <span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-lime" /> Outdoor</span>
        <span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-sky-300" /> MoonBoard</span>
        <span className="flex items-center gap-2"><i className="h-2 w-2 rounded-full bg-[#565e5a]" /> Attempts</span>
      </div>
    </section>
  );
}
