import {
  invokeTauriCommand,
  isTauriRuntime,
  openExternalUrl,
} from "@/lib/runtimeConfig";

export type RuntimePreflight = {
  dockerCliInstalled: boolean;
  dockerComposeAvailable: boolean;
  dockerDaemonReachable: boolean;
  ready: boolean;
  failureKind?: string;
  detail?: string;
};

export type BootstrapStep = "setup" | "compose-up" | "health-check";

export type BootstrapStepResult = {
  ok: boolean;
  step: BootstrapStep;
  detail?: string;
  command?: string;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
};

export type HealthEndpointCheck = {
  endpoint: string;
  ok: boolean;
  statusCode?: number;
  detail?: string;
  responseExcerpt?: string;
};

export type RuntimeReadinessResult = BootstrapStepResult & {
  step: "health-check";
  ready: boolean;
  backendReachable: boolean;
  startupReady: boolean;
  redisReady: boolean;
  chatReady: boolean;
  llmReady?: boolean;
  checks: HealthEndpointCheck[];
};

export type RuntimeReadiness = RuntimeReadinessResult;

export type RuntimeHealthCheckResult = RuntimeReadinessResult;

export type RuntimeBootstrapStatus =
  | "checking-requirements"
  | "docker-missing"
  | "compose-missing"
  | "docker-not-running"
  | "preparing-local-config"
  | "starting-local-services"
  | "waiting-for-ready"
  | "failed"
  | "ready-for-welcome";

export type RuntimeBootstrapState = {
  status: RuntimeBootstrapStatus;
  title: string;
  message: string;
  detail?: string;
  failureKind?: string;
  preflight: RuntimePreflight | null;
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>>;
};

export type RuntimeReadinessWaitResult = {
  ok: boolean;
  attempts: number;
  elapsedMs: number;
  lastCheck: RuntimeReadinessResult;
};

const WELCOME_DISMISSED_STORAGE_KEY = "cfy.bootstrap.welcomeDismissed";
const DOCKER_DESKTOP_DOWNLOAD_URL =
  "https://www.docker.com/products/docker-desktop/";

function asBoolean(value: unknown): boolean {
  return value === true;
}

function normalizeText(value: unknown): string | undefined {
  const normalized = String(value ?? "").trim();
  return normalized || undefined;
}

function normalizeFailureKind(value: unknown): string | undefined {
  return normalizeText(value)?.toLowerCase();
}

function normalizeExitCode(value: unknown): number | undefined {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function normalizeOptionalBoolean(value: unknown): boolean | undefined {
  if (value === true) return true;
  if (value === false) return false;
  return undefined;
}

function normalizeEndpointCheck(payload: unknown): HealthEndpointCheck {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  return {
    endpoint: String(source.endpoint ?? "").trim(),
    ok: asBoolean(source.ok),
    statusCode: normalizeExitCode(source.statusCode),
    detail: normalizeText(source.detail),
    responseExcerpt: normalizeText(source.responseExcerpt),
  };
}

function normalizeStep(step: unknown, fallback: BootstrapStep): BootstrapStep {
  if (step === "setup" || step === "compose-up" || step === "health-check") {
    return step;
  }
  return fallback;
}

function normalizeStepResult(
  payload: unknown,
  fallbackStep: BootstrapStep
): BootstrapStepResult {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  return {
    ok: asBoolean(source.ok ?? source.ready),
    step: normalizeStep(source.step, fallbackStep),
    detail: normalizeText(source.detail),
    command: normalizeText(source.command),
    stdout: normalizeText(source.stdout),
    stderr: normalizeText(source.stderr),
    exitCode: normalizeExitCode(source.exitCode),
  };
}

export function normalizeRuntimePreflight(payload: unknown): RuntimePreflight {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  const preflight: RuntimePreflight = {
    dockerCliInstalled: asBoolean(source.dockerCliInstalled),
    dockerComposeAvailable: asBoolean(source.dockerComposeAvailable),
    dockerDaemonReachable: asBoolean(source.dockerDaemonReachable),
    ready: asBoolean(source.ready),
    failureKind: normalizeFailureKind(source.failureKind),
    detail: normalizeText(source.detail),
  };

  if (
    preflight.ready &&
    (!preflight.dockerCliInstalled ||
      !preflight.dockerComposeAvailable ||
      !preflight.dockerDaemonReachable)
  ) {
    preflight.ready = false;
  }

  return preflight;
}

export function normalizeRuntimeReadiness(
  payload: unknown
): RuntimeReadinessResult {
  const base = normalizeStepResult(payload, "health-check");
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};
  const rawChecks = Array.isArray(source.checks) ? source.checks : [];

  return {
    ...base,
    step: "health-check",
    ok: asBoolean(source.ok ?? source.ready),
    ready: asBoolean(source.ready ?? source.ok),
    backendReachable: asBoolean(
      source.backendReachable ?? source.backend_reachable
    ),
    startupReady: asBoolean(source.startupReady ?? source.startup_ready),
    redisReady: asBoolean(source.redisReady ?? source.redis_ready),
    chatReady: asBoolean(source.chatReady ?? source.chat_ready),
    llmReady: normalizeOptionalBoolean(source.llmReady ?? source.llm_ready),
    checks: rawChecks.map((item) => normalizeEndpointCheck(item)),
  };
}

