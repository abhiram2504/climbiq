import { useCallback, useEffect, useState } from "react";
import { listSessions, listVideos, processVideo, uploadVideo } from "../services/api";
import type { ClimbingSession, VideoAttempt } from "../types/api";

export function useClimbData() {
  const [videos, setVideos] = useState<VideoAttempt[]>([]);
  const [sessions, setSessions] = useState<ClimbingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [videoResult, sessionResult] = await Promise.all([listVideos(), listSessions()]);
      setVideos(videoResult.items);
      setSessions(sessionResult.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reach the ClimbIQ API.");
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(true), 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const addVideo = useCallback(
    async (file: File, title?: string) => {
      const created = await uploadVideo(file, title);
      setVideos((current) => [created, ...current]);
      await refresh(true);
      return created;
    },
    [refresh],
  );

  const retryVideo = useCallback(async (videoId: string) => {
    const updated = await processVideo(videoId);
    setVideos((current) => current.map((video) => (video.id === videoId ? updated : video)));
    return updated;
  }, []);

  return { videos, sessions, loading, error, refresh, addVideo, retryVideo };
}
