import * as React from "react";

import { fetchHeartbeatStatus, type HeartbeatStatusResponse } from "@/features/commandCenter/api";

type UseHeartbeatStatusOptions = {
  enabled: boolean;
};

type UseHeartbeatStatusResult = {
  status: HeartbeatStatusResponse | null;
  loading: boolean;
  error: string | null;
  lastCheckedAt: number | null;
  refresh: () => Promise<void>;
};

const POLL_INTERVAL_MS = 30_000; // 30 seconds — heartbeat artifacts change slowly

export default function useHeartbeatStatus({
  enabled,
}: UseHeartbeatStatusOptions): UseHeartbeatStatusResult {
  const [status, setStatus] = React.useState<HeartbeatStatusResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = React.useState<number | null>(null);

  const refresh = React.useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHeartbeatStatus();
      setStatus(data);
      setLastCheckedAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  // Initial fetch
  React.useEffect(() => {
    if (!enabled) return;
    refresh();
  }, [enabled, refresh]);

  // Poll
  React.useEffect(() => {
    if (!enabled) return;
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [enabled, refresh]);

  return { status, loading, error, lastCheckedAt, refresh };
}
