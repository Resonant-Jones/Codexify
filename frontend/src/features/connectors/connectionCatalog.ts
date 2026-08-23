/**
 * Canonical frontend projection of the Connections catalog API.
 *
 * This module carries the *types and presentation helpers* for the
 * backend-owned catalog. It never invents connection entries: every row in
 * the bay is projected from `GET /api/connections`.
 */

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export type ConnectionCategory =
  | "messaging"
  | "web"
  | "inference"
  | "knowledge";

export type ImplementationState =
  | "implemented"
  | "partial"
  | "unimplemented"
  | "experimental";

export type SetupState =
  | "available"
  | "needs_setup"
  | "authenticating"
  | "configured"
  | "connected"
  | "degraded"
  | "error"
  | "unavailable";

export type AuthMethod =
  | "oauth_browser"
  | "oauth_device"
  | "api_key"
  | "token"
  | "service_credentials"
  | "local_endpoint"
  | "none";

export interface ConnectionFieldSpec {
  key: string;
  label: string;
  type: string;
  secret?: boolean;
}

export interface ConnectionRuntimeBinding {
  subsystem: string | null;
  adapter: string | null;
  setup_route: string | null;
  registry_provider_id: string | null;
  oauth_backend_handler_exists: boolean;
}

export interface ConnectionOAuthRow {
  provider: string;
  mode: string;
  status: string;
  scopes: string[];
  expires_at: string | null;
  last_refresh_at: string | null;
  error_kind: string | null;
}

export interface ConnectionOAuthProjection {
  supported: boolean;
  backend_handler_exists: boolean;
  connection: ConnectionOAuthRow | null;
  launchable?: boolean;
  node_configured?: boolean;
}

export interface ConnectionAuthorization {
  registered: boolean;
  registry_provider_id?: string | null;
  governance_classification?: string;
  authorized?: boolean;
  available?: boolean;
  enabled?: boolean;
  disabled_reason?: string | null;
  note?: string;
}

/** Safe provider validation state. It intentionally contains no credential or
 * raw upstream error payload. */
export interface ConnectionValidation {
  configured: boolean;
  state: string;
  last_validated_at: string | null;
}

export interface ConnectionEntry {
  id: string;
  display_name: string;
  category: ConnectionCategory;
  description: string;
  auth_methods: AuthMethod[];
  capabilities: string[];
  implementation_state: ImplementationState;
  setup_state: SetupState;
  runtime_binding: ConnectionRuntimeBinding;
  required_fields: ConnectionFieldSpec[];
  scopes: string[];
  setup_help: string;
  oauth: ConnectionOAuthProjection | null;
  validation?: ConnectionValidation | null;
  authorization: ConnectionAuthorization | null;
}

export interface ConnectionsResponse {
  categories: ConnectionCategory[];
  items: ConnectionEntry[];
}

export const CATEGORY_LABELS: Record<ConnectionCategory, string> = {
  messaging: "Messaging",
  web: "Web",
  inference: "Inference",
  knowledge: "Knowledge",
};

export const IMPLEMENTATION_STATE_LABELS: Record<ImplementationState, string> = {
  implemented: "Implemented",
  partial: "Partial",
  unimplemented: "Not implemented",
  experimental: "Experimental",
};

export const SETUP_STATE_LABELS: Record<SetupState, string> = {
  available: "Available",
  needs_setup: "Needs setup",
  authenticating: "Authenticating",
  configured: "Configured",
  connected: "Connected",
  degraded: "Degraded",
  error: "Error",
  unavailable: "Not available",
};

export const AUTH_METHOD_LABELS: Record<AuthMethod, string> = {
  oauth_browser: "OAuth (browser)",
  oauth_device: "OAuth (device)",
  api_key: "API key",
  token: "Token",
  service_credentials: "Service credentials",
  local_endpoint: "Local endpoint",
  none: "No authentication",
};

export function isConnectionEntry(value: unknown): value is ConnectionEntry {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.display_name === "string" &&
    typeof candidate.implementation_state === "string" &&
    typeof candidate.setup_state === "string"
  );
}

/** A setup action may launch only when a real backing route exists. */
export function canLaunchSetup(entry: ConnectionEntry): boolean {
  if (entry.implementation_state === "unimplemented") return false;
  return Boolean(entry.runtime_binding.setup_route);
}

/** OAuth may launch only when a real backend authorization handler exists AND
 *  the entry's setup can actually be launched on the current node (e.g.
 *  the operator has provided the necessary application configuration).
 */
export function canLaunchOAuth(entry: ConnectionEntry): boolean {
  if (!entry.oauth?.backend_handler_exists) return false;
  if (entry.oauth.launchable === false) return false;
  return true;
}

export function matchesSearch(entry: ConnectionEntry, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [
    entry.id,
    entry.display_name,
    entry.description,
    ...entry.capabilities,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(needle);
}

type UseConnectionsOptions = {
  enabled?: boolean;
};

export function useConnections(options: UseConnectionsOptions = {}) {
  const enabled = options.enabled ?? true;
  const [connections, setConnections] = useState<ConnectionEntry[]>([]);
  const [categories, setCategories] = useState<ConnectionCategory[]>([]);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  const fetchConnections = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      setError(null);
      setConnections([]);
      setCategories([]);
      return;
    }
    try {
      setLoading(true);
      const res = await api.get<ConnectionsResponse>("/api/connections");
      const payload: unknown = res?.data;
      if (
        payload &&
        typeof payload === "object" &&
        Array.isArray((payload as ConnectionsResponse).items)
      ) {
        const items = (payload as ConnectionsResponse).items.filter(
          isConnectionEntry
        );
        const listed = (payload as ConnectionsResponse).categories ?? [];
        setConnections(items);
        setCategories(
          listed.filter(
            (c): c is ConnectionCategory =>
              c === "messaging" ||
              c === "web" ||
              c === "inference" ||
              c === "knowledge"
          )
        );
      } else {
        setConnections([]);
        setCategories([]);
      }
      setError(null);
    } catch (err: unknown) {
      // The catalog is a projection seam; a missing route must degrade to an
      // empty bay, never an invented list.
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 404) {
        setConnections([]);
        setCategories([]);
        setError(null);
      } else {
        setError("Failed to fetch connections");
        setConnections([]);
        setCategories([]);
      }
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void fetchConnections();
  }, [fetchConnections]);

  return {
    connections,
    categories,
    loading,
    error,
    refresh: fetchConnections,
  };
}
