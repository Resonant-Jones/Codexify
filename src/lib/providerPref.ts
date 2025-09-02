// Local persistence for the selected provider.
const KEY = "guardian.provider.v1";

export type ProviderName = string | null;

export function getPreferredProvider(): ProviderName {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return typeof parsed === "string" ? parsed : null;
  } catch {
    return null;
  }
}

export function setPreferredProvider(p: ProviderName): void {
  if (typeof window === "undefined") return;
  try {
    if (p === null) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, JSON.stringify(p));
    // Broadcast same-tab updates for instant sync across components
    try { window.dispatchEvent(new CustomEvent("guardian:providerChanged")); } catch {}
  } catch {
    /* ignore */
  }
}
