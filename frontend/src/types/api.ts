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
