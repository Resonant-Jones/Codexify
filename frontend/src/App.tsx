import React from "react";

import BootstrapGate from "./components/bootstrap/BootstrapGate";
import DocumentGenModal, {
  DocumentGenInput,
} from "./components/DocumentGenModal";
import AppShell from "./components/persona/layout/AppShell";
import { TopBar } from "./components/TopBar";
import { Button } from "./components/ui/button";
import CommandCenterPage from "./features/commandCenter/CommandCenterPage";
import api from "./lib/api";
import {
  appendBootstrapDetail,
  BOOTSTRAP_LOG_SERVICES,
  createCheckingRuntimeBootstrapState,
  createBootstrapSupportNoticeFromDockerOpenResult,
  createBootstrapSupportNoticeFromLogResult,
  createBootstrapSupportNoticeFromRestartResult,
  createComposeRecoveryStepResult,
  createFailedRuntimeBootstrapState,
  createPreparingLocalConfigState,
  createReadyForWelcomeState,
  createStartingLocalServicesState,
  createWaitingForReadyState,
  formatBootstrapStepResult,
  formatRuntimeReadinessResult,
  getBootstrapLogs,
  hasDismissedWelcomeScreen,
  mapRuntimePreflightFailureToState,
  mapRuntimeReadinessFailureToState,
  openDockerDesktopNative,
  openDockerDesktopDownloadPage,
  restartRuntimeServices,
  runComposeUp,
  runRuntimeBootstrapPreflight,
  runSetupCli,
  setWelcomeScreenDismissed,
  shouldRunRuntimeBootstrap,
  type BootstrapLogResult,
  type BootstrapLogService,
  type BootstrapRecoveryNotice,
  type BootstrapRecoveryStage,
  type BootstrapStep,
  type BootstrapStepResult,
  type RuntimeBootstrapState,
  type RuntimePreflight,
  waitForRuntimeReady,
} from "./lib/runtimeBootstrap";
import EventsConsole from "./pages/EventsConsole";
import { SharePage } from "./pages/SharePage";

/**
 * App entry with a gated UI Playground ("Tune Rack").
 *
 * When the env flag VITE_TUNE=1 is set (or in plain DEV),
 * visiting the route /dev/tune will try to load the sandboxed
 * playground from ./dev/ui-tune/UITunePad and its scoped CSS.
 *
 * This never touches production UI unless you intentionally
 * navigate to /dev/tune with the flag enabled.
 */

const TUNE_ENABLED = (import.meta as any)?.env?.DEV || (import.meta as any)?.env?.VITE_TUNE === "1";
const COMMAND_CENTER_ENABLED =
  (import.meta as any)?.env?.DEV ||
  /^(1|true)$/i.test(
    String((import.meta as any)?.env?.VITE_ENABLE_COMMAND_CENTER ?? "")
  );

const DOC_GEN_EXT_MAP: Record<string, string> = {
  markdown: "md",
  plain: "txt",
};

function getActiveThreadId(): number | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/chat\/(\d+)/);
  if (!match) return null;
  const id = Number(match[1]);
  return Number.isFinite(id) ? id : null;
}

function isTuneRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/dev/tune");
}

function isEventsRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/dev/events");
}

function isCommandCenterRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/command-center");
}

function isShareRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/share/");
}

function getShareToken() {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/share\/(.+)$/);
  return match ? match[1] : null;
}

type BootstrapPhase = "bootstrap" | "welcome" | "unlocked";
type BootstrapStartBoundary = BootstrapRecoveryStage;

type BootstrapLogsState = {
  visible: boolean;
  loading: boolean;
  service: BootstrapLogService;
  result: BootstrapLogResult | null;
};

type BootstrapRetryPlan = {
  boundary: BootstrapStartBoundary;
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>>;
};

type StartupOrchestrationOptions = {
  startAt: Exclude<BootstrapStartBoundary, "preflight">;
  initialDetail?: string;
  initialStepResults?: Partial<Record<BootstrapStep, BootstrapStepResult>>;
};