export function normalizeRuntimeHealthCheck(
  payload: unknown
): RuntimeReadinessResult {
  return normalizeRuntimeReadiness(payload);
}

type RuntimeBootstrapBuildOptions = {
  detail?: string;
  failureKind?: string;
  preflight?: RuntimePreflight | null;
  stepResults?: Partial<Record<BootstrapStep, BootstrapStepResult>>;
};

function buildRuntimeBootstrapState(
  status: RuntimeBootstrapStatus,
  title: string,
  message: string,
  options: RuntimeBootstrapBuildOptions = {}
): RuntimeBootstrapState {
  return {
    status,
    title,
    message,
    detail: options.detail,
    failureKind: options.failureKind,
    preflight: options.preflight ?? null,
    stepResults: options.stepResults ?? {},
  };
}

function formatPreflightDetail(preflight: RuntimePreflight): string | undefined {
  const lines = [
    `dockerCliInstalled=${preflight.dockerCliInstalled}`,
    `dockerComposeAvailable=${preflight.dockerComposeAvailable}`,
    `dockerDaemonReachable=${preflight.dockerDaemonReachable}`,
    `ready=${preflight.ready}`,
  ];
  if (preflight.failureKind) {
    lines.push(`failureKind=${preflight.failureKind}`);
  }
  if (preflight.detail) {
    lines.push("", preflight.detail);
  }
  return lines.join("\n").trim() || undefined;
}

type RuntimeReadinessPhase = "waiting" | "failed";

type RuntimeReadinessCopy = {
  title: string;
  message: string;
  failureKind: string;
};

