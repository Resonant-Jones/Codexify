export type TauriCoreApi = {
  invoke: <T = unknown>(
    command: string,
    payload?: Record<string, unknown>
  ) => Promise<T>;
};

const TAURI_CORE_WINDOW_KEY = "__CFY_TAURI_CORE__";

export const NATIVE_BRIDGE_FAILURE_KIND = "native-bridge-unavailable" as const;

export class NativeBridgeUnavailableError extends Error {
  readonly code = NATIVE_BRIDGE_FAILURE_KIND;

  constructor(message: string) {
    super(message);
    this.name = "NativeBridgeUnavailableError";
  }
}

function readInjectedTauriCore(): TauriCoreApi | null {
  if (typeof window === "undefined") return null;
  const candidate = (window as any)[TAURI_CORE_WINDOW_KEY];
  if (!candidate || typeof candidate.invoke !== "function") return null;
  return candidate as TauriCoreApi;
}

export function isTauriRuntime(): boolean {
  if (typeof window === "undefined") return false;
  return (
    typeof (window as any).__TAURI_IPC__ !== "undefined" ||
    typeof (window as any).__TAURI_INTERNALS__ !== "undefined"
  );
}

export async function loadTauriCore(): Promise<TauriCoreApi> {
  const injected = readInjectedTauriCore();
  if (injected) return injected;

  try {
    return (await import("@tauri-apps/api/core")) as TauriCoreApi;
  } catch (error) {
    const detail =
      error instanceof Error
        ? error.message
        : String(error ?? "Unknown native bridge import error");
    throw new NativeBridgeUnavailableError(detail);
  }
}

export async function invokeTauriCommand<T = unknown>(
  command: string,
  payload?: Record<string, unknown>
): Promise<T> {
  if (!isTauriRuntime()) {
    throw new NativeBridgeUnavailableError(
      "Tauri native bridge is unavailable outside the desktop runtime."
    );
  }
  const core = await loadTauriCore();
  return core.invoke<T>(command, payload);
}
