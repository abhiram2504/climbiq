import { Mountain } from "lucide-react";

export function Brand() {
  return (
    <div className="flex items-center gap-3" aria-label="ClimbIQ home">
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-ink">
        <Mountain size={21} strokeWidth={2.5} aria-hidden="true" />
      </div>
      <div>
        <p className="text-lg font-extrabold leading-none tracking-[-0.04em] text-chalk">ClimbIQ</p>
        <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.19em] text-mist">Climbing logbook</p>
      </div>
    </div>
  );
}