function describeRuntimeReadinessCopy(
  readiness: RuntimeReadinessResult | null | undefined,
  phase: RuntimeReadinessPhase
): RuntimeReadinessCopy {
  const generic =
    phase === "waiting"
      ? {
          title: "Waiting for local beta runtime",
          message:
            "Codexify is polling the real local readiness surfaces until the supported beta loop is usable.",
          failureKind: "readiness-waiting",
        }
      : {
          title: "Codexify did not become ready in time",
          message:
            "The local beta runtime never satisfied the readiness contract. Retry the bootstrap or inspect the technical details below.",
          failureKind: "readiness-failed",
        };

  if (!readiness) {
    return generic;
  }

  if (!readiness.backendReachable) {
    return phase === "waiting"
      ? {
          title: "Backend is still starting",
          message:
            "The backend process has not responded to /ping yet, so the workspace stays locked until the local API comes up.",
          failureKind: "backend-unreachable",
        }
      : {
          title: "Backend never became reachable",
          message:
            "Compose started, but the backend process never answered /ping. Retry startup from the beginning once the local API is available.",
          failureKind: "backend-unreachable",
        };
  }

  if (!readiness.startupReady) {
    return phase === "waiting"
      ? {
          title: "Backend is warming up",
          message:
            "The backend responds, but /health has not reported a completed startup yet. Postgres-backed initialization may still be finishing.",
          failureKind: "startup-not-ready",
        }
      : {
          title: "Backend startup did not finish",
          message:
            "The backend answered /ping, but /health never reached a usable state. Retry the bootstrap so Postgres-backed startup can complete cleanly.",
          failureKind: "startup-not-ready",
        };
  }

  if (!readiness.redisReady || !readiness.chatReady) {
    return phase === "waiting"
      ? {
          title: "Redis or chat workers are still warming up",
          message:
            "The backend is up, but /health/chat still reports the Redis or worker-backed completion path as unavailable.",
          failureKind: "chat-path-unavailable",
        }
      : {
          title: "Redis or chat workers are unavailable",
          message:
            "The backend is up, but /health/chat never reported a healthy completion path. The workspace stays locked until Redis, queueing, and worker heartbeat are green.",
          failureKind: "chat-path-unavailable",
        };
  }

  if (readiness.llmReady === false) {
    return phase === "waiting"
      ? {
          title: "Model health is still red",
          message:
            "The backend and queue surfaces are up, but /health/llm still reports the model path as unavailable.",
          failureKind: "llm-unavailable",
        }
      : {
          title: "Model health did not recover",
          message:
            "The backend and queue surfaces are up, but /health/llm never became healthy. Retry once the model path is green.",
          failureKind: "llm-unavailable",
        };
  }

  return generic;
}

export function shouldRunRuntimeBootstrap(): boolean {
  return isTauriRuntime();
}

export function createCheckingRuntimeBootstrapState(
  detail?: string
): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "checking-requirements",
    "Checking local runtime",
    "Codexify is verifying Docker Desktop, Docker Compose, and daemon reachability before startup orchestration begins.",
    { detail }
  );
}

export function mapRuntimePreflightFailureToState(
  preflight: RuntimePreflight,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  const detail = appendBootstrapDetail(
    formatPreflightDetail(preflight),
    preflight.detail
  );

  if (preflight.failureKind === "docker-binary-not-found" || !preflight.dockerCliInstalled) {
    return buildRuntimeBootstrapState(
      "docker-missing",
      "Docker Desktop is required",
      "Codexify could not find a usable Docker installation on this machine. Install Docker Desktop, then retry the bootstrap check.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (
    preflight.failureKind === "docker-compose-unavailable" ||
    !preflight.dockerComposeAvailable
  ) {
    return buildRuntimeBootstrapState(
      "compose-missing",
      "Docker Compose is unavailable",
      "Codexify found Docker, but the Compose capability is not available from the native shell yet. Update Docker Desktop and retry.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (
    preflight.failureKind === "docker-daemon-unreachable" ||
    !preflight.dockerDaemonReachable
  ) {
    return buildRuntimeBootstrapState(
      "docker-not-running",
      "Docker Desktop is not responding yet",
      "Codexify found Docker on this machine, but the local daemon is not reachable. Start Docker Desktop, wait for it to finish initializing, then retry.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  return buildRuntimeBootstrapState(
    "failed",
    "Runtime preflight failed",
    "Codexify could not classify the Docker preflight cleanly. Retry the check and review the technical details below.",
    {
      detail,
      failureKind: preflight.failureKind,
      preflight,
      stepResults,
    }
  );
}

export function createPreparingLocalConfigState(
  preflight: RuntimePreflight,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "preparing-local-config",
    "Preparing local config",
    "Codexify is running the existing setup source of truth so local configuration stays aligned with the repo-defined bootstrap path.",
    { detail, preflight, stepResults }
  );
}

export function createStartingLocalServicesState(
  preflight: RuntimePreflight,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "starting-local-services",
    "Starting local services",
    "Codexify is bringing the local Docker Compose stack up from the repo runtime directory.",
    { detail, preflight, stepResults }
  );
}

export function createWaitingForReadyState(
  preflight: RuntimePreflight,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {},
  readiness?: RuntimeReadinessResult | null
): RuntimeBootstrapState {
  const copy = describeRuntimeReadinessCopy(readiness, "waiting");
  return buildRuntimeBootstrapState(
    "waiting-for-ready",
    copy.title,
    copy.message,
    { detail, preflight, stepResults }
  );
}

export function createReadyForWelcomeState(
  preflight: RuntimePreflight,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {},
  readiness?: RuntimeReadinessResult | null
): RuntimeBootstrapState {
  const modelStatus =
    readiness && typeof readiness.llmReady === "boolean"
      ? readiness.llmReady
        ? " The model health surface is green too."
        : " The model health surface is still red."
      : "";
  return buildRuntimeBootstrapState(
    "ready-for-welcome",
    "Local beta runtime is ready",
    `Docker preflight passed, setup completed, Compose is up, and the local beta readiness checks succeeded.${modelStatus} Transitioning into the welcome screen now.`,
    { detail, preflight, stepResults }
  );
}

export function mapRuntimeReadinessFailureToState(
  preflight: RuntimePreflight,
  readiness: RuntimeReadinessResult | null,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  const copy = describeRuntimeReadinessCopy(readiness, "failed");
  return buildRuntimeBootstrapState(
    "failed",
    copy.title,
    copy.message,
    {
      detail,
      failureKind: copy.failureKind,
      preflight,
      stepResults,
    }
  );
}

export function createFailedRuntimeBootstrapState(options: {
  title: string;
  message: string;
  detail?: string;
  failureKind?: string;
  preflight: RuntimePreflight;
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>>;
}): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "failed",
    options.title,
    options.message,
    {
      detail: options.detail,
      failureKind: options.failureKind,
      preflight: options.preflight,
      stepResults: options.stepResults,
    }
  );
}

