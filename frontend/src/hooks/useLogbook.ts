import { useCallback, useEffect, useState } from "react";
import {
  createLogbookEntry,
  deleteLogbookEntry,
  getLogbookSummary,
  importMountainProject,
  listLogbook,
} from "../services/api";
import type {
  CreateLogbookEntry,
  ImportLogbookResponse,
  LogbookEntry,
  LogbookSummary,
} from "../types/api";

export function useLogbook() {
  const [entries, setEntries] = useState<LogbookEntry[]>([]);
  const [summary, setSummary] = useState<LogbookSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [logbook, nextSummary] = await Promise.all([listLogbook(), getLogbookSummary()]);
      setEntries(logbook.items);
      setSummary(nextSummary);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reach the ClimbIQ API.");
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const addEntry = useCallback(
    async (payload: CreateLogbookEntry) => {
      const created = await createLogbookEntry(payload);
      setEntries((current) => [created, ...current]);
      await refresh(true);
      return created;
    },
    [refresh],
  );

  const importTicks = useCallback(
    async (file: File): Promise<ImportLogbookResponse> => {
      const result = await importMountainProject(file);
      await refresh(true);
      return result;
    },
    [refresh],
  );

  const removeEntry = useCallback(
    async (entryId: string) => {
      await deleteLogbookEntry(entryId);
      setEntries((current) => current.filter((entry) => entry.id !== entryId));
      await refresh(true);
    },
    [refresh],
  );

  return { entries, summary, loading, error, refresh, addEntry, importTicks, removeEntry };
}
