function normalizeApiKey(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

let runtimeApiKey: string | null = null;
let runtimeApiKeyResolved = false;
let runtimeAuthVersion = 0;
const runtimeAuthListeners = new Set<() => void>();

export type RuntimeAuthSource =
  | "runtime-desktop"
  | "vite-dev"
  | "bearer-only"
  | "none"
  | "unknown";

export function resolveRuntimeAuthSource(options: {
  isTauriRuntime: boolean;
  runtimeDesktopKeyPresent: boolean;
  devKeyPresent: boolean;
  bearerPresent: boolean;
  desktopAuthConfigKnown: boolean;
}): RuntimeAuthSource {
  if (options.isTauriRuntime && options.runtimeDesktopKeyPresent) {
    return "runtime-desktop";
  }
  if (!options.isTauriRuntime && options.devKeyPresent) {
    return "vite-dev";
  }
  if (options.bearerPresent) {
    return "bearer-only";
  }
  if (options.isTauriRuntime) {
    return options.desktopAuthConfigKnown ? "none" : "unknown";
  }
  if (options.devKeyPresent) {
    return "vite-dev";
  }
  return "none";
}

function emitRuntimeAuthChange(): void {
  runtimeAuthVersion += 1;
  for (const listener of runtimeAuthListeners) {
    listener();
  }
}

export function setRuntimeApiKey(value: string | null | undefined): void {
  runtimeApiKey = normalizeApiKey(value);
  runtimeApiKeyResolved = true;
  emitRuntimeAuthChange();
}

export function getRuntimeApiKey(): string | null {
  return runtimeApiKey;
}

export function hasRuntimeApiKey(): boolean {
  return !!runtimeApiKey;
}

export function hasResolvedRuntimeApiKey(): boolean {
  return runtimeApiKeyResolved;
}

export function clearRuntimeApiKey(): void {
  runtimeApiKey = null;
  runtimeApiKeyResolved = true;
  emitRuntimeAuthChange();
}

export function __setRuntimeApiKeyForTests(value: string | null): void {
  runtimeApiKey = normalizeApiKey(value);
  runtimeApiKeyResolved = true;
  emitRuntimeAuthChange();
}

export function __resetRuntimeApiKeyForTests(): void {
  runtimeApiKey = null;
  runtimeApiKeyResolved = false;
  emitRuntimeAuthChange();
}

export function getRuntimeAuthVersion(): number {
  return runtimeAuthVersion;
}

export function subscribeRuntimeAuthState(listener: () => void): () => void {
  runtimeAuthListeners.add(listener);
  return () => {
    runtimeAuthListeners.delete(listener);
  };
}
