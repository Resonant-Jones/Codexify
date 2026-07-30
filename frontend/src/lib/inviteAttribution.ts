import { resolveApiUrl } from "./runtimeConfig";

const INVITE_FRAGMENT_PREFIX = "#invite=";
const INVITE_RESOLUTION_PATH = "/api/account-observability/invites/resolve";

type InviteWindow = Pick<Window, "location" | "history">;

export function extractInviteTokenFromHash(hash: string): string | null {
  if (!hash.startsWith(INVITE_FRAGMENT_PREFIX)) return null;
  const encoded = hash.slice(INVITE_FRAGMENT_PREFIX.length);
  if (!encoded || encoded.includes("&") || encoded.includes("#")) return null;
  try {
    const token = decodeURIComponent(encoded);
    return token || null;
  } catch {
    return null;
  }
}

function removeInviteFragment(windowRef: InviteWindow): void {
  windowRef.history.replaceState(
    windowRef.history.state,
    "",
    `${windowRef.location.pathname}${windowRef.location.search}`
  );
}

export function createInviteAttributionResolver(
  windowRef?: InviteWindow | null,
  fetchImpl?: typeof fetch
): () => Promise<void> {
  let attempted = false;

  return async (): Promise<void> => {
    if (attempted) return;
    attempted = true;

    const targetWindow =
      windowRef ??
      (typeof window !== "undefined" ? (window as InviteWindow) : null);
    const requestFetch =
      fetchImpl ?? (typeof fetch !== "undefined" ? fetch : null);
    if (!targetWindow || !requestFetch) return;

    const hash = targetWindow.location.hash;
    if (!hash.startsWith(INVITE_FRAGMENT_PREFIX)) return;

    // Clear the browser-visible fragment before decoding or making a request.
    removeInviteFragment(targetWindow);
    const token = extractInviteTokenFromHash(hash);
    if (!token) return;

    try {
      await requestFetch(resolveApiUrl(INVITE_RESOLUTION_PATH), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
        credentials: "include",
      });
    } catch {
      // Attribution is observational and must never block application startup.
    }
  };
}

export const resolveInviteAttribution = createInviteAttributionResolver();
