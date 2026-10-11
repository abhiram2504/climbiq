import type { AuthStatus, SessionListResponse, VideoAttempt, VideoListResponse } from "../types/api";

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
