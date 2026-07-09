import { useEffect, useRef, useState, useCallback } from "react";
import { WsClient } from "@/lib/wsClient";

// ─── Types ───────────────────────────────────────────────────────────────────

export type PresenceUser = {
  user_id: string;
  color: string;
};

export type UseDocumentCollaborationOptions = {
  /** Document ID for the collaboration session. */
  documentId: string;
  /** Current user identifier. */
  userId: string;
  /** Optional authentication token. */
  authToken?: string;
  /** Whether the current user has edit permission. When false, sendContentUpdate is a no-op. */
  canEdit?: boolean;
  /** Called when a remote content update arrives. */
  onRemoteContentUpdate: (content: string) => void;
  /** Optional callback invoked when the connection opens (e.g. to refresh the audit trail). */
  onAuditRefresh?: () => void;
};

export type UseDocumentCollaborationResult = {
  /** Whether the WebSocket is currently connected. */
  isConnected: boolean;
  /** Whether the session was closed due to access denial (close code 1008). */
  accessDenied: boolean;
  /** Users currently present in the document session. */
  activeUsers: PresenceUser[];
  /** Send a local content update to all other clients in the session. */
  sendContentUpdate: (content: string) => void;
};

// ─── Colour palette ──────────────────────────────────────────────────────────

const USER_COLORS = [
  "#FF6B6B",
  "#4ECDC4",
  "#45B7D1",
  "#FFA07A",
  "#98D8C8",
];

// ─── URL construction ────────────────────────────────────────────────────────

function buildCollabWsUrl(documentId: string, authToken?: string): string {
  const env = (import.meta as any).env;
  const apiBase: string =
    env?.VITE_GUARDIAN_API_BASE ??
    (typeof window !== "undefined" ? window.location.origin : "") ??
    "http://localhost:8000";

  const wsProtocol = apiBase.startsWith("https") ? "wss" : "ws";
  let url = `${wsProtocol}://${apiBase.replace(/^https?:\/\//, "")}/api/collab/ws/${documentId}`;

  if (authToken) {
    url += `?token=${encodeURIComponent(authToken)}`;
  }

  return url;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useDocumentCollaboration({
  documentId,
  userId,
  authToken,
  canEdit = true,
  onRemoteContentUpdate,
  onAuditRefresh,
}: UseDocumentCollaborationOptions): UseDocumentCollaborationResult {
  const [isConnected, setIsConnected] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [activeUsers, setActiveUsers] = useState<PresenceUser[]>([]);

  const clientRef = useRef<WsClient | null>(null);
  const userColorMapRef = useRef<Map<string, string>>(new Map());

  // Assign stable colours to user IDs
  const assignColor = useCallback((uid: string): string => {
    const map = userColorMapRef.current;
    if (!map.has(uid)) {
      const colorIndex = map.size % USER_COLORS.length;
      map.set(uid, USER_COLORS[colorIndex]);
    }
    return map.get(uid)!;
  }, []);

  // Build active-user list from a string array
  const rebuildPresence = useCallback(
    (ids: string[]) => {
      const users: PresenceUser[] = ids.map((id) => ({
        user_id: id,
        color: assignColor(id),
      }));
      setActiveUsers(users);
    },
    [assignColor],
  );

  // Connect / reconnect when dependencies change
  useEffect(() => {
    const wsUrl = buildCollabWsUrl(documentId, authToken);

    const client = new WsClient(wsUrl, {
      onUnauthorized: () => {
        setAccessDenied(true);
      },
    });
    clientRef.current = client;

    client.onStatusChange = (status) => {
      setIsConnected(status === "connected");
    };

    client.onConnectionChange = (connected) => {
      if (connected) {
        console.log(`Connected to collaborative session for document ${documentId}`);
        setAccessDenied(false);

        // Handshake
        client.send({
          user_id: userId,
          token: authToken,
        });

        onAuditRefresh?.();
      } else {
        console.log("Disconnected from collaborative session");
      }
    };

    client.on("message", (data: any) => {
      if (data?.type === "update") {
        const payload = data.payload ?? data;
        if (payload?.content !== undefined) {
          onRemoteContentUpdate(payload.content);
        }
      } else if (data?.type === "presence.join" && Array.isArray(data?.active_users)) {
        rebuildPresence(data.active_users);
      } else if (data?.type === "presence.leave" && Array.isArray(data?.active_users)) {
        rebuildPresence(data.active_users);
      }
    });

    client.on("error", (data: any) => {
      console.error("WebSocket error:", data?.message ?? data);
    });

    client.connect();

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [documentId, userId, authToken, onRemoteContentUpdate, onAuditRefresh, rebuildPresence]);

  // Public API
  const sendContentUpdate = useCallback(
    (content: string) => {
      const client = clientRef.current;
      if (!client?.isConnected || !canEdit) return;

      client.send({
        type: "update",
        content,
        user_id: userId,
        timestamp: new Date().toISOString(),
      });
    },
    [canEdit, userId],
  );

  return {
    isConnected,
    accessDenied,
    activeUsers,
    sendContentUpdate,
  };
}
