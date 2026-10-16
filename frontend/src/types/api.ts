export type ProcessingStatus = "uploaded" | "queued" | "processing" | "completed" | "failed";

export interface VideoAttempt {
  id: string;
  session_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  source_fps: number | null;
  status: ProcessingStatus;
  error_message: string | null;
  progress_percent: number | null;
  created_at: string;
  updated_at: string;
  stream_url: string;
  status_url: string;
  analysis_url: string;
  annotated_url: string | null;
}

export interface VideoListResponse {
  items: VideoAttempt[];
  total: number;
}

export interface ClimbingSession {
  id: string;
  title: string;
  notes: string | null;
  created_at: string;
  attempt_count: number;
}

export interface SessionListResponse {
  items: ClimbingSession[];
  total: number;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  picture_url: string | null;
}

export interface GmailConnection {
  connected: boolean;
  email: string | null;
  scopes: string[];
  connected_at: string | null;
}

export interface AuthStatus {
  authenticated: boolean;
  google_oauth_configured: boolean;
  user: AuthUser | null;
  gmail: GmailConnection;
}

export type ClimbSource = "manual" | "mountain_project" | "moonboard";
export type ClimbDiscipline = "outdoor" | "moonboard";
export type ClimbOutcome = "attempt" | "send";
export type ProjectStatus = "active" | "sent" | "archived";

export interface Climb {
  id: string;
  source: ClimbSource;
  discipline: ClimbDiscipline;
  external_id: string | null;
  name: string;
  grade: string;
  grade_system: string | null;
  location: string | null;
  route_type: string | null;
  external_url: string | null;
  pitches: number | null;
  length_ft: number | null;
  board_name: string | null;
  board_angle: number | null;
  setter: string | null;
  is_benchmark: boolean;
}

export interface LogbookEntry {
  id: string;
  project_id: string | null;
  climbed_on: string;
  outcome: ClimbOutcome;
  ascent_type: string | null;
  attempts: number;
  rating: number | null;
  notes: string | null;
  import_source: string | null;
  created_at: string;
  climb: Climb;
}

export interface LogbookListResponse {
  items: LogbookEntry[];
  total: number;
}

export interface CreateLogbookEntry {
  project_id?: string | null;
  discipline: ClimbDiscipline;
  source: ClimbSource;
  external_id?: string | null;
  name: string;
  grade: string;
  grade_system?: string | null;
  location?: string | null;
  route_type?: string | null;
  external_url?: string | null;
  board_name?: string | null;
  board_angle?: number | null;
  setter?: string | null;
  is_benchmark?: boolean;
  climbed_on: string;
  outcome: ClimbOutcome;
  ascent_type?: string | null;
  attempts: number;
  rating?: number | null;
  notes?: string | null;
}

export interface ImportLogbookResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface ProgressPoint {
  period: string;
  outdoor: number;
  moonboard: number;
  attempts: number;
}

export interface LogbookSummary {
  total_entries: number;
  total_sends: number;
  outdoor_sends: number;
  moonboard_sends: number;
  days_climbed: number;
  hardest_outdoor: string | null;
  hardest_moonboard: string | null;
  progress: ProgressPoint[];
}

export interface ProjectDrill {
  id: string;
  focus: string | null;
  created_at: string;
  climb: Climb;
  sent: boolean;
}

export interface ClimbingProject {
  id: string;
  status: ProjectStatus;
  demand_tags: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
  target_climb: Climb;
  drills: ProjectDrill[];
  outdoor_attempts: number;
  board_sessions: number;
  drill_sends: number;
  momentum_score: number;
  next_action: string;
  last_activity: string | null;
}

export interface ProjectListResponse {
  items: ClimbingProject[];
}

export interface CreateProject {
  name: string;
  grade: string;
  location?: string | null;
  route_type?: string | null;
  external_url?: string | null;
  demand_tags: string[];
  notes?: string | null;
}

export interface CreateProjectDrill {
  name: string;
  grade: string;
  focus?: string | null;
}
