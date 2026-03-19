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
  runtimeContext?: "development" | "packaged";
  repoRoot?: string;
  runtimeHome?: string;
  runtimeRoot?: string;
  packaged?: boolean;
};

export type BootstrapStep = "setup" | "compose-up" | "health-check";

export type BootstrapRecoveryStage =
  | "preflight"
  | "setup"
  | "compose-up"
  | "readiness";

export type BootstrapRecoveryAction =
  | "retry"
  | "view-logs"
  | "open-docker"
  | "restart-services"
  | "install-docker";

export type BootstrapLogService =
  | "backend"
  | "worker-chat"
  | "db"
  | "redis"
  | "migrator";

export type BootstrapStepResult = {
  ok: boolean;
  step: BootstrapStep;
  detail?: string;
  failureKind?: string;
  runtimeContext?: "development" | "packaged";
  repoRoot?: string;
  runtimeHome?: string;
  runtimeRoot?: string;
  packaged?: boolean;
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

export type BootstrapDockerOpenResult = {
  ok: boolean;
  detail?: string;
  command?: string;
};

export type BootstrapLogResult = {
  ok: boolean;
  service: BootstrapLogService;
  detail?: string;
  failureKind?: string;
  runtimeContext?: "development" | "packaged";
  repoRoot?: string;
  runtimeHome?: string;
  runtimeRoot?: string;
  packaged?: boolean;
  logs?: string;
  command?: string;
  exitCode?: number;
};

export type BootstrapRestartResult = {
  ok: boolean;
  detail?: string;
  failureKind?: string;
  runtimeContext?: "development" | "packaged";
  repoRoot?: string;
  runtimeHome?: string;
  runtimeRoot?: string;
  packaged?: boolean;
  command?: string;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
  services: string[];
};

export type BootstrapRecoveryNotice = {
  kind:
    | "logs-unavailable"
    | "docker-open-failed"
    | "restart-services-failed";
  title: string;
  message: string;
  detail?: string;
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
  lastCheck: RuntimeReadinessResult;
};

const WELCOME_DISMISSED_STORAGE_KEY = "cfy.bootstrap.welcomeDismissed";
const DOCKER_DESKTOP_DOWNLOAD_URL =
  "https://www.docker.com/products/docker-desktop/";
export const BOOTSTRAP_LOG_SERVICES: BootstrapLogService[] = [
  "backend",
  "worker-chat",
  "db",
  "redis",
  "migrator",
];

function asBoolean(value: unknown): boolean {
  return value === true;
}

function normalizeText(value: unknown): string | undefined {
  const normalized = String(value ?? "").trim();
  return normalized || undefined;
}

function normalizeFailureKind(value: unknown): string | undefined {
  const normalized = normalizeText(value)?.toLowerCase();
  if (!normalized) {
    return undefined;
  }

  switch (normalized) {
    case "runtime-path-unavailable":
      return "runtime-path-unavailable";
    case "runtime-root-unavailable":
      return "runtime-root-unavailable";
    case "runtime-home-unavailable":
    case "packaged-runtime-home-unusable":
      return "runtime-root-unavailable";
    case "repo-runtime-missing":
      return "packaged-runtime-assets-missing";
    case "docker-mount-path-unshared-or-unsupported":
      return "docker-mount-path-unshared-or-unsupported";
    case "docker-binary-not-found":
      return "docker-cli-unavailable";
    case "docker-cli-invocation-failed":
      return "docker-cli-execution-failed";
    case "docker-daemon-unreachable":
      return "docker-daemon-unavailable";
    default:
      return normalized;
  }
}

function normalizeRuntimeContext(
  value: unknown
): "development" | "packaged" | undefined {
  return value === "development" || value === "packaged" ? value : undefined;
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

function normalizeBootstrapLogService(
  value: unknown,
  fallback: BootstrapLogService
): BootstrapLogService {
  return BOOTSTRAP_LOG_SERVICES.includes(value as BootstrapLogService)
    ? (value as BootstrapLogService)
    : fallback;
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
    failureKind: normalizeFailureKind(source.failureKind),
    runtimeContext: normalizeRuntimeContext(source.runtimeContext),
    repoRoot: normalizeText(source.repoRoot),
    runtimeHome: normalizeText(source.runtimeHome),
    runtimeRoot: normalizeText(source.runtimeRoot),
    packaged: normalizeOptionalBoolean(source.packaged),
    command: normalizeText(source.command),
    stdout: normalizeText(source.stdout),
    stderr: normalizeText(source.stderr),
    exitCode: normalizeExitCode(source.exitCode),
  };
}

function normalizeBootstrapDockerOpenResult(
  payload: unknown
): BootstrapDockerOpenResult {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  return {
    ok: asBoolean(source.ok),
    detail: normalizeText(source.detail),
    command: normalizeText(source.command),
  };
}

function normalizeBootstrapLogResult(
  payload: unknown,
  fallbackService: BootstrapLogService
): BootstrapLogResult {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  return {
    ok: asBoolean(source.ok),
    service: normalizeBootstrapLogService(source.service, fallbackService),
    detail: normalizeText(source.detail),
    failureKind: normalizeFailureKind(source.failureKind),
    runtimeContext: normalizeRuntimeContext(source.runtimeContext),
    repoRoot: normalizeText(source.repoRoot),
    runtimeHome: normalizeText(source.runtimeHome),
    runtimeRoot: normalizeText(source.runtimeRoot),
    packaged: normalizeOptionalBoolean(source.packaged),
    logs: normalizeText(source.logs),
    command: normalizeText(source.command),
    exitCode: normalizeExitCode(source.exitCode),
  };
}

function normalizeBootstrapRestartResult(
  payload: unknown
): BootstrapRestartResult {
  const source =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : {};

  const services = Array.isArray(source.services)
    ? source.services
        .map((entry) => normalizeText(entry))
        .filter((entry): entry is string => Boolean(entry))
    : [];

  return {
    ok: asBoolean(source.ok),
    detail: normalizeText(source.detail),
    failureKind: normalizeFailureKind(source.failureKind),
    runtimeContext: normalizeRuntimeContext(source.runtimeContext),
    repoRoot: normalizeText(source.repoRoot),
    runtimeHome: normalizeText(source.runtimeHome),
    runtimeRoot: normalizeText(source.runtimeRoot),
    packaged: normalizeOptionalBoolean(source.packaged),
    command: normalizeText(source.command),
    stdout: normalizeText(source.stdout),
    stderr: normalizeText(source.stderr),
    exitCode: normalizeExitCode(source.exitCode),
    services,
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
    runtimeContext: normalizeRuntimeContext(source.runtimeContext),
    repoRoot: normalizeText(source.repoRoot),
    runtimeHome: normalizeText(source.runtimeHome),
    runtimeRoot: normalizeText(source.runtimeRoot),
    packaged: normalizeOptionalBoolean(source.packaged),
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
  if (preflight.runtimeContext) {
    lines.push(`runtimeContext=${preflight.runtimeContext}`);
  }
  if (typeof preflight.packaged === "boolean") {
    lines.push(`packaged=${preflight.packaged}`);
  }
  if (preflight.repoRoot) {
    lines.push(`repoRoot=${preflight.repoRoot}`);
  }
  if (preflight.runtimeHome) {
    lines.push(`runtimeHome=${preflight.runtimeHome}`);
  }
  if (preflight.runtimeRoot) {
    lines.push(`runtimeRoot=${preflight.runtimeRoot}`);
  }
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
            "The local beta runtime never satisfied the readiness contract. Retry the readiness checks first, then restart services if the runtime still looks wedged.",
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
            "Compose started, but the backend process never answered /ping. Retry the readiness gate first, then restart services if the API is still unavailable.",
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
            "The backend answered /ping, but /health never reached a usable state. Retry readiness first so startup can settle, then restart services if it stays stuck.",
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
            "The backend is up, but /health/chat never reported a healthy completion path. View logs or restart services if Redis, queueing, or worker heartbeat stay red.",
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
            "The backend and queue surfaces are up, but /health/llm never became healthy. Retry readiness first, then inspect logs or restart services if the model path stays red.",
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

  if (preflight.failureKind === "runtime-root-unavailable") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged runtime root is unavailable",
      "Codexify could not resolve or create its Docker-compatible packaged runtime root, so startup stayed locked before setup or Compose could run.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "packaged-runtime-assets-missing") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged runtime assets are missing",
      "This packaged build could not find the bundled runtime source it needs to materialize setup, Compose, and recovery assets into the packaged runtime root.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "packaged-runtime-materialization-failed") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged runtime materialization failed",
      "Codexify found the packaged runtime payload, but it could not finish copying the required bootstrap assets into the Docker-compatible packaged runtime root.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "packaged-runtime-assets-invalid") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged runtime assets are invalid",
      "Codexify found the packaged runtime root, but the materialized payload is incomplete or invalid for setup and Compose startup.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "docker-mount-path-unshared-or-unsupported") {
    return buildRuntimeBootstrapState(
      "failed",
      "Docker rejected the packaged runtime mount path",
      "Docker Desktop rejected the packaged runtime root path during Compose startup. This is a mount-path contract problem, not a missing Docker installation, so the workspace stayed locked.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "packaged-bootstrap-unsupported") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged bootstrap is not yet supported",
      "This macOS artifact launched without a packaged runtime payload it can safely attach to, so the workspace stayed locked instead of falling back to a development checkout.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (
    preflight.failureKind ===
    "docker-cli-found-but-unusable-from-packaged-context"
  ) {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged app could not execute Docker",
      "Codexify found a Docker installation, but this Finder-launched packaged app could not execute the Docker CLI cleanly from the current macOS launch context. The workspace stayed locked instead of pretending Docker is ready.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (preflight.failureKind === "docker-cli-execution-failed") {
    return buildRuntimeBootstrapState(
      "failed",
      "Docker CLI execution failed",
      "Codexify found Docker, but the Docker CLI could not be executed successfully from the current app context. Retry first, then inspect the technical details below before reinstalling Docker Desktop.",
      {
        detail,
        failureKind: preflight.failureKind,
        preflight,
        stepResults,
      }
    );
  }

  if (!preflight.dockerCliInstalled || preflight.failureKind === "docker-cli-unavailable") {
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
    preflight.failureKind === "docker-daemon-unavailable" ||
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

  if (preflight.packaged && preflight.failureKind === "unexpected-execution-error") {
    return buildRuntimeBootstrapState(
      "failed",
      "Packaged startup failed unexpectedly",
      "The packaged desktop shell hit an unexpected startup error while validating the local runtime context. Retry first, then review the technical details below before trying broader recovery steps.",
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
    "Codexify is running the setup source of truth so local configuration stays aligned with the resolved packaged runtime root.",
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
    "Codexify is bringing the local Docker Compose stack up from the Docker-compatible packaged runtime root.",
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
  const failureKind =
    readiness?.failureKind ??
    (preflight.packaged ? "packaged-readiness-failed" : copy.failureKind);
  return buildRuntimeBootstrapState(
    "failed",
    copy.title,
    copy.message,
    {
      detail,
      failureKind,
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

function stateFailureKind(state: RuntimeBootstrapState): string | undefined {
  return normalizeFailureKind(
    state.failureKind ??
      state.preflight?.failureKind ??
      state.stepResults["health-check"]?.failureKind ??
      state.stepResults["compose-up"]?.failureKind ??
      state.stepResults.setup?.failureKind
  );
}

export function isPackagedBootstrapState(state: RuntimeBootstrapState): boolean {
  return (
    state.preflight?.packaged === true ||
    state.stepResults.setup?.packaged === true ||
    state.stepResults["compose-up"]?.packaged === true ||
    state.stepResults["health-check"]?.packaged === true
  );
}

export function getBootstrapDisplayCopy(state: RuntimeBootstrapState): {
  title: string;
  message: string;
} {
  const failureKind = stateFailureKind(state);
  const packaged = isPackagedBootstrapState(state);

  if (failureKind === "runtime-root-unavailable") {
    return {
      title: "Packaged runtime root is unavailable",
      message:
        "The packaged app could not resolve or create its Docker-compatible packaged runtime root, so startup stayed locked.",
    };
  }

  if (failureKind === "packaged-runtime-assets-missing") {
    return {
      title: "Packaged runtime assets are missing",
      message:
        "This packaged build could not find the bundled runtime source it needs to materialize setup, Compose, and recovery assets into the packaged runtime root.",
    };
  }

  if (failureKind === "packaged-runtime-materialization-failed") {
    return {
      title: "Packaged runtime materialization failed",
      message:
        "Codexify found the packaged runtime payload, but it could not safely copy the required bootstrap assets into the packaged runtime root.",
    };
  }

  if (failureKind === "packaged-runtime-assets-invalid") {
    return {
      title: "Packaged runtime assets are invalid",
      message:
        "The packaged runtime root was found, but the materialized payload is incomplete or invalid for setup, Compose startup, or recovery commands.",
    };
  }

  if (failureKind === "docker-mount-path-unshared-or-unsupported") {
    return {
      title: "Docker rejected the packaged runtime mount path",
      message:
        "Docker Desktop rejected the packaged runtime root during Compose startup. Codexify kept the workspace locked and did not misclassify this as a Docker installation problem.",
    };
  }

  if (failureKind === "packaged-bootstrap-unsupported") {
    return {
      title: "Packaged bootstrap is not yet supported",
      message:
        "This macOS artifact launched without a packaged runtime payload it can safely attach to yet, so the workspace stayed locked instead of falling back to a development checkout.",
    };
  }

  if (failureKind === "docker-cli-unavailable") {
    return {
      title: "Docker Desktop is required",
      message:
        "Codexify could not find a usable Docker CLI or Compose entrypoint on this machine. Install or repair Docker Desktop, then retry.",
    };
  }

  if (failureKind === "docker-cli-execution-failed") {
    return {
      title: "Docker CLI execution failed",
      message:
        "Codexify found Docker, but the CLI could not be executed successfully from the current app context. Retry first, then inspect the technical details below before reinstalling Docker Desktop.",
    };
  }

  if (
    failureKind === "docker-cli-found-but-unusable-from-packaged-context"
  ) {
    return {
      title: "Packaged app could not execute Docker",
      message:
        "Codexify found Docker on this machine, but this Finder-launched packaged app could not execute it correctly from the current macOS launch context. The workspace stayed locked instead of telling you to reinstall Docker Desktop.",
    };
  }

  if (failureKind === "docker-daemon-unavailable") {
    return {
      title: "Docker Desktop is not responding yet",
      message:
        "Docker is installed, but the local daemon is not reachable yet. Open Docker Desktop, wait for it to finish starting, then retry.",
    };
  }

  if (failureKind === "runtime-path-unavailable") {
    return {
      title: "Codexify could not inspect the packaged startup path",
      message:
        "The packaged desktop shell could not determine a safe runtime path, so it kept the workspace locked instead of guessing at local state. Retry once, then relaunch the produced Codexify.app if this keeps happening.",
    };
  }

  if (packaged && failureKind === "unexpected-execution-error") {
    return {
      title: "Packaged startup failed unexpectedly",
      message:
        "The macOS beta artifact reached the packaged bootstrap path but hit an unexpected execution error. Retry first, then review the technical details below before trying broader recovery.",
    };
  }

  if (failureKind === "packaged-setup-failed") {
    return {
      title: "Packaged setup failed",
      message:
        "The packaged app passed Docker preflight, but the setup step did not complete cleanly from the materialized packaged runtime root. Retry to rerun setup while the workspace stays locked.",
    };
  }

  if (failureKind === "packaged-compose-up-failed") {
    return {
      title: "Packaged Compose startup failed",
      message:
        "The packaged app completed setup, but Docker Compose did not come up cleanly from the packaged runtime root. Retry first, then inspect logs or restart services if the runtime looks partially up.",
    };
  }

  if (failureKind === "packaged-readiness-failed") {
    return {
      title: state.title,
      message: `${state.message} This happened after the packaged app had already completed setup and Compose startup from the materialized packaged runtime root.`,
    };
  }

  if (
    packaged &&
    (failureKind === "setup-failed" || failureKind === "compose-up-failed")
  ) {
    return {
      title: "Packaged startup failed",
      message:
        "The macOS beta artifact found the local runtime context, but setup or Compose did not complete cleanly. Retry first, then use logs or service restart recovery if the runtime looks partially up.",
    };
  }

  return {
    title: state.title,
    message: state.message,
  };
}

export function getBootstrapRecoveryStage(
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

export function getBootstrapRecoveryActions(
  state: RuntimeBootstrapState
): BootstrapRecoveryAction[] {
  const stage = getBootstrapRecoveryStage(state);

  if (state.status === "docker-missing") {
    return ["retry", "install-docker"];
  }

  if (state.status === "compose-missing") {
    return ["retry", "install-docker"];
  }

  if (state.status === "docker-not-running") {
    return ["retry", "open-docker"];
  }

  const failureKind = stateFailureKind(state);

  if (
    failureKind === "docker-cli-execution-failed" ||
    failureKind === "docker-cli-found-but-unusable-from-packaged-context"
  ) {
    return ["retry"];
  }

  if (stage === "setup") {
    return ["retry"];
  }

  if (stage === "compose-up" || stage === "readiness") {
    return ["retry", "view-logs", "restart-services"];
  }

  if (stage === "preflight") {
    return ["retry"];
  }

  return [];
}

export function getDefaultBootstrapLogService(
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

export function createBootstrapSupportNoticeFromLogResult(
  result: BootstrapLogResult
): BootstrapRecoveryNotice | null {
  if (result.ok) return null;

  if (result.failureKind === "runtime-root-unavailable") {
    return {
      kind: "logs-unavailable",
      title: "Packaged runtime root is unavailable",
      message:
        "Codexify could not resolve or create its Docker-compatible packaged runtime root, so it did not attempt to read Compose logs.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-assets-missing") {
    return {
      kind: "logs-unavailable",
      title: "Packaged runtime assets are missing",
      message:
        "Codexify could not find the bundled runtime payload it needs to attach Compose logs from the packaged app.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-materialization-failed") {
    return {
      kind: "logs-unavailable",
      title: "Packaged runtime materialization failed",
      message:
        "Codexify found the packaged runtime payload, but it could not finish copying it into the packaged runtime root, so logs are unavailable.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-assets-invalid") {
    return {
      kind: "logs-unavailable",
      title: "Packaged runtime assets are invalid",
      message:
        "Codexify found the packaged runtime root, but the materialized payload is incomplete or invalid, so Compose logs stayed unavailable.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "docker-mount-path-unshared-or-unsupported") {
    return {
      kind: "logs-unavailable",
      title: "Docker rejected the packaged runtime mount path",
      message:
        "Docker Desktop rejected the packaged runtime root path during Compose startup, so Codexify could not attach useful Compose logs from that attempt.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-bootstrap-unsupported") {
    return {
      kind: "logs-unavailable",
      title: "Packaged bootstrap is not yet supported",
      message:
        "This packaged build does not yet include a runtime payload it can safely attach to, so log access stayed locked.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "runtime-path-unavailable") {
    return {
      kind: "logs-unavailable",
      title: "Runtime path is unavailable",
      message:
        "Codexify could not determine a safe local runtime path, so it did not attempt to read Compose logs.",
      detail: result.detail,
    };
  }

  return {
    kind: "logs-unavailable",
    title: "Recent logs are unavailable",
    message: `Codexify could not load recent ${result.service} logs from the local Compose runtime. Retry the log fetch or verify Docker and the service state directly.`,
    detail: result.detail,
  };
}

export function createBootstrapSupportNoticeFromDockerOpenResult(
  result: BootstrapDockerOpenResult
): BootstrapRecoveryNotice | null {
  if (result.ok) return null;

  return {
    kind: "docker-open-failed",
    title: "Docker Desktop did not open",
    message:
      "Codexify could not launch Docker Desktop through the native macOS open path. Start Docker Desktop manually, wait for the daemon to come up, then retry preflight.",
    detail: result.detail,
  };
}

export function createBootstrapSupportNoticeFromRestartResult(
  result: BootstrapRestartResult
): BootstrapRecoveryNotice | null {
  if (result.ok) return null;

  if (result.failureKind === "runtime-root-unavailable") {
    return {
      kind: "restart-services-failed",
      title: "Packaged runtime root is unavailable",
      message:
        "Codexify could not resolve or create its Docker-compatible packaged runtime root, so it did not attempt a service restart.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-assets-missing") {
    return {
      kind: "restart-services-failed",
      title: "Packaged runtime assets are missing",
      message:
        "Codexify could not find the bundled runtime payload it needs to restart services from the packaged app.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-materialization-failed") {
    return {
      kind: "restart-services-failed",
      title: "Packaged runtime materialization failed",
      message:
        "Codexify found the packaged runtime payload, but it could not finish copying it into the packaged runtime root, so service restart is unavailable.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-runtime-assets-invalid") {
    return {
      kind: "restart-services-failed",
      title: "Packaged runtime assets are invalid",
      message:
        "Codexify found the packaged runtime root, but the materialized payload is incomplete or invalid, so service restart stayed unavailable.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "docker-mount-path-unshared-or-unsupported") {
    return {
      kind: "restart-services-failed",
      title: "Docker rejected the packaged runtime mount path",
      message:
        "Docker Desktop rejected the packaged runtime root path during Compose startup, so Codexify left the workspace locked instead of retrying a misleading service restart.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "packaged-bootstrap-unsupported") {
    return {
      kind: "restart-services-failed",
      title: "Packaged bootstrap is not yet supported",
      message:
        "This packaged build does not yet include a runtime payload it can safely attach to, so service restart stayed locked.",
      detail: result.detail,
    };
  }

  if (result.failureKind === "runtime-path-unavailable") {
    return {
      kind: "restart-services-failed",
      title: "Runtime path is unavailable",
      message:
        "Codexify could not determine a safe local runtime path, so it did not attempt a service restart.",
      detail: result.detail,
    };
  }

  return {
    kind: "restart-services-failed",
    title: "Service restart failed",
    message:
      "Codexify could not complete the targeted Compose restart/start recovery flow. Review the command detail and runtime logs before retrying.",
    detail: result.detail,
  };
}

export function createComposeRecoveryStepResult(
  result: BootstrapRestartResult
): BootstrapStepResult {
  return {
    ok: result.ok,
    step: "compose-up",
    detail: result.detail,
    failureKind: result.failureKind,
    runtimeContext: result.runtimeContext,
    repoRoot: result.repoRoot,
    runtimeHome: result.runtimeHome,
    packaged: result.packaged,
    command: result.command,
    stdout: result.stdout,
    stderr: result.stderr,
    exitCode: result.exitCode,
  };
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
  if (result.runtimeContext) {
    lines.push(`runtimeContext=${result.runtimeContext}`);
  }
  if (typeof result.packaged === "boolean") {
    lines.push(`packaged=${result.packaged}`);
  }
  if (result.repoRoot) {
    lines.push(`repoRoot=${result.repoRoot}`);
  }
  if (result.runtimeHome) {
    lines.push(`runtimeHome=${result.runtimeHome}`);
  }
  if (result.runtimeRoot) {
    lines.push(`runtimeRoot=${result.runtimeRoot}`);
  }
  if (result.failureKind) {
    lines.push(`failureKind=${result.failureKind}`);
  }
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
  if (result.runtimeContext) {
    lines.push(`runtimeContext=${result.runtimeContext}`);
  }
  if (typeof result.packaged === "boolean") {
    lines.push(`packaged=${result.packaged}`);
  }
  if (result.runtimeHome) {
    lines.push(`runtimeHome=${result.runtimeHome}`);
  }
  if (result.runtimeRoot) {
    lines.push(`runtimeRoot=${result.runtimeRoot}`);
  }
  if (result.failureKind) {
    lines.push(`failureKind=${result.failureKind}`);
  }
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

export async function openDockerDesktopNative(): Promise<BootstrapDockerOpenResult> {
  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_open_docker_desktop"
    );
    return normalizeBootstrapDockerOpenResult(payload);
  } catch (error) {
    return {
      ok: false,
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

export async function getBootstrapLogs(
  service: BootstrapLogService
): Promise<BootstrapLogResult> {
  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_get_bootstrap_logs",
      { service }
    );
    return normalizeBootstrapLogResult(payload, service);
  } catch (error) {
    return {
      ok: false,
      service,
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
    };
  }
}

export async function restartRuntimeServices(): Promise<BootstrapRestartResult> {
  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_restart_runtime_services"
    );
    return normalizeBootstrapRestartResult(payload);
  } catch (error) {
    return {
      ok: false,
      detail:
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
      services: [],
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
