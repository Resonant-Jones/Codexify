import { useEffect, useRef } from "react";
import { getBackendOutageRemainingMs } from "@/lib/api";

export type PollOptions = {
  intervalMs: number;
  maxBackoffMs?: number;
  enabled?: boolean;
  onErrorKey?: string;
  logTtlMs?: number;
};

/**
 * Poll an async function using adaptive backoff on failures.
 *
 * - Success resets backoff to the baseline interval.
 * - Failure exponentially increases delay up to maxBackoffMs.
 * - Uses setTimeout (not setInterval) so delay can change per tick.
 */
export function usePollWithBackoff(
  fn: () => Promise<void>,
  opts: PollOptions
): void {
  const {
    intervalMs,
    maxBackoffMs = 60_000,
    enabled = true,
  } = opts;
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!enabled || !Number.isFinite(intervalMs) || intervalMs <= 0) return;

    let cancelled = false;
    let failures = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const schedule = (delayMs: number) => {
      if (cancelled) return;
      timer = setTimeout(() => {
        void tick();
      }, Math.max(0, delayMs));
    };

    const tick = async () => {
      if (cancelled) return;
      try {
        await fnRef.current();
        failures = 0;
        schedule(intervalMs);
      } catch (error: any) {
        failures += 1;
        const retryAfterMs = Number(error?.waitMs ?? 0);
        const outageMs = getBackendOutageRemainingMs();
        const nextDelay = Math.max(
          Math.min(
            intervalMs * Math.pow(2, failures),
            maxBackoffMs
          ),
          Number.isFinite(retryAfterMs) ? Math.max(0, retryAfterMs) : 0,
          outageMs
        );
        schedule(nextDelay);
      }
    };

    const initialOutageMs = getBackendOutageRemainingMs();
    if (initialOutageMs > 0) {
      const boundedInitialDelay = Math.max(
        intervalMs,
        intervalMs * Math.pow(2, failures),
        Math.min(maxBackoffMs, initialOutageMs)
      );
      schedule(boundedInitialDelay);
    } else {
      void tick();
    }

    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };
  }, [enabled, intervalMs, maxBackoffMs]);
}

export default usePollWithBackoff;
