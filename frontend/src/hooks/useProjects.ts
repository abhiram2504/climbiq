import { useCallback, useEffect, useState } from "react";
import {
  addProjectDrill,
  createProject,
  listProjects,
  updateProjectStatus,
} from "../services/api";
import type {
  ClimbingProject,
  CreateProject,
  CreateProjectDrill,
  ProjectStatus,
} from "../types/api";

export function useProjects() {
  const [projects, setProjects] = useState<ClimbingProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const response = await listProjects();
      setProjects(response.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load projects.");
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const addProject = useCallback(async (payload: CreateProject) => {
    const created = await createProject(payload);
    setProjects((current) => [created, ...current]);
    return created;
  }, []);

  const addDrill = useCallback(async (projectId: string, payload: CreateProjectDrill) => {
    const updated = await addProjectDrill(projectId, payload);
    setProjects((current) => current.map((project) => project.id === projectId ? updated : project));
    return updated;
  }, []);

  const setStatus = useCallback(async (projectId: string, status: ProjectStatus) => {
    const updated = await updateProjectStatus(projectId, status);
    setProjects((current) => current.map((project) => project.id === projectId ? updated : project));
    return updated;
  }, []);

  return { projects, loading, error, refresh, addProject, addDrill, setStatus };
}
