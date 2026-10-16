import {
  CheckCircle2,
  Dumbbell,
  ExternalLink,
  LoaderCircle,
  Mountain,
  Plus,
  RotateCcw,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import type {
  ClimbingProject,
  CreateProject,
  CreateProjectDrill,
  ProjectStatus,
} from "../types/api";

interface ProjectModePanelProps {
  projects: ClimbingProject[];
  loading: boolean;
  error: string | null;
  onCreate: (payload: CreateProject) => Promise<ClimbingProject>;
  onAddDrill: (projectId: string, payload: CreateProjectDrill) => Promise<ClimbingProject>;
  onStatus: (projectId: string, status: ProjectStatus) => Promise<ClimbingProject>;
}

const demandOptions = [
  "crimp",
  "lock-off",
  "compression",
  "body tension",
  "power",
  "power endurance",
  "footwork",
  "confidence",
];

export function ProjectModePanel({
  projects,
  loading,
  error,
  onCreate,
  onAddDrill,
  onStatus,
}: ProjectModePanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [grade, setGrade] = useState("");
  const [location, setLocation] = useState("");
  const [routeType, setRouteType] = useState("Sport");
  const [externalUrl, setExternalUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [demands, setDemands] = useState<string[]>([]);
  const [drillName, setDrillName] = useState("");
  const [drillGrade, setDrillGrade] = useState("");
  const [drillFocus, setDrillFocus] = useState("");

  useEffect(() => {
    if (!selectedId && projects[0]) setSelectedId(projects[0].id);
    if (projects.length === 0 && !loading) setShowCreate(true);
  }, [loading, projects, selectedId]);

  const selected = useMemo(
    () => projects.find((project) => project.id === selectedId) ?? projects[0] ?? null,
    [projects, selectedId],
  );

  function toggleDemand(demand: string) {
    setDemands((current) => current.includes(demand)
      ? current.filter((item) => item !== demand)
      : [...current, demand]);
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setMessage(null);
    try {
      const created = await onCreate({
        name: name.trim(),
        grade: grade.trim(),
        location: location.trim() || null,
        route_type: routeType,
        external_url: externalUrl.trim() || null,
        demand_tags: demands,
        notes: notes.trim() || null,
      });
      setSelectedId(created.id);
      setShowCreate(false);
      setName("");
      setGrade("");
      setLocation("");
      setExternalUrl("");
      setNotes("");
      setDemands([]);
      setMessage("Project created. Add a board drill to build the bridge.");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not create the project.");
    } finally {
      setWorking(false);
    }
  }

  async function addDrill(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setWorking(true);
    setMessage(null);
    try {
      await onAddDrill(selected.id, {
        name: drillName.trim(),
        grade: drillGrade.trim(),
        focus: drillFocus.trim() || null,
      });
      setDrillName("");
      setDrillGrade("");
      setDrillFocus("");
      setMessage("MoonBoard drill attached to this project.");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not attach the drill.");
    } finally {
      setWorking(false);
    }
  }

  async function changeStatus(status: ProjectStatus) {
    if (!selected) return;
    setWorking(true);
    setMessage(null);
    try {
      await onStatus(selected.id, status);
      setMessage(status === "sent" ? "Project marked sent. Nice work." : "Project reopened.");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not update the project.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section id="projects" className="card scroll-mt-24 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-lime/10 text-lime"><Target size={20} /></div>
          <div>
            <p className="eyebrow text-lime">Project mode</p>
            <h2 className="mt-2 text-xl font-extrabold tracking-[-0.04em]">Train for the climb that matters</h2>
            <p className="mt-1 text-xs text-mist">Connect an outdoor objective to focused MoonBoard 2016/40° work.</p>
          </div>
        </div>
        <button className="button-secondary" type="button" onClick={() => setShowCreate((open) => !open)}>
          {showCreate ? <X size={15} /> : <Plus size={15} />}
          {showCreate ? "Close" : "New project"}
        </button>
      </div>

      {showCreate && (
        <form className="border-b border-line bg-white/[0.012] p-5 sm:p-6" onSubmit={create}>
          <div className="grid gap-4 lg:grid-cols-[1.2fr_8rem_1fr_9rem]">
            <label className="space-y-1.5"><span className="field-label">Outdoor route</span><input className="field" required value={name} onChange={(event) => setName(event.target.value)} placeholder="Project name" /></label>
            <label className="space-y-1.5"><span className="field-label">Grade</span><input className="field" required value={grade} onChange={(event) => setGrade(event.target.value)} placeholder="5.12a" /></label>
            <label className="space-y-1.5"><span className="field-label">Area or crag</span><input className="field" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Red River Gorge" /></label>
            <label className="space-y-1.5"><span className="field-label">Type</span><select className="field" value={routeType} onChange={(event) => setRouteType(event.target.value)}><option>Sport</option><option>Trad</option><option>Boulder</option><option>Top rope</option><option>Multi-pitch</option></select></label>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <label className="space-y-1.5"><span className="field-label">Mountain Project URL <span className="normal-case tracking-normal text-mist/60">optional</span></span><input className="field" type="url" value={externalUrl} onChange={(event) => setExternalUrl(event.target.value)} placeholder="https://www.mountainproject.com/route/…" /></label>
            <label className="space-y-1.5"><span className="field-label">Goal note</span><input className="field" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="What needs to change for the send?" /></label>
          </div>
          <fieldset className="mt-4">
            <legend className="field-label">Crux demands</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {demandOptions.map((demand) => <button key={demand} className={`rounded-full border px-3 py-2 text-[10px] font-extrabold capitalize transition ${demands.includes(demand) ? "border-lime/40 bg-lime/10 text-lime" : "border-line text-mist hover:text-chalk"}`} type="button" aria-pressed={demands.includes(demand)} onClick={() => toggleDemand(demand)}>{demand}</button>)}
            </div>
          </fieldset>
          <button className="button-primary mt-5" type="submit" disabled={working}>{working ? <LoaderCircle size={16} className="animate-spin" /> : <Target size={16} />}Create project</button>
        </form>
      )}

      {error && <p className="border-b border-line px-6 py-3 text-xs font-bold text-red-200" role="alert">{error}</p>}
      {message && <p className="border-b border-line px-6 py-3 text-xs font-bold text-lime" role="status">{message}</p>}

      {!selected ? (
        <div className="grid min-h-64 place-items-center p-8 text-center">
          <div><Target className="mx-auto text-mist" size={30} /><p className="mt-4 text-sm font-extrabold">Choose the climb you want to unlock</p><p className="mt-1 text-xs text-mist">Create an outdoor project, then attach board drills that train its crux.</p></div>
        </div>
      ) : (
        <div className="grid xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div className="border-b border-line p-5 sm:p-6 xl:border-b-0 xl:border-r">
            {projects.length > 1 && <label className="mb-5 block max-w-sm space-y-1.5"><span className="field-label">Current project</span><select className="field" value={selected.id} onChange={(event) => setSelectedId(event.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.target_climb.name} · {project.target_climb.grade}{project.status !== "active" ? ` · ${project.status}` : ""}</option>)}</select></label>}
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-2"><h3 className="text-2xl font-extrabold tracking-[-0.045em]">{selected.target_climb.name}</h3><span className="grade-pill">{selected.target_climb.grade}</span><span className={`result-pill ${selected.status === "sent" ? "result-send" : "result-attempt"}`}>{selected.status}</span></div>
                <p className="mt-2 text-xs text-mist">{[selected.target_climb.location, selected.target_climb.route_type].filter(Boolean).join(" · ") || "Outdoor objective"}</p>
                {selected.notes && <p className="mt-3 max-w-xl text-sm leading-6 text-mist/90">{selected.notes}</p>}
              </div>
              <div className="flex gap-2">
                {selected.target_climb.external_url && <a className="icon-button" href={selected.target_climb.external_url} target="_blank" rel="noreferrer" aria-label="Open project source"><ExternalLink size={16} /></a>}
                {selected.status === "active" ? <button className="button-secondary" type="button" disabled={working} onClick={() => void changeStatus("sent")}><CheckCircle2 size={15} />Mark sent</button> : <button className="button-secondary" type="button" disabled={working} onClick={() => void changeStatus("active")}><RotateCcw size={15} />Reopen</button>}
              </div>
            </div>
            {selected.demand_tags.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{selected.demand_tags.map((tag) => <span key={tag} className="rounded-full border border-white/10 bg-white/[0.035] px-2.5 py-1.5 text-[10px] font-bold capitalize text-mist">{tag}</span>)}</div>}

            <div className="mt-6 grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-line bg-ink p-3"><p className="field-label">Outdoor goes</p><p className="mt-2 text-xl font-extrabold">{selected.outdoor_attempts}</p></div>
              <div className="rounded-xl border border-line bg-ink p-3"><p className="field-label">Board logs</p><p className="mt-2 text-xl font-extrabold">{selected.board_sessions}</p></div>
              <div className="rounded-xl border border-line bg-ink p-3"><p className="field-label">Drills sent</p><p className="mt-2 text-xl font-extrabold">{selected.drill_sends}<span className="text-xs text-mist">/{selected.drills.length}</span></p></div>
            </div>

            <div className="mt-5 rounded-xl border border-lime/15 bg-lime/[0.035] p-4">
              <div className="flex items-center justify-between gap-3"><p className="flex items-center gap-2 text-xs font-extrabold text-chalk"><Sparkles size={15} className="text-lime" />Training momentum <span className="font-medium text-mist">heuristic</span></p><span className="text-sm font-extrabold text-lime">{selected.momentum_score}%</span></div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-ink"><div className="h-full rounded-full bg-lime transition-all" style={{ width: `${selected.momentum_score}%` }} /></div>
              <p className="mt-3 text-xs leading-5 text-mist"><strong className="text-chalk">Next:</strong> {selected.next_action}</p>
            </div>
          </div>

          <div className="p-5 sm:p-6">
            <div className="flex items-center justify-between"><div><p className="eyebrow text-sky-300">Training bridge</p><h3 className="mt-2 text-base font-extrabold">MoonBoard drills</h3></div><Dumbbell size={19} className="text-sky-300" /></div>
            <div className="mt-4 space-y-2">
              {selected.drills.length === 0 ? <p className="rounded-xl border border-dashed border-line p-4 text-xs leading-5 text-mist">Add a 2016/40° problem that rehearses a hold type, body position, or energy-system demand from the outdoor crux.</p> : selected.drills.map((drill) => <div key={drill.id} className="flex items-center justify-between gap-3 rounded-xl border border-line bg-ink p-3"><div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate text-xs font-extrabold">{drill.climb.name}</p><span className="grade-pill">{drill.climb.grade}</span></div><p className="mt-1 truncate text-[10px] text-mist">{drill.focus || "2016 · 40° training problem"}</p></div>{drill.sent ? <CheckCircle2 size={17} className="shrink-0 text-lime" /> : <Mountain size={17} className="shrink-0 text-mist" />}</div>)}
            </div>
            {selected.status === "active" && <form className="mt-5 space-y-3 border-t border-line pt-5" onSubmit={addDrill}><div className="grid grid-cols-[1fr_6rem] gap-3"><label className="space-y-1.5"><span className="field-label">Problem name</span><input className="field" required value={drillName} onChange={(event) => setDrillName(event.target.value)} placeholder="MoonBoard problem" /></label><label className="space-y-1.5"><span className="field-label">Grade</span><input className="field" required value={drillGrade} onChange={(event) => setDrillGrade(event.target.value)} placeholder="7A" /></label></div><label className="block space-y-1.5"><span className="field-label">Training focus</span><input className="field" value={drillFocus} onChange={(event) => setDrillFocus(event.target.value)} placeholder="e.g. left-hand lock-off into a high foot" /></label><button className="button-secondary w-full" type="submit" disabled={working}>{working ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />}Attach drill</button></form>}
          </div>
        </div>
      )}
    </section>
  );
}
