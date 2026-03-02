function normalizeApiKey(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

let runtimeApiKey: string | null = null;

export function setRuntimeApiKey(value: string | null | undefined): void {
  runtimeApiKey = normalizeApiKey(value);
}

export function getRuntimeApiKey(): string | null {
  return runtimeApiKey;
}

export function hasRuntimeApiKey(): boolean {
  return !!runtimeApiKey;
}

export function clearRuntimeApiKey(): void {
  runtimeApiKey = null;
}

export function __setRuntimeApiKeyForTests(value: string | null): void {
  runtimeApiKey = normalizeApiKey(value);
}
