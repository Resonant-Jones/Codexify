function normalizeApiKey(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

let runtimeApiKey: string | null = null;
let runtimeApiKeyResolved = false;

export function setRuntimeApiKey(value: string | null | undefined): void {
  runtimeApiKey = normalizeApiKey(value);
  runtimeApiKeyResolved = true;
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
}

export function __setRuntimeApiKeyForTests(value: string | null): void {
  runtimeApiKey = normalizeApiKey(value);
  runtimeApiKeyResolved = true;
}

export function __resetRuntimeApiKeyForTests(): void {
  runtimeApiKey = null;
  runtimeApiKeyResolved = false;
}