export function appendBootstrapDetail(
  current: string | undefined,
  next: string | undefined,
  heading?: string
): string | undefined {
  const normalizedCurrent = normalizeText(current);
  const normalizedNext = normalizeText(next);

  if (!normalizedNext) return normalizedCurrent;

  const block = heading ? `${heading}\n${normalizedNext}` : normalizedNext;
  if (!normalizedCurrent) return block;

  if (normalizedCurrent.includes(block)) {
    return normalizedCurrent;
  }

  return `${normalizedCurrent}\n\n${block}`;
}

export function formatBootstrapStepResult(result: BootstrapStepResult): string {
  const lines = [
    `step=${result.step}`,
    `ok=${result.ok}`,
  ];
  if (result.command) {
    lines.push(`command=${result.command}`);
  }
  if (typeof result.exitCode === "number") {
    lines.push(`exitCode=${result.exitCode}`);
  }
  if (result.stdout) {
    lines.push("", "stdout:", result.stdout);
  }
  if (result.stderr) {
    lines.push("", "stderr:", result.stderr);
  }
  if (result.detail) {
    lines.push("", result.detail);
  }
  return lines.join("\n").trim();
}

export function formatRuntimeReadinessResult(
  result: RuntimeReadinessResult
): string {
  const lines = [
    `step=${result.step}`,
    `ok=${result.ok}`,
    `ready=${result.ready}`,
    `backendReachable=${result.backendReachable}`,
    `startupReady=${result.startupReady}`,
    `redisReady=${result.redisReady}`,
    `chatReady=${result.chatReady}`,
  ];
  if (typeof result.llmReady === "boolean") {
    lines.push(`llmReady=${result.llmReady}`);
  } else {
    lines.push("llmReady=not-gated");
  }
  if (result.command) {
    lines.push(`command=${result.command}`);
  }
  if (typeof result.exitCode === "number") {
    lines.push(`exitCode=${result.exitCode}`);
  }
  for (const check of result.checks) {
    lines.push(
      "",
      `${check.endpoint}: ok=${check.ok}${
        typeof check.statusCode === "number"
          ? ` statusCode=${check.statusCode}`
          : ""
      }`
    );
    if (check.detail) {
      lines.push(check.detail);
    }
    if (check.responseExcerpt) {
      lines.push(check.responseExcerpt);
    }
  }
  if (result.detail) {
    lines.push("", result.detail);
  }
  return lines.join("\n").trim();
}

