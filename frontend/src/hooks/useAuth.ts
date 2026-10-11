import { useCallback, useEffect, useState } from "react";
import { disconnectGmail, getAuthStatus, logout } from "../services/api";
import type { AuthStatus } from "../types/api";

export function useAuth() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await getAuthStatus());
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not check your session.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    await logout();
    await refresh();
  }, [refresh]);

  const removeGmail = useCallback(async () => {
    await disconnectGmail();
    await refresh();
  }, [refresh]);

  return { status, loading, error, refresh, signOut, removeGmail };
}
