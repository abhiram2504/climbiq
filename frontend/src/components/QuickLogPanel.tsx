import { Check, Grid3X3, LoaderCircle, Mountain, Plus } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import type {
  ClimbDiscipline,
  ClimbingProject,
  ClimbOutcome,
  CreateLogbookEntry,
} from "../types/api";

interface QuickLogPanelProps {
  projects: ClimbingProject[];
  onSubmit: (payload: CreateLogbookEntry) => Promise<unknown>;
}

function todayValue() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${today.getFullYear()}-${month}-${day}`;
}

export function QuickLogPanel({ projects, onSubmit }: QuickLogPanelProps) {
  const [discipline, setDiscipline] = useState<ClimbDiscipline>("outdoor");
  const [outcome, setOutcome] = useState<ClimbOutcome>("send");
  const [name, setName] = useState("");
  const [grade, setGrade] = useState("");
  const [location, setLocation] = useState("");
  const [routeType, setRouteType] = useState("Sport");
  const [climbedOn, setClimbedOn] = useState(todayValue);
  const [attempts, setAttempts] = useState("1");
  const [ascentType, setAscentType] = useState("redpoint");
  const [notes, setNotes] = useState("");
  const [externalUrl, setExternalUrl] = useState("");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [projectId, setProjectId] = useState("");
  const activeProjects = useMemo(
    () => projects.filter((project) => project.status === "active"),
    [projects],
  );

  useEffect(() => {
    if (projectId && !activeProjects.some((project) => project.id === projectId)) {
      setProjectId("");
    }
  }, [activeProjects, projectId]);

  function applyProjectTarget(nextProjectId: string) {
    setProjectId(nextProjectId);
    const project = activeProjects.find((item) => item.id === nextProjectId);
    if (!project || discipline !== "outdoor") return;
    setName(project.target_climb.name);
    setGrade(project.target_climb.grade);
    setLocation(project.target_climb.location || "");
    setRouteType(project.target_climb.route_type || "Sport");
    setExternalUrl(project.target_climb.external_url || "");
  }

  function chooseDiscipline(next: ClimbDiscipline) {
    setDiscipline(next);
    setMessage(null);
    const project = activeProjects.find((item) => item.id === projectId);
    if (next === "outdoor" && project) {
      setName(project.target_climb.name);
      setGrade(project.target_climb.grade);
      setLocation(project.target_climb.location || "");
      setRouteType(project.target_climb.route_type || "Sport");
      setExternalUrl(project.target_climb.external_url || "");
    } else if (next === "moonboard") {
      setName("");
      setGrade("");
    }
  }

  function chooseOutcome(next: ClimbOutcome) {
    setOutcome(next);
    setAscentType(next === "send" ? "redpoint" : "project");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setMessage(null);
    try {
      await onSubmit({
        project_id: projectId || null,
        discipline,
        source: discipline === "moonboard" ? "moonboard" : "manual",
        name: name.trim(),
        grade: grade.trim(),
        location: discipline === "outdoor" ? location.trim() || null : null,
        route_type: discipline === "outdoor" ? routeType : null,
        external_url: discipline === "outdoor" ? externalUrl.trim() || null : null,
        board_name: discipline === "moonboard" ? "MoonBoard 2016" : null,
        board_angle: discipline === "moonboard" ? 40 : null,
        climbed_on: climbedOn,
        outcome,
        ascent_type: ascentType || null,
        attempts: Math.max(1, Number(attempts) || 1),
        notes: notes.trim() || null,
      });
      const selectedProject = activeProjects.find((project) => project.id === projectId);
      if (discipline === "outdoor" && selectedProject) {
        setName(selectedProject.target_climb.name);
        setGrade(selectedProject.target_climb.grade);
      } else {
        setName("");
        setGrade("");
      }
      setNotes("");
      setAttempts("1");
      setMessage("Climb added to your timeline.");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not save this climb.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section id="log" className="card scroll-mt-24 p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow text-lime">Quick log</p>
          <h2 className="mt-2 text-xl font-extrabold tracking-[-0.04em]">Record today’s climb</h2>
        </div>
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime/10 text-lime">
          <Plus size={19} />
        </div>
      </div>

      <form className="mt-6 space-y-4" onSubmit={submit}>
        <div className="grid grid-cols-2 gap-2 rounded-xl bg-ink p-1" aria-label="Climb type">
          <button
            type="button"
            className={`segment-button ${discipline === "outdoor" ? "segment-button-active" : ""}`}
            onClick={() => chooseDiscipline("outdoor")}
          >
            <Mountain size={15} /> Outdoor
          </button>
          <button
            type="button"
            className={`segment-button ${discipline === "moonboard" ? "segment-button-active" : ""}`}
            onClick={() => chooseDiscipline("moonboard")}
          >
            <Grid3X3 size={15} /> MoonBoard
          </button>
        </div>

        {activeProjects.length > 0 && (
          <label className="block space-y-1.5">
            <span className="field-label">Training project <span className="normal-case tracking-normal text-mist/60">optional</span></span>
            <select className="field" value={projectId} onChange={(event) => applyProjectTarget(event.target.value)}>
              <option value="">General log — no project</option>
              {activeProjects.map((project) => <option key={project.id} value={project.id}>{project.target_climb.name} · {project.target_climb.grade}</option>)}
            </select>
          </label>
        )}

        <div className="grid gap-3 sm:grid-cols-[1fr_8rem]">
          <label className="space-y-1.5">
            <span className="field-label">Climb name</span>
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} required placeholder={discipline === "outdoor" ? "Route or boulder" : "Problem name"} />
          </label>
          <label className="space-y-1.5">
            <span className="field-label">Grade</span>
            <input className="field" value={grade} onChange={(event) => setGrade(event.target.value)} required placeholder={discipline === "outdoor" ? "5.11a / V5" : "7A"} />
          </label>
        </div>

        {discipline === "outdoor" ? (
          <>
            <div className="grid gap-3 sm:grid-cols-[1fr_9rem]">
              <label className="space-y-1.5">
                <span className="field-label">Area or crag</span>
                <input className="field" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Red River Gorge · The Motherlode" />
              </label>
              <label className="space-y-1.5">
                <span className="field-label">Climb type</span>
                <select className="field" value={routeType} onChange={(event) => setRouteType(event.target.value)}>
                  <option>Sport</option>
                  <option>Trad</option>
                  <option>Boulder</option>
                  <option>Top rope</option>
                  <option>Multi-pitch</option>
                  <option>Ice</option>
                  <option>Mixed</option>
                </select>
              </label>
            </div>
            <label className="block space-y-1.5">
              <span className="field-label">Mountain Project URL <span className="normal-case tracking-normal text-mist/60">optional</span></span>
              <input className="field" type="url" value={externalUrl} onChange={(event) => setExternalUrl(event.target.value)} placeholder="https://www.mountainproject.com/route/…" />
            </label>
          </>
        ) : (
          <div className="grid grid-cols-[1fr_auto] gap-3 rounded-xl border border-sky-300/15 bg-sky-300/[0.04] px-4 py-3" aria-label="MoonBoard setup">
            <div>
              <span className="field-label">Board setup</span>
              <p className="mt-1 text-sm font-bold text-chalk">MoonBoard 2016</p>
            </div>
            <div className="border-l border-line pl-4 text-right">
              <span className="field-label">Angle</span>
              <p className="mt-1 text-sm font-bold text-sky-300">40°</p>
            </div>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="space-y-1.5">
            <span className="field-label">Date</span>
            <input className="field" type="date" value={climbedOn} onChange={(event) => setClimbedOn(event.target.value)} required />
          </label>
          <label className="space-y-1.5">
            <span className="field-label">Result</span>
            <select className="field" value={outcome} onChange={(event) => chooseOutcome(event.target.value as ClimbOutcome)}>
              <option value="send">Sent</option>
              <option value="attempt">Attempted</option>
            </select>
          </label>
          <label className="space-y-1.5">
            <span className="field-label">Goes</span>
            <input className="field" type="number" min="1" max="999" value={attempts} onChange={(event) => setAttempts(event.target.value)} />
          </label>
        </div>

        <label className="block space-y-1.5">
          <span className="field-label">Style</span>
          <select className="field" value={ascentType} onChange={(event) => setAscentType(event.target.value)}>
            {outcome === "send" ? (
              <>
                <option value="onsight">Onsight</option>
                <option value="flash">Flash</option>
                <option value="redpoint">Redpoint</option>
                <option value="repeat">Repeat</option>
              </>
            ) : (
              <>
                <option value="project">Projecting</option>
                <option value="fell/hung">Fell / hung</option>
                <option value="working moves">Working moves</option>
              </>
            )}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="field-label">Notes</span>
          <textarea className="field min-h-24 resize-y" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="What worked? What will you try next time?" maxLength={4000} />
        </label>

        {message && (
          <p className={`flex items-center gap-2 text-xs font-bold ${message.includes("added") ? "text-lime" : "text-red-200"}`} role="status">
            {message.includes("added") && <Check size={14} />}{message}
          </p>
        )}
        <button className="button-primary w-full" type="submit" disabled={working}>
          {working ? <LoaderCircle size={17} className="animate-spin" /> : <Plus size={17} />}
          {working ? "Saving…" : "Add to logbook"}
        </button>
      </form>
    </section>
  );
}
