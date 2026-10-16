import type {
  AuthStatus,
  ClimbingProject,
  CreateProject,
  CreateProjectDrill,
  CreateLogbookEntry,
  ImportLogbookResponse,
  LogbookEntry,
  LogbookListResponse,
  LogbookSummary,
  ProjectListResponse,
  ProjectStatus,
  SessionListResponse,
  VideoAttempt,
  VideoListResponse,
} from "../types/api";

const API_ROOT = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, { credentials: "include", ...options });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || `Request failed with status ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function authRedirectUrl(path: string): string {
  return `${API_ROOT}/auth${path}`;
}

export function absoluteApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  if (API_ROOT.startsWith("http")) return `${API_ROOT.replace(/\/api$/, "")}${path}`;
  return path;
}

export function listVideos(): Promise<VideoListResponse> {
  return request<VideoListResponse>("/videos");
}

export function listSessions(): Promise<SessionListResponse> {
  return request<SessionListResponse>("/sessions");
}

export async function uploadVideo(file: File, sessionTitle?: string): Promise<VideoAttempt> {
  const body = new FormData();
  body.append("video", file);
  if (sessionTitle?.trim()) body.append("session_title", sessionTitle.trim());
  return request<VideoAttempt>("/videos/upload", { method: "POST", body });
}

export function processVideo(videoId: string): Promise<VideoAttempt> {
  return request<VideoAttempt>(`/videos/${videoId}/process`, { method: "POST" });
}

export function getAuthStatus(): Promise<AuthStatus> {
  return request<AuthStatus>("/auth/me");
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function disconnectGmail(): Promise<void> {
  return request<void>("/auth/gmail", { method: "DELETE" });
}

export function listLogbook(): Promise<LogbookListResponse> {
  return request<LogbookListResponse>("/logbook?limit=500");
}

export function getLogbookSummary(): Promise<LogbookSummary> {
  return request<LogbookSummary>("/logbook/summary");
}

export function createLogbookEntry(payload: CreateLogbookEntry): Promise<LogbookEntry> {
  return request<LogbookEntry>("/logbook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function importMountainProject(file: File): Promise<ImportLogbookResponse> {
  const body = new FormData();
  body.append("file", file);
  return request<ImportLogbookResponse>("/logbook/import/mountain-project", {
    method: "POST",
    body,
  });
}

export function deleteLogbookEntry(entryId: string): Promise<void> {
  return request<void>(`/logbook/${entryId}`, { method: "DELETE" });
}

export function listProjects(): Promise<ProjectListResponse> {
  return request<ProjectListResponse>("/projects");
}

export function createProject(payload: CreateProject): Promise<ClimbingProject> {
  return request<ClimbingProject>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function addProjectDrill(
  projectId: string,
  payload: CreateProjectDrill,
): Promise<ClimbingProject> {
  return request<ClimbingProject>(`/projects/${projectId}/drills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateProjectStatus(
  projectId: string,
  status: ProjectStatus,
): Promise<ClimbingProject> {
  return request<ClimbingProject>(`/projects/${projectId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}
