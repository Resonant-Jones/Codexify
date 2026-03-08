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
  detail?: string;
};

export type RuntimeBootstrapStatus =
  | "checking"
  | "docker-missing"
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

function formatPreflightDetail(preflight: RuntimePreflight): string | undefined {
  const lines = [
    `dockerCliInstalled=${preflight.dockerCliInstalled}`,
    `dockerComposeAvailable=${preflight.dockerComposeAvailable}`,
    `dockerDaemonReachable=${preflight.dockerDaemonReachable}`,
    `ready=${preflight.ready}`,
  ];
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

  if (!preflight.dockerCliInstalled || !preflight.dockerComposeAvailable) {
    return {
      status: "docker-missing",
      title: "Docker Desktop is required",
      message: preflight.dockerCliInstalled
        ? "Docker was found, but Docker Compose is unavailable. Install or update Docker Desktop before continuing."
        : "Install Docker Desktop to give Codexify a local runtime with Docker CLI and Docker Compose support.",
      detail,
      preflight,
    };
  }

  if (!preflight.dockerDaemonReachable) {
    return {
      status: "docker-not-running",
      title: "Start Docker Desktop to continue",
      message:
        "Docker is installed, but the local daemon is not reachable yet. Launch Docker Desktop and retry the preflight check.",
      detail,
      preflight,
    };
  }

  return {
    status: "error",
    title: "Runtime preflight failed",
    message:
      "Codexify could not determine the local Docker runtime state. Retry the check to capture a fresh diagnostic snapshot.",
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
      title: "Runtime preflight failed",
      message:
        "Codexify could not complete the Docker preflight command. Retry the check to gather a fresh status.",
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