function resolveBootstrapRecoveryStage(
  state: RuntimeBootstrapState
): BootstrapRecoveryStage | null {
  if (
    state.status === "checking-requirements" ||
    state.status === "docker-missing" ||
    state.status === "compose-missing" ||
    state.status === "docker-not-running"
  ) {
    return "preflight";
  }

  if (state.stepResults["health-check"] && !state.stepResults["health-check"]?.ok) {
    return "readiness";
  }

  if (state.stepResults["compose-up"] && !state.stepResults["compose-up"]?.ok) {
    return "compose-up";
  }

  if (state.stepResults.setup && !state.stepResults.setup?.ok) {
    return "setup";
  }

  if (state.status === "failed") {
    return "preflight";
  }

  return null;
}

function resolveBootstrapDefaultLogService(
  state: RuntimeBootstrapState
): BootstrapLogService {
  if (state.stepResults["health-check"] && !state.stepResults["health-check"]?.ok) {
    return "backend";
  }

  if (state.stepResults["compose-up"] && !state.stepResults["compose-up"]?.ok) {
    return "backend";
  }

  return "backend";
}

function WelcomeScreen({ onEnter }: { onEnter: () => void }) {
  return (
    <div
      className="flex min-h-screen w-full items-center justify-center p-6 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-screen-title"
    >
      <div className="absolute inset-0 bg-black/35 backdrop-blur-xl" />
      <div
        className="relative z-10 w-full max-w-2xl overflow-hidden rounded-[26px] border shadow-2xl"
        style={{
          borderColor: "var(--panel-border-strong, var(--panel-border))",
          background:
            "linear-gradient(155deg, rgba(12,18,30,0.95), rgba(19,29,42,0.86))",
          color: "var(--text)",
          boxShadow: "0 32px 110px rgba(0,0,0,0.34)",
        }}
      >
        <div
          className="border-b px-6 py-4 sm:px-8"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <span
            className="inline-flex items-center rounded-full border px-3 py-1 text-xs uppercase tracking-[0.24em]"
            style={{
              borderColor: "var(--chip-border)",
              background: "rgba(255,255,255,0.04)",
              color: "var(--muted)",
            }}
          >
            Welcome
          </span>
        </div>

        <div className="space-y-6 px-6 py-7 sm:px-8 sm:py-9">
          <div className="space-y-3">
            <h1
              id="welcome-screen-title"
              className="text-2xl font-semibold tracking-[-0.02em] sm:text-3xl"
            >
              Codexify is ready.
            </h1>
            <p
              className="max-w-xl text-sm leading-6 sm:text-[15px]"
              style={{ color: "var(--muted)" }}
            >
              The backend process is reachable, startup has completed, Redis
              and chat health are green, and the local beta readiness contract
              is satisfied. Enter when you want the full workspace surface to
              become interactive.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div
                className="text-xs uppercase tracking-[0.18em]"
                style={{ color: "var(--muted)" }}
              >
                Local first
              </div>
              <p
                className="mt-2 text-sm leading-6"
                style={{ color: "var(--text)" }}
              >
                Startup stays anchored to the local repo, runtime files, and
                health surfaces instead of a separate desktop-only bootstrap.
              </p>
            </div>
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div
                className="text-xs uppercase tracking-[0.18em]"
                style={{ color: "var(--muted)" }}
              >
                Explicit gating
              </div>
              <p
                className="mt-2 text-sm leading-6"
                style={{ color: "var(--text)" }}
              >
                Guardian, Dashboard, Documents, and Gallery stay locked until
                the real runtime proves it is ready.
              </p>
            </div>
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div
                className="text-xs uppercase tracking-[0.18em]"
                style={{ color: "var(--muted)" }}
              >
                One time
              </div>
              <p
                className="mt-2 text-sm leading-6"
                style={{ color: "var(--text)" }}
              >
                This welcome screen is dismissed per local profile so repeat
                launches can go straight to the workspace once the local beta
                loop is green.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" className="rounded-full px-5" onClick={onEnter}>
              Enter Codexify
            </Button>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              The workspace unlocks after this step.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function DevTuneGate() {
  const [Mod, setMod] = React.useState<React.ComponentType | null>(null);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    // Load the CSS first (scoped inside UITunePad via .tune-sandbox)
    import("./dev/ui-tune/ui-tune.dev.css").catch(() => {
      // Non-fatal if CSS not present yet
    });

    // Dynamically import the playground component only on the dev route
    import("./dev/ui-tune/UITunePad")
      .then((m) => {
        if (cancelled) return;
        const Comp = (m as any).default || (m as any).UITunePad || (m as any);
        if (typeof Comp === "function") setMod(() => Comp);
        else setError(new Error("UITunePad module did not export a component"));
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div style={{ padding: 16, fontFamily: "ui-sans-serif, system-ui" }}>
        <strong>UI Tune Rack not found.</strong>
        <div style={{ opacity: 0.75, marginTop: 8 }}>
          Create <code>src/dev/ui-tune/UITunePad.tsx</code> and
          <code> src/dev/ui-tune/ui-tune.dev.css</code>, or disable the tune route.
        </div>
      </div>
    );
  }

  if (!Mod) {
    return null; // simple fade-in once loaded
  }

  const Comp = Mod;
  return <Comp />;
}

export default function App() {
  const tuneRoute = TUNE_ENABLED && isTuneRoute();
  const eventsRoute = isEventsRoute();
  const commandCenterRoute = isCommandCenterRoute();
  const shareRoute = isShareRoute();
  const shareToken = shareRoute ? getShareToken() : null;
  const bootstrapEnabled =
    shouldRunRuntimeBootstrap() &&
    !tuneRoute &&
    !eventsRoute &&
    !commandCenterRoute &&
    !(shareRoute && !!shareToken);
  const [docGenOpen, setDocGenOpen] = React.useState(false);
  const [docGenDraft, setDocGenDraft] = React.useState<DocumentGenInput | null>(
    null
  );
  const [bootstrapState, setBootstrapState] =
    React.useState<RuntimeBootstrapState>(createCheckingRuntimeBootstrapState);
  const [bootstrapPhase, setBootstrapPhase] = React.useState<BootstrapPhase>(
    () => (bootstrapEnabled ? "bootstrap" : "unlocked")
  );
  const bootstrapRunRef = React.useRef(0);
  const autoBootstrapStartedRef = React.useRef(false);
  const latestPreflightRef = React.useRef<RuntimePreflight | null>(null);
  const diagnosticsRef = React.useRef<string | undefined>(undefined);
  const bootstrapLogsRequestRef = React.useRef(0);
  const [bootstrapLogs, setBootstrapLogs] = React.useState<BootstrapLogsState>(
    () => ({
      visible: false,
      loading: false,
      service: "backend",
      result: null,
    })
  );
  const [bootstrapRecoveryNotice, setBootstrapRecoveryNotice] =
    React.useState<BootstrapRecoveryNotice | null>(null);
  const [openingDockerDesktop, setOpeningDockerDesktop] = React.useState(false);
  const [restartingServices, setRestartingServices] = React.useState(false);

  const handleDocGenSubmit = React.useCallback(
    async (input: DocumentGenInput) => {
      setDocGenDraft(input);
      const threadId = getActiveThreadId();
      if (!threadId) {
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:toast", {
              detail: {
                kind: "error",
                message: "Open a chat thread before generating a document.",
              },
            })
          );
        } catch {
          // ignore
        }
        return;
      }

      try {
        const payload = {
          thread_id: threadId,
          title: input.title.trim() || undefined,
          prompt: input.prompt,
          format: input.format,
          doc_type: input.doc_type,
        };
        const response = await api.post("/documents/generate", payload);
        const data = response?.data ?? {};
        const documentId = data.document_id ?? data.id;
        if (!documentId) {
          throw new Error("Missing generated document id.");
        }
        const resolvedTitle =
          (data.title || input.title).trim() || "Generated document";
        const resolvedFormat = String(
          data.format || input.format || "markdown"
        ).toLowerCase();
        const ext = DOC_GEN_EXT_MAP[resolvedFormat] || "md";
        const doc = {
          id: documentId,
          title: resolvedTitle,
          ext,
          type: "file",
          thread_id: threadId,
        };
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:documents:add", {
              detail: { items: [doc] },
            })
          );
        } catch {
          // ignore
        }
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:documents:open", { detail: { doc } })
          );
        } catch {
          // ignore
        }
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:toast", {
              detail: { message: "Document generated." },
            })
          );
        } catch {
          // ignore
        }
      } catch (err: unknown) {
        const fallback = "Failed to generate document.";
        const maybeErr =
          err && typeof err === "object"
            ? (err as {
                response?: { data?: { detail?: string } };
                message?: string;
              })
            : null;
        const message =
          maybeErr?.response?.data?.detail ||
          maybeErr?.message ||
          fallback;
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:toast", {
              detail: { kind: "error", message },
            })
          );
        } catch {
          // ignore
        }
      }
    },
    []
  );

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const onOpen = () => setDocGenOpen(true);
    window.addEventListener("cfy:documents:generate", onOpen as EventListener);
    return () =>
      window.removeEventListener(
        "cfy:documents:generate",
        onOpen as EventListener
      );
  }, []);

  const appendDiagnostics = React.useCallback(
    (next: string | undefined, heading?: string) => {
      diagnosticsRef.current = appendBootstrapDetail(
        diagnosticsRef.current,
        next,
        heading
      );
      return diagnosticsRef.current;
    },
    []
  );

  const syncBootstrapDetail = React.useCallback((detail: string | undefined) => {
    setBootstrapState((current) =>
      current.detail === detail ? current : { ...current, detail }
    );
  }, []);

  const buildRetryPlan = React.useCallback(
    (state: RuntimeBootstrapState): BootstrapRetryPlan => {
      const stage = resolveBootstrapRecoveryStage(state);

      if (stage === "readiness") {
        const stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {};
        if (state.stepResults.setup?.ok) {
          stepResults.setup = state.stepResults.setup;
        }
        if (state.stepResults["compose-up"]?.ok) {
          stepResults["compose-up"] = state.stepResults["compose-up"];
        }
        return { boundary: "readiness", stepResults };
      }

      if (stage === "compose-up") {
        const stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {};
        if (state.stepResults.setup?.ok) {
          stepResults.setup = state.stepResults.setup;
        }
        return { boundary: "compose-up", stepResults };
      }

      if (stage === "setup" && state.preflight?.ready) {
        return { boundary: "setup", stepResults: {} };
      }

      return { boundary: "preflight", stepResults: {} };
    },
    []
  );

  React.useEffect(() => {
    const defaultService = resolveBootstrapDefaultLogService(bootstrapState);
    setBootstrapLogs((current) =>
      current.visible || current.service === defaultService
        ? current
        : { ...current, service: defaultService }
    );
  }, [bootstrapState]);

  const advanceToWelcomeOrWorkspace = React.useCallback((runId: number) => {
    const moveForward = () => {
      if (runId !== bootstrapRunRef.current) return;
      if (hasDismissedWelcomeScreen()) {
        setBootstrapPhase("unlocked");
        return;
      }
      setBootstrapPhase("welcome");
    };

    if (
      typeof window !== "undefined" &&
      typeof window.requestAnimationFrame === "function"
    ) {
      window.requestAnimationFrame(moveForward);
      return;
    }

    queueMicrotask(moveForward);
  }, []);

  const runStartupOrchestration = React.useCallback(
    async (
      preflight: RuntimePreflight,
      options: StartupOrchestrationOptions
    ) => {
      const runId = bootstrapRunRef.current;
      let stepResults = { ...(options.initialStepResults ?? {}) };
      let detail = options.initialDetail ?? diagnosticsRef.current;
      let startAt = options.startAt;

      if (startAt === "readiness" && !stepResults["compose-up"]?.ok) {
        startAt = "compose-up";
      }
      if (startAt !== "setup" && !stepResults.setup?.ok) {
        startAt = "setup";
      }

      setBootstrapPhase("bootstrap");

      if (startAt === "setup") {
        setBootstrapState(
          createPreparingLocalConfigState(preflight, detail, stepResults)
        );

        const setupResult = await runSetupCli();
        if (runId !== bootstrapRunRef.current) return;
        stepResults = {
          ...stepResults,
          setup: setupResult,
        };
        detail = appendDiagnostics(
          formatBootstrapStepResult(setupResult),
          "Setup step"
        );
        if (!setupResult.ok) {
          const failureKind =
            setupResult.failureKind ??
            (preflight.packaged ? "packaged-setup-failed" : "setup-failed");
          setBootstrapState(
            createFailedRuntimeBootstrapState({
              title: preflight.packaged
                ? "Packaged setup failed"
                : "Preparing local config failed",
              message: preflight.packaged
                ? "Codexify could not complete the packaged setup step from the materialized runtime home. Retry to rerun setup while the workspace stays locked."
                : "Codexify could not complete the repo-defined setup step. Retry to rerun setup, then continue through Compose startup and readiness while the workspace stays locked.",
              detail,
              failureKind,
              preflight,
              stepResults,
            })
          );
          return;
        }
      }

      if (startAt === "setup" || startAt === "compose-up") {
        setBootstrapState(
          createStartingLocalServicesState(preflight, detail, stepResults)
        );

        const composeResult = await runComposeUp();
        if (runId !== bootstrapRunRef.current) return;
        stepResults = {
          ...stepResults,
          "compose-up": composeResult,
        };
        detail = appendDiagnostics(
          formatBootstrapStepResult(composeResult),
          "Compose startup"
        );
        if (!composeResult.ok) {
          const failureKind =
            composeResult.failureKind ??
            (preflight.packaged
              ? "packaged-compose-up-failed"
              : "compose-up-failed");
          setBootstrapState(
            createFailedRuntimeBootstrapState({
              title: preflight.packaged
                ? "Packaged Compose startup failed"
                : "Starting local services failed",
              message: preflight.packaged
                ? "Codexify could not bring the packaged Compose stack up cleanly from the materialized runtime home. Retry to rerun Compose startup, or inspect logs and restart services if the runtime needs intervention."
                : "Codexify could not bring the local Compose stack up cleanly. Retry to rerun Compose startup, or inspect logs and restart services if the runtime needs intervention.",
              detail,
              failureKind,
              preflight,
              stepResults,
            })
          );
          return;
        }
      }

      setBootstrapState(
        createWaitingForReadyState(preflight, detail, stepResults)
      );

      const readiness = await waitForRuntimeReady({
        onPoll: (healthResult, attempt) => {
          if (runId !== bootstrapRunRef.current) return;
          const liveDetail = appendBootstrapDetail(
            detail,
            formatRuntimeReadinessResult(healthResult),
            `Readiness probe ${attempt}`
          );
          setBootstrapState(
            createWaitingForReadyState(
              preflight,
              liveDetail,
              {
                ...stepResults,
                "health-check": healthResult,
              },
              healthResult
            )
          );
        },
      });

      if (runId !== bootstrapRunRef.current) return;

      stepResults = {
        ...stepResults,
        "health-check": readiness.lastCheck,
      };
      detail = appendDiagnostics(
        formatRuntimeReadinessResult(readiness.lastCheck),
        readiness.ok
          ? `Readiness succeeded after ${readiness.attempts} probe(s) in ${Math.round(
              readiness.elapsedMs / 1000
            )}s`
          : `Readiness failed after ${readiness.attempts} probe(s) in ${Math.round(
              readiness.elapsedMs / 1000
            )}s`
      );

      if (!readiness.ok) {
        setBootstrapState(
          mapRuntimeReadinessFailureToState(
            preflight,
            readiness.lastCheck,
            detail,
            stepResults
          )
        );
        return;
      }

      setBootstrapState(
        createReadyForWelcomeState(
          preflight,
          detail,
          stepResults,
          readiness.lastCheck
        )
      );
      advanceToWelcomeOrWorkspace(runId);
    },
    [advanceToWelcomeOrWorkspace, appendDiagnostics]
  );

  const runBootstrapFlow = React.useCallback(
    async (
      boundary: BootstrapStartBoundary,
      stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
    ) => {
      if (!bootstrapEnabled) {
        setBootstrapPhase("unlocked");
        return;
      }

      const runId = ++bootstrapRunRef.current;
      bootstrapLogsRequestRef.current += 1;
      setBootstrapPhase("bootstrap");
      setBootstrapRecoveryNotice(null);
      setOpeningDockerDesktop(false);
      setRestartingServices(false);

      const reusePreflight =
        boundary !== "preflight" && latestPreflightRef.current?.ready
          ? latestPreflightRef.current
          : null;

      if (reusePreflight) {
        await runStartupOrchestration(reusePreflight, {
          startAt: boundary === "preflight" ? "setup" : boundary,
          initialDetail: diagnosticsRef.current,
          initialStepResults: stepResults,
        });
        return;
      }

      setBootstrapState(createCheckingRuntimeBootstrapState(diagnosticsRef.current));
      const preflight = await runRuntimeBootstrapPreflight();

      if (runId !== bootstrapRunRef.current) return;

      latestPreflightRef.current = preflight.ready ? preflight : null;
      const preflightDetail = appendDiagnostics(
        preflight.detail,
        "Docker preflight"
      );

      if (!preflight.ready) {
        const failureState = mapRuntimePreflightFailureToState({
          ...preflight,
          detail: preflightDetail,
        });
        diagnosticsRef.current = failureState.detail;
        setBootstrapState(failureState);
        return;
      }

      await runStartupOrchestration(preflight, {
        startAt: boundary === "preflight" ? "setup" : boundary,
        initialDetail: preflightDetail,
        initialStepResults: stepResults,
      });
    },
    [
      appendDiagnostics,
      bootstrapEnabled,
      runStartupOrchestration,
      bootstrapLogsRequestRef,
    ]
  );

  React.useEffect(() => {
    if (!bootstrapEnabled) {
      autoBootstrapStartedRef.current = false;
      latestPreflightRef.current = null;
      bootstrapLogsRequestRef.current += 1;
      setBootstrapRecoveryNotice(null);
      setOpeningDockerDesktop(false);
      setRestartingServices(false);
      setBootstrapLogs((current) => ({
        ...current,
        visible: false,
        loading: false,
      }));
      setBootstrapPhase("unlocked");
      return;
    }

    setBootstrapPhase("bootstrap");
    if (autoBootstrapStartedRef.current) return;

    autoBootstrapStartedRef.current = true;
    void runBootstrapFlow("preflight");
  }, [bootstrapEnabled, runBootstrapFlow]);

  const loadBootstrapLogs = React.useCallback(
    async (service: BootstrapLogService) => {
      const requestId = ++bootstrapLogsRequestRef.current;
      setBootstrapRecoveryNotice(null);
      setBootstrapLogs((current) => ({
        visible: true,
        loading: true,
        service,
        result: current.service === service ? current.result : null,
      }));

      const result = await getBootstrapLogs(service);
      if (requestId !== bootstrapLogsRequestRef.current) return;

      setBootstrapLogs({
        visible: true,
        loading: false,
        service,
        result,
      });

      if (!result.ok) {
        const detail = appendDiagnostics(
          result.detail,
          `Log retrieval (${service})`
        );
        syncBootstrapDetail(detail);
        setBootstrapRecoveryNotice(
          createBootstrapSupportNoticeFromLogResult({
            ...result,
            detail,
          })
        );
      }
    },
    [appendDiagnostics, syncBootstrapDetail]
  );

  const handleRetryBootstrap = React.useCallback(() => {
    const plan = buildRetryPlan(bootstrapState);
    void runBootstrapFlow(plan.boundary, plan.stepResults);
  }, [bootstrapState, buildRetryPlan, runBootstrapFlow]);

  const handleWelcomeEnter = React.useCallback(() => {
    setWelcomeScreenDismissed(true);
    setBootstrapPhase("unlocked");
  }, []);

  const handleInstallDocker = React.useCallback(async () => {
    setBootstrapRecoveryNotice(null);
    const opened = await openDockerDesktopDownloadPage();
    if (opened) return;
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: {
            kind: "error",
            message: "Unable to open the Docker Desktop download page.",
          },
        })
      );
    } catch {
      // ignore
    }
  }, []);

  const handleOpenDocker = React.useCallback(async () => {
    setBootstrapRecoveryNotice(null);
    setOpeningDockerDesktop(true);
    const result = await openDockerDesktopNative();
    setOpeningDockerDesktop(false);

    const detail = appendDiagnostics(result.detail, "Open Docker Desktop");
    syncBootstrapDetail(detail);

    if (!result.ok) {
      setBootstrapRecoveryNotice(
        createBootstrapSupportNoticeFromDockerOpenResult({
          ...result,
          detail,
        })
      );
    }
  }, [appendDiagnostics, syncBootstrapDetail]);

  const handleToggleBootstrapLogs = React.useCallback(() => {
    if (bootstrapLogs.visible) {
      bootstrapLogsRequestRef.current += 1;
      setBootstrapLogs((current) => ({
        ...current,
        visible: false,
        loading: false,
      }));
      return;
    }

    const nextService =
      bootstrapLogs.service || resolveBootstrapDefaultLogService(bootstrapState);
    void loadBootstrapLogs(nextService);
  }, [bootstrapLogs.service, bootstrapLogs.visible, bootstrapState, loadBootstrapLogs]);

  const handleSelectBootstrapLogService = React.useCallback(
    (service: BootstrapLogService) => {
      if (!BOOTSTRAP_LOG_SERVICES.includes(service)) return;
      if (!bootstrapLogs.visible) {
        setBootstrapLogs((current) => ({ ...current, service }));
        return;
      }
      void loadBootstrapLogs(service);
    },
    [bootstrapLogs.visible, loadBootstrapLogs]
  );

  const handleRestartServices = React.useCallback(async () => {
    const preflight = latestPreflightRef.current ?? bootstrapState.preflight;
    if (!preflight?.ready) {
      void runBootstrapFlow("preflight");
      return;
    }

    const runId = ++bootstrapRunRef.current;
    bootstrapLogsRequestRef.current += 1;
    setBootstrapRecoveryNotice(null);
    setRestartingServices(true);
    setBootstrapPhase("bootstrap");
    setBootstrapState(
      createStartingLocalServicesState(
        preflight,
        diagnosticsRef.current,
        bootstrapState.stepResults
      )
    );

    const result = await restartRuntimeServices();
    if (runId !== bootstrapRunRef.current) return;
    setRestartingServices(false);

    const composeRecovery = createComposeRecoveryStepResult(result);
    const detail = appendDiagnostics(
      formatBootstrapStepResult(composeRecovery),
      "Restart services"
    );

    if (!result.ok) {
      setBootstrapState(
        createFailedRuntimeBootstrapState({
          title: "Restarting local services failed",
          message:
            "Codexify could not complete the targeted runtime restart from the desktop shell. The workspace stays locked until Compose startup and readiness succeed.",
          detail,
          failureKind: "restart-services-failed",
          preflight,
          stepResults: bootstrapState.stepResults,
        })
      );
      setBootstrapRecoveryNotice(
        createBootstrapSupportNoticeFromRestartResult({
          ...result,
          detail,
        })
      );
      return;
    }

    const nextStepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {
      ...bootstrapState.stepResults,
      "compose-up": composeRecovery,
    };

    setBootstrapState(
      createWaitingForReadyState(preflight, detail, nextStepResults)
    );
    await runStartupOrchestration(preflight, {
      startAt: "readiness",
      initialDetail: detail,
      initialStepResults: nextStepResults,
    });
  }, [appendDiagnostics, bootstrapState, runBootstrapFlow, runStartupOrchestration]);

  const startupLocked = bootstrapEnabled && bootstrapPhase !== "unlocked";

  if (tuneRoute) {
    return <DevTuneGate />;
  }
  if (eventsRoute) {
    return (
      <div style={{ minHeight: "100svh", display: "flex", flexDirection: "column" }}>
        <TopBar />
        <main style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
          <EventsConsole />
        </main>
      </div>
    );
  }
  if (commandCenterRoute) {
    return <CommandCenterPage enabled={COMMAND_CENTER_ENABLED} />;
  }
  if (shareRoute) {
    if (shareToken) {
      return <SharePage token={shareToken} />;
    }
  }
  if (startupLocked) {
    if (bootstrapPhase === "welcome") {
      return <WelcomeScreen onEnter={handleWelcomeEnter} />;
    }

    return (
      <BootstrapGate
        state={bootstrapState}
        onRetry={handleRetryBootstrap}
        onInstallDocker={handleInstallDocker}
        onOpenDocker={handleOpenDocker}
        onRestartServices={handleRestartServices}
        onToggleLogs={handleToggleBootstrapLogs}
        onSelectLogService={handleSelectBootstrapLogService}
        logs={bootstrapLogs}
        recoveryNotice={bootstrapRecoveryNotice}
        openingDocker={openingDockerDesktop}
        restartingServices={restartingServices}
      />
    );
  }

  return (
    <>
      {appShell}
      <div className="fixed bottom-6 right-6 z-[1200]">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full px-4 shadow"
          onClick={() => setDocGenOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={docGenOpen}
        >
          Generate Doc
        </Button>
      </div>
      <DocumentGenModal
        open={docGenOpen}
        onOpenChange={setDocGenOpen}
        onSubmit={handleDocGenSubmit}
        initialValues={docGenDraft ?? undefined}
      />
    </>
  );
}
