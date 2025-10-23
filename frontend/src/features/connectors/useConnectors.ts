

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useLiveEvents } from "@/hooks/useLiveEvents";

export interface ConnectorAuth {
  type: "oauth" | "api_key" | "local";
  token?: string;
  path?: string;
}

export interface ConnectorOption {
  key: string;
  label: string;
  type: "boolean" | "string" | "number" | "select";
  value: any;
  options?: string[];
}

export interface ConnectorCapabilities {
  supportsOAuth: boolean;
  supportsApiKey: boolean;
  supportsLocal: boolean;
}

export interface RequiredField {
  key: string;
  label: string;
  type: "string" | "password";
  secret?: boolean;
}

export interface Connector {
  id: string;
  name: string;
  type?: string;
  status: "connected" | "disconnected";
  auth: ConnectorAuth | null;
  syncInterval: string;
  scopes: string[];
  options: ConnectorOption[];
  capabilities?: ConnectorCapabilities;
  requiredFields?: RequiredField[];
  needsAdminSecret?: boolean;
  lastSyncAt?: string | null;
  errorMessage?: string | null;
}

export function useConnectors() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { subscribe } = useLiveEvents();

  const fetchConnectors = useCallback(async () => {
    try {
      setLoading(true);
      // Prefer /api/connectors if backend is namespaced; fall back to /connectors
      let res: any;
      try {
        res = await api.get<Connector[]>("/api/connectors");
      } catch (e: any) {
        // Gracefully handle 404 or mismatch by falling back
        res = await api.get<Connector[]>("/connectors");
      }
      if ((import.meta as any)?.env?.DEV) {
        // eslint-disable-next-line no-console
        console.log("Connectors response:", res.data);
      }
      if (Array.isArray(res.data)) {
        setConnectors(res.data);
      } else {
        // eslint-disable-next-line no-console
        console.warn("Unexpected connectors response", res.data);
        setConnectors([]);
      }
      setError(null);
    } catch (err: any) {
      // Swallow 404 as "no connectors yet" instead of erroring the UI
      const status = err?.response?.status;
      if (status === 404) {
        setConnectors([]);
        setError(null);
      } else {
        console.error("Failed to fetch connectors", err);
        setError("Failed to fetch connectors");
        setConnectors([]);
      }
      } finally {
        setLoading(false);
      }
  }, []);

  async function updateConnector(id: string, data: Partial<Connector>) {
    try {
      const res = await api.patch(`/api/connectors/${id}`, data);
      if (!res?.data) return;
      if (res.data && res.data.id) {
        // server returned a single connector object
        setConnectors((prev) => prev.map((c) => (c.id === res.data.id ? res.data : c)));
      } else if (res.data && res.data.connector) {
        // legacy shape; keep for resilience
        setConnectors((prev) => prev.map((c) => (c.id === res.data.connector.id ? res.data.connector : c)));
      } else {
        // eslint-disable-next-line no-console
        console.warn("Unexpected updateConnector response", res.data);
      }
    } catch (err) {
      console.error("Failed to update connector", err);
    }
  }

  async function authorizeOAuth(id: string) {
    try {
      const redirectUri = window.location.origin + "/auth/callback"; // UI can handle close
      const res = await api.post(`/connectors/${id}/authorize`, { redirectUri });
      if (res?.data?.authUrl) {
        const w = window.open(res.data.authUrl, "oauth", "width=600,height=700");
        // Poll connector status for up to 60s
        const started = Date.now();
        const poll = async () => {
          try {
            const s = await api.get<Connector>(`/api/connectors/${id}`);
            if (s.data?.status === "connected") {
              await fetchConnectors();
              try { w && w.close(); } catch {}
              return;
            }
          } catch {}
          if (Date.now() - started < 60000) setTimeout(poll, 1500);
        };
        setTimeout(poll, 1500);
      }
    } catch (err) {
      console.error("OAuth authorize failed", err);
    }
  }

  async function testConnector(id: string) {
    try {
      const res = await api.post(`/api/connectors/${id}/test`);
      return res.data;
    } catch (err) {
      console.error("Test connector failed", err);
      return { ok: false };
    }
  }

  async function syncConnector(id: string) {
    try {
      const res = await api.post(`/connectors/${id}/sync`);
      return res.data;
    } catch (err) {
      console.error("Sync connector failed", err);
      return null;
    }
  }

  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  useEffect(() => {
    return subscribe("connector.sync", () => {
      fetchConnectors();
    });
  }, [fetchConnectors, subscribe]);

  return {
    connectors,
    loading,
    error,
    refresh: fetchConnectors,
    updateConnector,
    authorizeOAuth,
    testConnector,
    syncConnector,
  };
}
