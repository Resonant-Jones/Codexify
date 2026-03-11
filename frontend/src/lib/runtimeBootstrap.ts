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

export type RuntimeHealthCheckResult = BootstrapStepResult & {
  step: "health-check";
  ready: boolean;
  checks: HealthEndpointCheck[];
};

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
  lastCheck: RuntimeHealthCheckResult;
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
    ok: asBoolean(source.ok),
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

export function normalizeRuntimeHealthCheck(
  payload: unknown
): RuntimeHealthCheckResult {
  const base = normalizeStepResult(payload, "health-check");
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};
  const rawChecks = Array.isArray(source.checks) ? source.checks : [];

  return {
    ...base,
    step: "health-check",
    ready: asBoolean(source.ready),
    checks: rawChecks.map((item) => normalizeEndpointCheck(item)),
  };
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
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "waiting-for-ready",
    "Waiting for Codexify to become ready",
    "Codexify is polling the existing local readiness surfaces instead of sleeping blindly. The workspace stays locked until those checks pass.",
    { detail, preflight, stepResults }
  );
}

export function createReadyForWelcomeState(
  preflight: RuntimePreflight,
  detail?: string,
  stepResults: Partial<Record<BootstrapStep, BootstrapStepResult>> = {}
): RuntimeBootstrapState {
  return buildRuntimeBootstrapState(
    "ready-for-welcome",
    "Ready for welcome",
    "Docker preflight passed, setup completed, Compose is up, and the runtime health checks succeeded. Transitioning into the welcome screen now.",
    { detail, preflight, stepResults }
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

export function formatRuntimeHealthCheckResult(
  result: RuntimeHealthCheckResult
): string {
  const lines = [
    `step=${result.step}`,
    `ok=${result.ok}`,
    `ready=${result.ready}`,
  ];
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

export async function runRuntimeHealthCheck(): Promise<RuntimeHealthCheckResult> {
  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_runtime_health_check"
    );
    return normalizeRuntimeHealthCheck(payload);
  } catch (error) {
    return {
      ok: false,
      ready: false,
      step: "health-check",
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
  onPoll?: (result: RuntimeHealthCheckResult, attempt: number) => void;
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
  let lastCheck = await runRuntimeHealthCheck();
  attempts += 1;
  options.onPoll?.(lastCheck, attempts);

  while (!lastCheck.ready && Date.now() - startedAt < timeoutMs) {
    await sleep(intervalMs);
    lastCheck = await runRuntimeHealthCheck();
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
