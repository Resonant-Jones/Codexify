import React from "react";

import { Button } from "@/components/ui/button";
import type {
  BootstrapLogResult,
  BootstrapLogService,
  BootstrapRecoveryNotice,
  BootstrapStep,
  RuntimeBootstrapState,
} from "@/lib/runtimeBootstrap";
import {
  BOOTSTRAP_LOG_SERVICES,
  getBootstrapDisplayCopy,
  getBootstrapRecoveryActions,
  isPackagedBootstrapState,
} from "@/lib/runtimeBootstrap";

type BootstrapGateProps = {
  state: RuntimeBootstrapState;
  onRetry: () => void;
  onInstallDocker: () => Promise<void> | void;
  onOpenDocker: () => Promise<void> | void;
  onRestartServices: () => Promise<void> | void;
  onToggleLogs: () => void;
  onSelectLogService: (service: BootstrapLogService) => void;
  logs: {
    visible: boolean;
    loading: boolean;
    service: BootstrapLogService;
    result: BootstrapLogResult | null;
  };
  recoveryNotice: BootstrapRecoveryNotice | null;
  openingDocker: boolean;
  restartingServices: boolean;
};

type PhaseCardState = "pending" | "running" | "done" | "failed";

type PhaseCardProps = {
  label: string;
  state: PhaseCardState;
  description: string;
};

const PHASE_STEP_MAP: Record<
  Exclude<BootstrapStep, "health-check"> | "preflight" | "readiness",
  string
> = {
  preflight: "checking-requirements",
  setup: "preparing-local-config",
  "compose-up": "starting-local-services",
  readiness: "waiting-for-ready",
};

const PREFLIGHT_FAILURE_KINDS = new Set([
  "runtime-home-unavailable",
  "packaged-runtime-assets-missing",
  "packaged-runtime-assets-corrupt",
  "packaged-runtime-materialization-failed",
  "packaged-bootstrap-unsupported",
  "runtime-path-unavailable",
  "repo-runtime-missing",
  "docker-cli-unavailable",
  "docker-cli-execution-failed",
  "docker-cli-found-but-unusable-from-packaged-context",
  "docker-compose-unavailable",
  "docker-daemon-unavailable",
  "docker-missing",
  "compose-missing",
  "docker-not-running",
  "unexpected-execution-error",
]);

