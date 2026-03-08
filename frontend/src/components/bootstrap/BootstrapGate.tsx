import React from "react";

import { Button } from "@/components/ui/button";
import type { RuntimeBootstrapState } from "@/lib/runtimeBootstrap";

type BootstrapGateProps = {
  state: RuntimeBootstrapState;
  onRetry: () => void;
  onInstallDocker: () => Promise<void> | void;
  onContinue: () => void;
};

type CheckRowProps = {
  label: string;
  value: boolean | null;
  successLabel: string;
  failureLabel: string;
};

function CheckRow({
  label,
  value,
  successLabel,
  failureLabel,
}: CheckRowProps) {
  const pending = value == null;
  const tone = pending
    ? "rgba(255,255,255,0.58)"
    : value
    ? "var(--accent-strong, #7dd3fc)"
    : "var(--danger-text, #fca5a5)";

  return (
    <div
      className="rounded-[18px] border px-4 py-3"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
      }}
    >
      <div className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
        {label}
      </div>
      <div className="mt-2 text-sm font-medium" style={{ color: tone }}>
        {pending ? "Pending" : value ? successLabel : failureLabel}
      </div>
    </div>
  );
}

export default function BootstrapGate({
  state,
  onRetry,
  onInstallDocker,
  onContinue,
}: BootstrapGateProps) {
  const [openingInstallPage, setOpeningInstallPage] = React.useState(false);
  const isChecking = state.status === "checking";
  const showInstallAction = state.status === "docker-missing";
  const showRetryAction =
    state.status === "docker-missing" ||
    state.status === "compose-missing" ||
    state.status === "docker-not-running" ||
    state.status === "error";
  const showContinueAction = state.status === "ready";
  const openDetailsByDefault =
    Boolean(state.detail) && !isChecking && state.status !== "ready";

  const handleInstallDocker = React.useCallback(async () => {
    setOpeningInstallPage(true);
    try {
      await onInstallDocker();
    } finally {
      setOpeningInstallPage(false);
    }
  }, [onInstallDocker]);

  const preflight = state.preflight;

  return (
    <div
      className="flex h-full w-full items-center justify-center p-6 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bootstrap-gate-title"
    >
      <div className="absolute inset-0 bg-black/45 backdrop-blur-xl" />
      <div
        className="relative z-10 w-full max-w-3xl overflow-hidden rounded-[26px] border shadow-2xl"
        style={{
          borderColor: "var(--panel-border-strong, var(--panel-border))",
          background:
            "linear-gradient(160deg, rgba(10,16,26,0.96), rgba(20,28,39,0.88))",
          color: "var(--text)",
          boxShadow: "0 32px 120px rgba(0,0,0,0.38)",
        }}
      >
        <div className="border-b px-6 py-4 sm:px-8" style={{ borderColor: "var(--panel-border)" }}>
          <div className="flex items-center gap-3 text-xs uppercase tracking-[0.24em]">
            <span
              className="inline-flex items-center gap-2 rounded-full border px-3 py-1"
              style={{
                borderColor: "var(--chip-border)",
                background: "rgba(255,255,255,0.04)",
                color: "var(--muted)",
              }}
            >
              <span
                className={`h-2 w-2 rounded-full ${isChecking ? "animate-pulse" : ""}`}
                style={{
                  background:
                    state.status === "ready"
                      ? "var(--accent-strong, #7dd3fc)"
                      : state.status === "checking"
                      ? "#fbbf24"
                      : "var(--danger-text, #fca5a5)",
                }}
              />
              Startup Gate
            </span>
            <span style={{ color: "var(--muted)" }}>Native runtime preflight</span>
          </div>
        </div>

        <div className="space-y-6 px-6 py-7 sm:px-8 sm:py-8">
          <div className="space-y-3">
            <h1
              id="bootstrap-gate-title"
              className="text-2xl font-semibold tracking-[-0.02em] sm:text-3xl"
            >
              {state.title}
            </h1>
            <p className="max-w-2xl text-sm leading-6 sm:text-[15px]" style={{ color: "var(--muted)" }}>
              {state.message}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <CheckRow
              label="Docker CLI"
              value={isChecking ? null : preflight?.dockerCliInstalled ?? false}
              successLabel="Detected"
              failureLabel="Missing"
            />
            <CheckRow
              label="Docker Compose"
              value={isChecking ? null : preflight?.dockerComposeAvailable ?? false}
              successLabel="Available"
              failureLabel="Unavailable"
            />
            <CheckRow
              label="Docker Daemon"
              value={isChecking ? null : preflight?.dockerDaemonReachable ?? false}
              successLabel="Reachable"
              failureLabel="Not reachable"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {showContinueAction && (
              <Button type="button" className="rounded-full px-5" onClick={onContinue}>
                Continue
              </Button>
            )}
            {showRetryAction && (
              <Button type="button" variant="ghost" className="rounded-full px-5" onClick={onRetry}>
                Retry
              </Button>
            )}
            {showInstallAction && (
              <Button
                type="button"
                variant="ghost"
                className="rounded-full px-5"
                onClick={() => {
                  void handleInstallDocker();
                }}
                disabled={openingInstallPage}
              >
                {openingInstallPage ? "Opening…" : "Install Docker Desktop"}
              </Button>
            )}
            {isChecking && (
              <div className="inline-flex items-center gap-3 text-sm" style={{ color: "var(--muted)" }}>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-transparent" />
                Collecting native runtime diagnostics…
              </div>
            )}
          </div>

          {state.detail && (
            <details
              open={openDetailsByDefault}
              className="rounded-[20px] border px-4 py-3"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <summary
                className="cursor-pointer list-none text-sm font-medium"
                style={{ color: "var(--text)" }}
              >
                Technical details from native preflight
              </summary>
              <pre
                className="mt-3 overflow-auto whitespace-pre-wrap break-words text-xs leading-5"
                style={{ color: "var(--muted)" }}
              >
                {state.detail}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
