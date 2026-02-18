// Local persistence for selected provider/model routing.
const PROVIDER_KEY = "guardian.provider.v1";
const PROVIDER_MODEL_KEY = "guardian.provider_model.v1";

export type ProviderName = string | null;
export type ProviderModelSelection = {
  provider: ProviderName;
  model: string | null;
};

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function emitProviderChanged(): void {
  try {
    window.dispatchEvent(new CustomEvent("guardian:providerChanged"));
  } catch {}
}

export function getPreferredProvider(): ProviderName {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PROVIDER_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    const provider = normalizeString(parsed);
    if (provider) return provider;
    return getPreferredProviderSelection()?.provider ?? null;
  } catch {
    return null;
  }
}

export function setPreferredProvider(p: ProviderName): void {
  if (typeof window === "undefined") return;
  try {
    const normalizedProvider = normalizeString(p);
    if (normalizedProvider === null) {
      localStorage.removeItem(PROVIDER_KEY);
      localStorage.removeItem(PROVIDER_MODEL_KEY);
      emitProviderChanged();
      return;
    }

    localStorage.setItem(PROVIDER_KEY, JSON.stringify(normalizedProvider));
    const current = getPreferredProviderSelection();
    const nextSelection: ProviderModelSelection = {
      provider: normalizedProvider,
      model: current?.provider === normalizedProvider ? current.model : null,
    };
    localStorage.setItem(PROVIDER_MODEL_KEY, JSON.stringify(nextSelection));
    emitProviderChanged();
  } catch {
    /* ignore */
  }
}

export function getPreferredProviderSelection(): ProviderModelSelection | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PROVIDER_MODEL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const provider = normalizeString((parsed as { provider?: unknown }).provider);
    const model = normalizeString((parsed as { model?: unknown }).model);
    if (!provider && !model) return null;
    return {
      provider: provider ?? null,
      model: model ?? null,
    };
  } catch {
    return null;
  }
}

export function setPreferredProviderSelection(
  selection: ProviderModelSelection | null
): void {
  if (typeof window === "undefined") return;
  try {
    if (!selection) {
      localStorage.removeItem(PROVIDER_KEY);
      localStorage.removeItem(PROVIDER_MODEL_KEY);
      emitProviderChanged();
      return;
    }

    const provider = normalizeString(selection.provider);
    const model = normalizeString(selection.model);
    if (!provider && !model) {
      localStorage.removeItem(PROVIDER_KEY);
      localStorage.removeItem(PROVIDER_MODEL_KEY);
      emitProviderChanged();
      return;
    }

    if (provider) {
      localStorage.setItem(PROVIDER_KEY, JSON.stringify(provider));
    } else {
      localStorage.removeItem(PROVIDER_KEY);
    }
    localStorage.setItem(
      PROVIDER_MODEL_KEY,
      JSON.stringify({
        provider: provider ?? null,
        model: model ?? null,
      })
    );
    emitProviderChanged();
  } catch {
    /* ignore */
  }
}