function PhaseCard({ label, state, description }: PhaseCardProps) {
  const palette =
    state === "done"
      ? {
          tone: "var(--accent-strong, #7dd3fc)",
          border: "rgba(125,211,252,0.36)",
        }
      : state === "failed"
      ? {
          tone: "var(--danger-text, #fca5a5)",
          border: "rgba(252,165,165,0.3)",
        }
      : state === "running"
      ? {
          tone: "#fbbf24",
          border: "rgba(251,191,36,0.32)",
        }
      : {
          tone: "rgba(255,255,255,0.62)",
          border: "rgba(255,255,255,0.08)",
        };

  const statusLabel =
    state === "done"
      ? "Complete"
      : state === "failed"
      ? "Failed"
      : state === "running"
      ? "In progress"
      : "Pending";

  return (
    <div
      className="rounded-[18px] border px-4 py-4"
      style={{
        borderColor: palette.border,
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div
            className="text-xs uppercase tracking-[0.18em]"
            style={{ color: "var(--muted)" }}
          >
            {label}
          </div>
          <div
            className="mt-2 text-sm font-medium"
            style={{ color: palette.tone }}
          >
            {statusLabel}
          </div>
        </div>
        <span
          className={`mt-1 inline-flex h-3 w-3 rounded-full ${
            state === "running" ? "animate-pulse" : ""
          }`}
          style={{ background: palette.tone }}
          aria-hidden="true"
        />
      </div>
      <p
        className="mt-3 text-sm leading-6"
        style={{ color: "var(--muted)" }}
      >
        {description}
      </p>
    </div>
  );
}

function phaseStateFor(
  state: RuntimeBootstrapState,
  step: "preflight" | "setup" | "compose-up" | "readiness"
): PhaseCardState {
  const failureKind = state.failureKind ?? state.preflight?.failureKind;

  if (step === "preflight") {
    if (state.status === "checking-requirements") return "running";
    if (
      state.status === "docker-missing" ||
      state.status === "compose-missing" ||
      state.status === "docker-not-running"
    ) {
      return "failed";
    }
    if (
      state.status === "failed" &&
      failureKind &&
      PREFLIGHT_FAILURE_KINDS.has(failureKind)
    ) {
      return "failed";
    }
    return "done";
  }

  if (step === "setup") {
    const result = state.stepResults.setup;
    if (state.status === "preparing-local-config") return "running";
    if (result?.ok) return "done";
    if (result && !result.ok) return "failed";
    return state.status === "checking-requirements" ? "pending" : "pending";
  }

  if (step === "compose-up") {
    const result = state.stepResults["compose-up"];
    if (state.status === "starting-local-services") return "running";
    if (result?.ok) return "done";
    if (result && !result.ok) return "failed";
    if (state.status === "preparing-local-config") return "pending";
    return "pending";
  }

  const result = state.stepResults["health-check"];
  if (state.status === "waiting-for-ready") return "running";
  if (state.status === "ready-for-welcome") return "done";
  if (result?.ok) return "done";
  if (result && !result.ok && state.status === "failed") return "failed";
  if (state.status === "starting-local-services") return "pending";
  return "pending";
}

export default function BootstrapGate({
  state,
  onRetry,
  onInstallDocker,
  onOpenDocker,
  onRestartServices,
  onToggleLogs,
  onSelectLogService,
  logs,
  recoveryNotice,
  openingDocker,
  restartingServices,
}: BootstrapGateProps) {
  const [openingInstallPage, setOpeningInstallPage] = React.useState(false);
  const recoveryActions = getBootstrapRecoveryActions(state);
  const displayCopy = getBootstrapDisplayCopy(state);
  const packaged = isPackagedBootstrapState(state);
  const showInstallAction = recoveryActions.includes("install-docker");
  const showRetryAction = recoveryActions.includes("retry");
  const showOpenDockerAction = recoveryActions.includes("open-docker");
  const showLogsAction = recoveryActions.includes("view-logs");
  const showRestartAction = recoveryActions.includes("restart-services");
  const isBusy =
    state.status === "checking-requirements" ||
    state.status === "preparing-local-config" ||
    state.status === "starting-local-services" ||
    state.status === "waiting-for-ready";
  const actionsBusy = isBusy || openingDocker || restartingServices;
  const failureKind = state.failureKind ?? state.preflight?.failureKind;
  const runtimeHome =
    state.preflight?.runtimeHome ??
    state.stepResults.setup?.runtimeHome ??
    state.stepResults["compose-up"]?.runtimeHome ??
    state.stepResults["health-check"]?.runtimeHome;
  const packagedDockerContextFailure =
    failureKind === "docker-cli-found-but-unusable-from-packaged-context";

  const handleInstallDocker = React.useCallback(async () => {
    setOpeningInstallPage(true);
    try {
      await onInstallDocker();
    } finally {
      setOpeningInstallPage(false);
    }
  }, [onInstallDocker]);

  const phaseCards = [
    {
      id: "preflight",
      label: "Checking requirements",
      description:
        "Verify Docker CLI, Compose support, and daemon reachability before touching local runtime state.",
    },
    {
      id: PHASE_STEP_MAP.setup,
      label: "Preparing local config",
      description:
        "Run the packaged-safe setup source so .env, .env.template, and the runtime attachment manifest all resolve from the runtime home instead of repo-root assumptions.",
    },
    {
      id: PHASE_STEP_MAP["compose-up"],
      label: "Starting local services",
      description:
        "Bring the existing Docker Compose stack up from the resolved runtime home with explicit compose/env attachment paths.",
    },
    {
      id: PHASE_STEP_MAP.readiness,
      label: "Waiting for local beta runtime",
      description:
        "Poll /ping, /health, /health/chat, and /health/llm until the supported local beta loop is genuinely usable.",
    },
  ] as const;

  return (
    <div
      className="flex min-h-screen w-full items-center justify-center p-6 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bootstrap-gate-title"
    >
      <div className="absolute inset-0 bg-black/45 backdrop-blur-xl" />
      <div
        className="relative z-10 w-full max-w-4xl overflow-hidden rounded-[26px] border shadow-2xl"
        style={{
          borderColor: "var(--panel-border-strong, var(--panel-border))",
          background:
            "linear-gradient(160deg, rgba(10,16,26,0.96), rgba(20,28,39,0.88))",
          color: "var(--text)",
          boxShadow: "0 32px 120px rgba(0,0,0,0.38)",
        }}
      >
        <div
          className="border-b px-6 py-4 sm:px-8"
          style={{ borderColor: "var(--panel-border)" }}
        >
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
                className={`h-2 w-2 rounded-full ${isBusy ? "animate-pulse" : ""}`}
                style={{
                  background:
                    state.status === "ready-for-welcome"
                      ? "var(--accent-strong, #7dd3fc)"
                      : state.status === "failed" ||
                          state.status === "docker-missing" ||
                          state.status === "compose-missing" ||
                          state.status === "docker-not-running"
                      ? "var(--danger-text, #fca5a5)"
                      : isBusy
                      ? "#fbbf24"
                      : "rgba(255,255,255,0.62)",
                }}
              />
              Startup Gate
            </span>
            <span style={{ color: "var(--muted)" }}>
              Native runtime bootstrap
            </span>
          </div>
        </div>

        <div className="space-y-6 px-6 py-7 sm:px-8 sm:py-8">
          <div className="space-y-3">
            <h1
              id="bootstrap-gate-title"
              className="text-2xl font-semibold tracking-[-0.02em] sm:text-3xl"
            >
              {displayCopy.title}
            </h1>
            <p
              className="max-w-3xl text-sm leading-6 sm:text-[15px]"
              style={{ color: "var(--muted)" }}
            >
              {displayCopy.message}
            </p>
            {packagedDockerContextFailure && (
              <p
                className="max-w-3xl text-xs uppercase tracking-[0.12em] sm:text-[13px]"
                style={{ color: "var(--danger-text, #fca5a5)" }}
              >
                Docker was found, but this packaged Finder launch could not invoke
                it with the current macOS subprocess environment.
              </p>
            )}
            {packaged && (
              <div className="space-y-2">
                <div
                  className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs uppercase tracking-[0.18em]"
                  style={{
                    borderColor: "var(--chip-border)",
                    background: "rgba(255,255,255,0.04)",
                    color: "var(--muted)",
                  }}
                >
                  macOS beta artifact
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{
                      background:
                        state.status === "ready-for-welcome"
                          ? "var(--accent-strong, #7dd3fc)"
                          : state.status === "failed"
                          ? "var(--danger-text, #fca5a5)"
                          : "#fbbf24",
                    }}
                  />
                </div>
                {runtimeHome && (
                  <p
                    className="max-w-3xl font-mono text-xs leading-5"
                    style={{ color: "var(--muted)" }}
                  >
                    Runtime home: {runtimeHome}
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {phaseCards.map((phase) => (
              <PhaseCard
                key={phase.id}
                label={phase.label}
                state={phaseStateFor(
                  state,
                  phase.id === "preflight"
                    ? "preflight"
                    : phase.id === PHASE_STEP_MAP.setup
                    ? "setup"
                    : phase.id === PHASE_STEP_MAP["compose-up"]
                    ? "compose-up"
                    : "readiness"
                )}
                description={phase.description}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {showRetryAction && (
              <Button
                type="button"
                className="rounded-full px-5"
                onClick={onRetry}
                disabled={actionsBusy}
              >
                Retry
              </Button>
            )}
            {showOpenDockerAction && (
              <Button
                type="button"
                variant="ghost"
                className="rounded-full px-5"
                onClick={() => {
                  void onOpenDocker();
                }}
                disabled={actionsBusy}
              >
                {openingDocker ? "Opening Docker..." : "Open Docker"}
              </Button>
            )}
            {showLogsAction && (
              <Button
                type="button"
                variant="ghost"
                className="rounded-full px-5"
                onClick={onToggleLogs}
                disabled={isBusy || restartingServices}
              >
                {logs.visible ? "Hide Logs" : "View Logs"}
              </Button>
            )}
            {showRestartAction && (
              <Button
                type="button"
                variant="ghost"
                className="rounded-full px-5"
                onClick={() => {
                  void onRestartServices();
                }}
                disabled={actionsBusy}
              >
                {restartingServices ? "Restarting Services..." : "Restart Services"}
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
                disabled={openingInstallPage || actionsBusy}
              >
                {openingInstallPage ? "Opening..." : "Install Docker Desktop"}
              </Button>
            )}
            {isBusy && (
              <div
                className="inline-flex items-center gap-3 text-sm"
                style={{ color: "var(--muted)" }}
              >
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-transparent" />
                {state.status === "ready-for-welcome"
                  ? "Opening welcome screen..."
                  : "Running native startup orchestration..."}
              </div>
            )}
            {state.status === "ready-for-welcome" && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Local beta readiness checks are green. Opening the welcome screen next.
              </p>
            )}
          </div>

          {recoveryNotice && (
            <div
              className="rounded-[20px] border px-4 py-4"
              style={{
                borderColor: "rgba(252,165,165,0.28)",
                background: "rgba(127,29,29,0.16)",
              }}
            >
              <div
                className="text-xs uppercase tracking-[0.18em]"
                style={{ color: "var(--danger-text, #fca5a5)" }}
              >
                Recovery status
              </div>
              <div className="mt-2 text-sm font-medium">{recoveryNotice.title}</div>
              <p
                className="mt-2 text-sm leading-6"
                style={{ color: "var(--muted)" }}
              >
                {recoveryNotice.message}
              </p>
              {recoveryNotice.detail && (
                <pre
                  className="mt-3 overflow-auto whitespace-pre-wrap break-words text-xs leading-5"
                  style={{ color: "var(--muted)" }}
                >
                  {recoveryNotice.detail}
                </pre>
              )}
            </div>
          )}

          {logs.visible && (
            <section
              className="rounded-[20px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
              aria-labelledby="bootstrap-runtime-logs-title"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <h2
                    id="bootstrap-runtime-logs-title"
                    className="text-sm font-medium"
                  >
                    Runtime logs
                  </h2>
                  <p
                    className="text-sm leading-6"
                    style={{ color: "var(--muted)" }}
                  >
                    Recent Docker Compose output is shown here separately from the
                    startup diagnostics so runtime failures are easier to trace.
                  </p>
                </div>
                <div
                  className="rounded-full border px-3 py-1 text-xs uppercase tracking-[0.18em]"
                  style={{
                    borderColor: "var(--chip-border)",
                    color: "var(--muted)",
                  }}
                >
                  Service: {logs.service}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {BOOTSTRAP_LOG_SERVICES.map((service) => {
                  const selected = logs.service === service;
                  return (
                    <button
                      key={service}
                      type="button"
                      className="rounded-full border px-3 py-1 text-xs uppercase tracking-[0.14em] transition"
                      style={{
                        borderColor: selected
                          ? "rgba(125,211,252,0.36)"
                          : "var(--chip-border)",
                        background: selected
                          ? "rgba(125,211,252,0.12)"
                          : "rgba(255,255,255,0.04)",
                        color: selected
                          ? "var(--accent-strong, #7dd3fc)"
                          : "var(--muted)",
                      }}
                      onClick={() => onSelectLogService(service)}
                      aria-pressed={selected}
                      disabled={restartingServices}
                    >
                      {service}
                    </button>
                  );
                })}
              </div>

              <div
                className="mt-4 rounded-[18px] border"
                style={{
                  borderColor: "rgba(255,255,255,0.08)",
                  background: "rgba(5,10,18,0.8)",
                }}
              >
                <div
                  className="border-b px-4 py-3 text-xs uppercase tracking-[0.18em]"
                  style={{
                    borderColor: "rgba(255,255,255,0.08)",
                    color: "var(--muted)",
                  }}
                >
                  {logs.loading
                    ? `Loading ${logs.service} logs`
                    : logs.result?.ok
                    ? `${logs.service} logs`
                    : `${logs.service} logs unavailable`}
                </div>
                <div className="max-h-[320px] overflow-auto px-4 py-4">
                  {logs.loading ? (
                    <div
                      className="inline-flex items-center gap-3 text-sm"
                      style={{ color: "var(--muted)" }}
                    >
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-transparent" />
                      Fetching recent Compose output for {logs.service}.
                    </div>
                  ) : logs.result?.logs ? (
                    <pre
                      className="whitespace-pre-wrap break-words font-mono text-xs leading-5"
                      style={{ color: "var(--text)" }}
                    >
                      {logs.result.logs}
                    </pre>
                  ) : (
                    <p
                      className="text-sm leading-6"
                      style={{ color: "var(--muted)" }}
                    >
                      {logs.result?.ok
                        ? `No recent log output was returned for ${logs.service}.`
                        : `Codexify could not load recent ${logs.service} logs from Docker Compose.`}
                    </p>
                  )}
                </div>
              </div>

              {(logs.result?.command || logs.result?.detail) && (
                <div className="mt-3 space-y-2 text-xs leading-5" style={{ color: "var(--muted)" }}>
                  {logs.result?.command && <div>{logs.result.command}</div>}
                  {logs.result?.detail && (
                    <pre className="overflow-auto whitespace-pre-wrap break-words">
                      {logs.result.detail}
                    </pre>
                  )}
                </div>
              )}
            </section>
          )}

          {state.detail && (
            <details
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
                Technical details
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