export function formatRuntimeHealthCheckResult(
  result: RuntimeReadinessResult
): string {
  return formatRuntimeReadinessResult(result);
}

export async function runRuntimeBootstrapPreflight(): Promise<RuntimePreflight> {
  if (!shouldRunRuntimeBootstrap()) {
    return {
      dockerCliInstalled: false,
      dockerComposeAvailable: false,
      dockerDaemonReachable: false,
      ready: false,
      failureKind: "desktop-runtime-unavailable",
      detail: "window.__TAURI_IPC__ was not detected.",
    };
  }

  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_runtime_preflight_check"
    );
    return normalizeRuntimePreflight(payload);
  } catch (error) {
    return {
      dockerCliInstalled: false,
      dockerComposeAvailable: false,
      dockerDaemonReachable: false,
      ready: false,
      failureKind: "native-command-failed",
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

export async function runSetupCli(): Promise<BootstrapStepResult> {
  try {
    const payload = await invokeTauriCommand<unknown>("desktop_run_setup_cli");
    return normalizeStepResult(payload, "setup");
  } catch (error) {
    return {
      ok: false,
      step: "setup",
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

export async function runComposeUp(): Promise<BootstrapStepResult> {
  try {
    const payload = await invokeTauriCommand<unknown>("desktop_compose_up");
    return normalizeStepResult(payload, "compose-up");
  } catch (error) {
    return {
      ok: false,
      step: "compose-up",
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

export async function runRuntimeReadinessCheck(): Promise<RuntimeReadinessResult> {
  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_runtime_readiness_check"
    );
    return normalizeRuntimeReadiness(payload);
  } catch (error) {
    return {
      ok: false,
      ready: false,
      step: "health-check",
      backendReachable: false,
      startupReady: false,
      redisReady: false,
      chatReady: false,
      checks: [],
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

type RuntimeReadinessWaitOptions = {
  timeoutMs?: number;
  intervalMs?: number;
  onPoll?: (result: RuntimeReadinessResult, attempt: number) => void;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function waitForRuntimeReady(
  options: RuntimeReadinessWaitOptions = {}
): Promise<RuntimeReadinessWaitResult> {
  const timeoutMs = Math.max(5_000, options.timeoutMs ?? 180_000);
  const intervalMs = Math.max(500, options.intervalMs ?? 1_500);
  const startedAt = Date.now();
  let attempts = 0;
  let lastCheck = await runRuntimeReadinessCheck();
  attempts += 1;
  options.onPoll?.(lastCheck, attempts);

  while (!lastCheck.ready && Date.now() - startedAt < timeoutMs) {
    await sleep(intervalMs);
    lastCheck = await runRuntimeReadinessCheck();
    attempts += 1;
    options.onPoll?.(lastCheck, attempts);
  }

  return {
    ok: lastCheck.ready,
    attempts,
    elapsedMs: Date.now() - startedAt,
    lastCheck,
  };
}

export async function runRuntimeHealthCheck(): Promise<RuntimeReadinessResult> {
  return runRuntimeReadinessCheck();
}

export function hasDismissedWelcomeScreen(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(WELCOME_DISMISSED_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setWelcomeScreenDismissed(value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (value) {
      window.localStorage.setItem(WELCOME_DISMISSED_STORAGE_KEY, "1");
    } else {
      window.localStorage.removeItem(WELCOME_DISMISSED_STORAGE_KEY);
    }
  } catch {
    // Ignore storage failures in locked or private contexts.
  }
}

export async function openDockerDesktopDownloadPage(): Promise<boolean> {
  const opened = await openExternalUrl(DOCKER_DESKTOP_DOWNLOAD_URL);
  if (opened) return true;

  if (typeof window !== "undefined") {
    const popup = window.open(
      DOCKER_DESKTOP_DOWNLOAD_URL,
      "_blank",
      "noopener,noreferrer"
    );
    return popup !== null;
  }

  return false;
}
