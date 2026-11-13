import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuthState } from "@/lib/authState";

export const FEED_CARDS = [
  { id: "threads", label: "Recent Threads" },
  { id: "documents", label: "Recent Documents" },
  { id: "gallery", label: "Gallery" },
] as const;
export type FeedCardId = (typeof FEED_CARDS)[number]["id"];
export type FeedPreferences = { version: 1; order: FeedCardId[]; hidden: FeedCardId[] };
const ids = FEED_CARDS.map((card) => card.id);
const isCardId = (value: unknown): value is FeedCardId => ids.includes(value as FeedCardId);

export function normalizeFeedPreferences(value?: unknown): FeedPreferences {
  const saved = value as Partial<FeedPreferences> | null;
  const valid = saved?.version === 1;
  const order = valid && Array.isArray(saved.order) ? saved.order.filter(isCardId) : [];
  const hidden = valid && Array.isArray(saved.hidden) ? saved.hidden.filter(isCardId) : [];
  return { version: 1, order: [...new Set([...order, ...ids])], hidden: [...new Set(hidden)] };
}

export function feedStorageKey(accountId: string): string {
  return `cfy.feed.v1:${encodeURIComponent(accountId)}`;
}

function readPreferences(accountId: string | null): FeedPreferences {
  try {
    return normalizeFeedPreferences(accountId ? JSON.parse(localStorage.getItem(feedStorageKey(accountId)) ?? "null") : null);
  } catch {
    return normalizeFeedPreferences();
  }
}

function savePreferences(accountId: string, value: FeedPreferences): boolean {
  try {
    localStorage.setItem(feedStorageKey(accountId), JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

/** Local presentation preferences only; the backend remains authoritative for card data. */
export function useFeedPreferences() {
  const auth = useAuthState();
  // Never persist credentials. This scope only prevents an old request/state crossing a login change.
  const session = auth.status === "authenticated" ? auth.token ?? "local" : auth.status;
  const [owner, setOwner] = useState<{ session: typeof session; id: string | null }>({ session, id: null });
  const accountId = owner.session === session ? owner.id : null;
  const scope = accountId ? feedStorageKey(accountId) : session;
  const [state, setState] = useState(() => ({
    scope,
    session,
    value: readPreferences(accountId),
    saved: true,
    pending: false,
  }));
  if (state.scope !== scope || state.session !== session) {
    // A completed lookup must not overwrite this session's explicit edits.
    // An actual login change always starts from the new account's preferences.
    const preserveEdits = state.session === session && state.scope === session && state.pending;
    setState({
      scope,
      session,
      value: preserveEdits ? state.value : readPreferences(accountId),
      saved: !preserveEdits,
      pending: preserveEdits,
    });
  }

  useEffect(() => {
    if (auth.status !== "authenticated") return;
    let cancelled = false;
    // Match the existing sidebar's account ownership source; never infer identity from a display name.
    void api.get("/api/projects").then((response) => {
      const payload = response?.data;
      const projects = Array.isArray(payload) ? payload : payload?.projects;
      const owners = Array.isArray(projects)
        ? projects.map((project) => typeof project?.user_id === "string" ? project.user_id.trim() : "")
        : [];
      const id = owners.length && owners.every((candidate) => candidate && candidate === owners[0]) ? owners[0] : null;
      if (!cancelled) setOwner({ session, id });
    }).catch(() => {
      // Keep controls usable for this visit when account ownership cannot be resolved.
    });
    return () => { cancelled = true; };
  }, [session, auth.status]);

  useEffect(() => {
    if (!accountId || state.scope !== scope || state.session !== session || !state.pending) return;
    const saved = savePreferences(accountId, state.value);
    setState((current) => current === state ? { ...current, saved, pending: false } : current);
  }, [accountId, scope, session, state]);

  function update(value: FeedPreferences) {
    const saved = accountId ? savePreferences(accountId, value) : false;
    setState({ scope, session, value, saved, pending: !accountId });
  }

  return {
    preferences: state.scope === scope && state.session === session ? state.value : readPreferences(accountId),
    update,
    persistent: !!accountId && state.saved,
  };
}
