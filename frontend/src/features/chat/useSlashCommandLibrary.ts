import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import type { SlashCommandManifest } from "@/contracts/slashCommands";
import { fetchSlashCommandManifest } from "@/lib/api";
import type { AuthState } from "@/lib/authState";
import { getRuntimeAuthVersion, subscribeRuntimeAuthState } from "@/lib/runtimeAuth";
import {
  getRuntimeConfigHydrationState,
  getRuntimeConfigVersion,
  resolveApiUrl,
  subscribeRuntimeConfigState,
} from "@/lib/runtimeConfig";

export type SlashCommandLibrary =
  | { status: "loading" | "unavailable"; manifest?: undefined }
  | { status: "ready"; manifest: SlashCommandManifest };

export function useSlashCommandLibrary(
  auth: AuthState,
  backendReachable?: boolean | null
): SlashCommandLibrary {
  const runtimeVersion = useSyncExternalStore(
    subscribeRuntimeConfigState, getRuntimeConfigVersion, getRuntimeConfigVersion
  );
  const credentialVersion = useSyncExternalStore(
    subscribeRuntimeAuthState, getRuntimeAuthVersion, getRuntimeAuthVersion
  );
  const endpoint = resolveApiUrl("/api/chat/slash-commands/manifest");
  const enabled =
    auth.ready && auth.status === "authenticated" &&
    backendReachable !== false && getRuntimeConfigHydrationState() === "ready";
  const scope = useMemo(
    () => ({ enabled, endpoint, runtimeVersion, credentialVersion, token: auth.token }),
    [enabled, endpoint, runtimeVersion, credentialVersion, auth.token]
  );
  const [result, setResult] = useState<{
    scope: typeof scope;
    library: SlashCommandLibrary;
  }>();

  useEffect(() => {
    if (!scope.enabled) return;
    const request = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => {
      request.abort();
      if (active) setResult({ scope, library: { status: "unavailable" } });
    }, 15_000);
    void fetchSlashCommandManifest(request.signal).then(
      (manifest) => {
        if (active && !request.signal.aborted) {
          setResult({ scope, library: { status: "ready", manifest } });
        }
      },
      () => {
        if (active) setResult({ scope, library: { status: "unavailable" } });
      }
    ).finally(() => window.clearTimeout(timeout));
    return () => {
      active = false;
      window.clearTimeout(timeout);
      request.abort();
    };
  }, [scope]);

  if (!enabled) return { status: "unavailable" };
  // A new credential or endpoint must hide the old snapshot during render,
  // before the previous request's effect cleanup has a chance to run.
  return result?.scope === scope ? result.library : { status: "loading" };
}
