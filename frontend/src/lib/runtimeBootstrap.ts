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

export type RuntimeBootstrapStatus =
  | "checking"
  | "docker-missing"
  | "compose-missing"
  | "docker-not-running"
  | "ready"
  | "error";

export type RuntimeBootstrapState = {
  status: RuntimeBootstrapStatus;
  title: string;
  message: string;
  detail?: string;
  preflight: RuntimePreflight | null;
};

const WELCOME_DISMISSED_STORAGE_KEY = "cfy.bootstrap.welcomeDismissed";
const DOCKER_DESKTOP_DOWNLOAD_URL =
  "https://www.docker.com/products/docker-desktop/";

function asBoolean(value: unknown): boolean {
  return value === true;
}

function normalizeDetail(value: unknown): string | undefined {
  const normalized = String(value ?? "").trim();
  return normalized ? normalized : undefined;
}

function normalizeFailureKind(value: unknown): string | undefined {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized || undefined;
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

export function createCheckingRuntimeBootstrapState(): RuntimeBootstrapState {
  return {
    status: "checking",
    title: "Checking local runtime",
    message:
      "Codexify is verifying that Docker Desktop is installed, Compose is available, and the local daemon is reachable.",
    detail: undefined,
    preflight: null,
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
    detail: normalizeDetail(source.detail),
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

export function mapRuntimePreflightToState(
  preflight: RuntimePreflight
): RuntimeBootstrapState {
  const detail = formatPreflightDetail(preflight);

  if (preflight.ready) {
    return {
      status: "ready",
      title: "Runtime preflight passed",
      message:
        "Docker Desktop is available and the local daemon is responding. Continue into Codexify when you are ready.",
      detail,
      preflight,
    };
  }

  if (preflight.failureKind === "docker-binary-not-found") {
    return {
      status: "docker-missing",
      title: "Docker Desktop is required",
      message:
        "Codexify beta requires Docker Desktop, and the native preflight could not find a usable Docker installation on this machine.",
      detail,
      preflight,
    };
  }

  if (preflight.failureKind === "docker-compose-unavailable") {
    return {
      status: "compose-missing",
      title: "Docker Compose is unavailable",
      message:
        "Codexify found the Docker CLI, but the Compose capability is unavailable or not discoverable from the native shell.",
      detail,
      preflight,
    };
  }

  if (preflight.failureKind === "docker-daemon-unreachable") {
    return {
      status: "docker-not-running",
      title: "Docker Desktop is installed, but not responding yet",
      message:
        "Codexify found Docker on this machine, but it cannot talk to the local daemon yet. Start Docker Desktop, wait for it to finish initializing, then retry.",
      detail,
      preflight,
    };
  }

  if (
    preflight.failureKind === "docker-cli-invocation-failed" ||
    preflight.failureKind === "unexpected-command-execution-error" ||
    preflight.failureKind
  ) {
    return {
      status: "error",
      title: "Native runtime diagnostics hit an unexpected error",
      message:
        "Codexify could not complete the Docker preflight cleanly. Retry the check and review the native diagnostics below.",
      detail,
      preflight,
    };
  }

  if (!preflight.dockerCliInstalled) {
    return {
      status: "docker-missing",
      title: "Docker Desktop is required",
      message:
        "Codexify beta requires Docker Desktop, and the native preflight could not find a usable Docker installation on this machine.",
      detail,
      preflight,
    };
  }

  if (!preflight.dockerComposeAvailable) {
    return {
      status: "compose-missing",
      title: "Docker Compose is unavailable",
      message:
        "Codexify found the Docker CLI, but the Compose capability is unavailable or not discoverable from the native shell.",
      detail,
      preflight,
    };
  }

  if (!preflight.dockerDaemonReachable) {
    return {
      status: "docker-not-running",
      title: "Docker Desktop is installed, but not responding yet",
      message:
        "Codexify found Docker on this machine, but it cannot talk to the local daemon yet. Start Docker Desktop, wait for it to finish initializing, then retry.",
      detail,
      preflight,
    };
  }

  return {
    status: "error",
    title: "Native runtime diagnostics hit an unexpected error",
    message:
      "Codexify could not classify the Docker preflight result cleanly. Retry the check and review the native diagnostics below.",
    detail,
    preflight,
  };
}

export async function runRuntimeBootstrapPreflight(): Promise<RuntimeBootstrapState> {
  if (!shouldRunRuntimeBootstrap()) {
    return {
      status: "error",
      title: "Desktop runtime unavailable",
      message:
        "Runtime preflight can only run inside the native Codexify shell.",
      detail: "window.__TAURI_IPC__ was not detected.",
      preflight: null,
    };
  }

  try {
    const payload = await invokeTauriCommand<unknown>(
      "desktop_runtime_preflight_check"
    );
    return mapRuntimePreflightToState(normalizeRuntimePreflight(payload));
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : String(error ?? "Unknown error");
    return {
      status: "error",
      title: "Native runtime diagnostics hit an unexpected error",
      message:
        "Codexify could not complete the native Docker preflight command. Retry the check and review the diagnostics below.",
      detail,
      preflight: null,
    };
  }
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
