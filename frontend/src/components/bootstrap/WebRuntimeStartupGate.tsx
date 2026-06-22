import React from "react";

import { Button } from "@/components/ui/button";
import {
  getBackendOutageRemainingMs,
  preflightBackendAvailability,
} from "@/lib/api";

type WebRuntimeStartupGateProps = {
  enabled: boolean;
  children: React.ReactNode;
};

const PROBE_TIMEOUT_MS = 4000;
const INITIAL_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 15000;

function formatDetail(detail: string | null): string {
  if (!detail) {
    return "The local backend has not answered yet.";
  }
  return detail;
}

export default function WebRuntimeStartupGate({
  enabled,
  children,
}: WebRuntimeStartupGateProps) {
  const [ready, setReady] = React.useState(() => !enabled);
  const [checking, setChecking] = React.useState(enabled);
  const [detail, setDetail] = React.useState<string | null>(null);
  const [retryNonce, setRetryNonce] = React.useState(0);

  React.useEffect(() => {
    if (!enabled) {
      setReady(true);
      setChecking(false);
      setDetail(null);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const clearTimer = () => {
      if (!timer) return;
      clearTimeout(timer);
      timer = null;
    };

    const probe = async () => {
      setChecking(true);
      const result = await preflightBackendAvailability(PROBE_TIMEOUT_MS);
      if (cancelled) {
        return;
      }

      if (result.ok) {
        clearTimer();
        setReady(true);
        setChecking(false);
        setDetail(null);
        return;
      }

      attempt += 1;
      const nextDetail = result.technicalDetail ?? null;
      setReady(false);
      setChecking(false);
      setDetail(nextDetail);

      const outageDelay = getBackendOutageRemainingMs();
      const backoffDelay = Math.min(
        MAX_RETRY_DELAY_MS,
        INITIAL_RETRY_DELAY_MS * Math.pow(2, Math.max(0, attempt - 1))
      );
      const nextDelay = Math.max(1000, outageDelay || backoffDelay);

      clearTimer();
      timer = setTimeout(() => {
        void probe();
      }, nextDelay);
    };

    void probe();

    return () => {
      cancelled = true;
      clearTimer();
    };
  }, [enabled, retryNonce]);

  const handleRetry = React.useCallback(() => {
    setRetryNonce((current) => current + 1);
  }, []);

  if (!enabled) {
    return <>{children}</>;
  }

  return (
    <div className="relative min-h-screen w-full">
      {children}
      {!ready && (
        <div className="fixed inset-0 z-[1300] flex items-end justify-center p-4 sm:p-6">
          <div
            className="pointer-events-auto w-full max-w-2xl overflow-hidden rounded-[22px] border shadow-2xl backdrop-blur-xl"
            style={{
              borderColor: "var(--panel-border-strong, var(--panel-border))",
              background:
                "linear-gradient(155deg, rgba(12,18,30,0.96), rgba(19,29,42,0.9))",
              color: "var(--text)",
              boxShadow: "0 24px 90px rgba(0,0,0,0.28)",
            }}
          >
            <div
              className="border-b px-5 py-4 sm:px-6"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <span
                className="inline-flex items-center rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.24em]"
                style={{
                  borderColor: "var(--chip-border)",
                  background: "rgba(255,255,255,0.04)",
                  color: "var(--muted)",
                }}
              >
                Local runtime
              </span>
            </div>

            <div className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="space-y-2">
                <h1 className="text-lg font-semibold tracking-[-0.02em] sm:text-xl">
                  Waiting for the backend
                </h1>
                <p
                  className="max-w-xl text-sm leading-6"
                  style={{ color: "var(--muted)" }}
                >
                  The frontend is ready, but the local API has not answered yet.
                </p>
                <p
                  className="max-w-xl text-xs leading-6"
                  style={{ color: "var(--muted)" }}
                >
                  {checking ? "Checking the runtime now." : formatDetail(detail)}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button type="button" onClick={handleRetry} disabled={checking}>
                  {checking ? "Checking..." : "Retry now"}
                </Button>
                <span className="text-xs" style={{ color: "var(--muted)" }}>
                  Automatic retries stay on until the backend is reachable.
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
