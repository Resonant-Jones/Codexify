import { useState, useCallback, useEffect, useRef } from "react";
import api from "@/lib/api";
import { useDocumentCollaboration } from "./useDocumentCollaboration";
import type { PresenceUser } from "./useDocumentCollaboration";

type AuditLogEntry = {
  id: number;
  user_id: string | null;
  action: string;
  payload: Record<string, any> | null;
  timestamp: string;
};

type UserPermissions = {
  can_edit: boolean;
  can_comment: boolean;
};

export type CollaborativeNoteProps = {
  documentId: string;
  threadId: number;
  userId?: string;
  initialContent?: string;
  onContentChange?: (content: string) => void;
  authToken?: string;
};

export function CollaborativeNote({
  documentId,
  threadId,
  userId = "anonymous",
  initialContent = "",
  onContentChange,
  authToken,
}: CollaborativeNoteProps) {
  const [content, setContent] = useState(initialContent);
  const [lastAutosave, setLastAutosave] = useState<Date | null>(null);
  const [autosaveError, setAutosaveError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [auditHistory, setAuditHistory] = useState<AuditLogEntry[]>([]);
  const [showAuditTrail, setShowAuditTrail] = useState(false);

  const autosaveTimer = useRef<NodeJS.Timeout>();
  const stopTypingTimer = useRef<NodeJS.Timeout>();

  // ── Audit trail ──────────────────────────────────────────────────────────

  const fetchAuditTrail = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/collab/${documentId}/audit?limit=100`,
        {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        }
      );
      if (response.ok) {
        const data = await response.json();
        setAuditHistory(data.entries);
      }
    } catch (error) {
      console.error("Failed to fetch audit trail:", error);
    }
  }, [documentId, authToken]);

  // ── Remote content handler ───────────────────────────────────────────────

  const handleRemoteContentUpdate = useCallback(
    (remoteContent: string) => {
      if (remoteContent === content) return;
      setContent(remoteContent);
      onContentChange?.(remoteContent);
    },
    [content, onContentChange],
  );

  // ── Collaboration hook ───────────────────────────────────────────────────

  const {
    isConnected,
    accessDenied,
    activeUsers,
    typingUsers,
    sendContentUpdate,
    notifyTyping,
    stopTyping,
  } = useDocumentCollaboration({
    documentId,
    userId,
    authToken,
    canEdit: permissions?.can_edit !== false,
    onRemoteContentUpdate: handleRemoteContentUpdate,
    onAuditRefresh: fetchAuditTrail,
  });

  // ── Autosave ─────────────────────────────────────────────────────────────

  useEffect(() => {
    autosaveTimer.current = setInterval(async () => {
      try {
        await api.post(
          "/documents/autosave",
          {
            thread_id: threadId,
            content,
          },
          authToken
            ? {
                headers: {
                  Authorization: `Bearer ${authToken}`,
                },
              }
            : undefined
        );
        setLastAutosave(new Date());
        setAutosaveError(null);
      } catch (error) {
        console.error("Autosave failed:", error);
        const status = (
          error as { response?: { status?: number } } | undefined
        )?.response?.status;
        setAutosaveError(
          status ? `Autosave failed (${status})` : "Autosave failed"
        );
      }
    }, 15_000);

    return () => {
      if (autosaveTimer.current) {
        clearInterval(autosaveTimer.current);
      }
      if (stopTypingTimer.current) {
        clearTimeout(stopTypingTimer.current);
        stopTyping();
      }
    };
  }, [content, threadId, authToken]);

  // ── Local changes ────────────────────────────────────────────────────────

  const handleChange = (value: string) => {
    setContent(value);
    sendContentUpdate(value);
    onContentChange?.(value);

    // Typing indicator
    notifyTyping();
    if (stopTypingTimer.current) clearTimeout(stopTypingTimer.current);
    stopTypingTimer.current = setTimeout(() => {
      stopTyping();
    }, 1_200);
  };

  // ── Access denied ────────────────────────────────────────────────────────

  if (accessDenied) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
          backgroundColor: "var(--panel-bg)",
          borderRadius: 8,
          padding: "32px",
          textAlign: "center",
          color: "var(--text)",
        }}
      >
        <div
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: "var(--danger-text)",
            marginBottom: "12px",
          }}
        >
          Access Denied
        </div>
        <div style={{ fontSize: 14, color: "var(--muted)" }}>
          You do not have permission to access this document.
        </div>
      </div>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "var(--panel-bg)",
        borderRadius: 8,
        overflow: "hidden",
        color: "var(--text)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--panel-border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Connection status */}
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: isConnected ? "#10b981" : "#ef4444",
            }}
            title={isConnected ? "Connected" : "Disconnected"}
          />
          <span style={{ fontSize: 13, fontWeight: 600 }}>
            {isConnected ? "Live Editing" : "Offline"}
          </span>

          {/* Typing indicator */}
          {typingUsers.length > 0 && (
            <span
              style={{
                fontSize: 11,
                color: "var(--text-subtle)",
                fontStyle: "italic",
              }}
            >
              {typingUsers.length === 1
                ? `${typingUsers[0].user_id} is typing…`
                : `${typingUsers.length} collaborators are typing…`}
            </span>
          )}

          {/* Permission lock indicator */}
          {!permissions?.can_edit && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "4px 8px",
                backgroundColor: "var(--tag-surface)",
                borderRadius: 4,
                color: "var(--text)",
              }}
              title="Read-only mode"
            >
              <span style={{ fontSize: 12 }}>🔒</span>
              <span style={{ fontSize: 11, fontWeight: 500 }}>Read-only</span>
            </div>
          )}
        </div>

        {/* Presence indicators */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {activeUsers.length > 0 && (
            <div style={{ display: "flex", gap: 4 }}>
              {activeUsers.map((user: PresenceUser) => (
                <div
                  key={user.user_id}
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    backgroundColor: user.color,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 11,
                    fontWeight: 600,
                    title: user.user_id,
                    cursor: "default",
                  }}
                >
                  {user.user_id.charAt(0).toUpperCase()}
                </div>
              ))}
            </div>
          )}

          {/* Last autosave indicator */}
          {lastAutosave && (
            <span
              style={{
                fontSize: 11,
                color: "var(--text-subtle)",
                whiteSpace: "nowrap",
              }}
            >
              Saved{" "}
              {Math.round((Date.now() - lastAutosave.getTime()) / 1000)}s ago
            </span>
          )}
          {autosaveError && (
            <span
              style={{
                fontSize: 11,
                color: "#ef4444",
                whiteSpace: "nowrap",
              }}
            >
              {autosaveError}
            </span>
          )}

          {/* View History button */}
          <button
            onClick={() => setShowAuditTrail(!showAuditTrail)}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              fontWeight: 500,
              backgroundColor: showAuditTrail
                ? "var(--info-surface)"
                : "var(--surface-soft)",
              border: "1px solid var(--panel-border)",
              borderRadius: 4,
              cursor: "pointer",
              color: showAuditTrail ? "var(--info-text)" : "var(--muted)",
            }}
          >
            View History
          </button>
        </div>
      </div>

      {/* Audit trail panel */}
      {showAuditTrail && (
        <div
          style={{
            maxHeight: "200px",
            overflowY: "auto",
            borderBottom: "1px solid var(--panel-border)",
            backgroundColor: "var(--surface-soft)",
            padding: "12px 16px",
            fontSize: 12,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: "8px" }}>
            Activity ({auditHistory.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {auditHistory.length === 0 ? (
              <div style={{ color: "var(--text-subtle)" }}>No activity yet</div>
            ) : (
              auditHistory.map((entry: AuditLogEntry) => (
                <div
                  key={entry.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    color: "var(--muted)",
                    paddingBottom: "6px",
                    borderBottom: "1px solid var(--panel-border)",
                  }}
                >
                  <span>
                    <strong>{entry.user_id || "system"}</strong> {entry.action}
                  </span>
                  <span style={{ color: "var(--text-subtle)" }}>
                    {entry.timestamp
                      ? new Date(entry.timestamp).toLocaleTimeString()
                      : ""}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Editor area */}
      <textarea
        value={content}
        onChange={(e: any) => handleChange(e.target.value)}
        disabled={permissions?.can_edit === false}
        placeholder={
          permissions?.can_edit === false
            ? "Read-only mode - you do not have edit permissions"
            : "Start typing... (auto-saves every 15s)"
        }
        style={{
          flex: 1,
          padding: "16px",
          border: "none",
          fontFamily: "monospace",
          fontSize: 14,
          lineHeight: 1.6,
          resize: "none",
          outline: "none",
          color:
            permissions?.can_edit === false
              ? "var(--text-subtle)"
              : "var(--text)",
          backgroundColor:
            permissions?.can_edit === false
              ? "var(--surface-soft)"
              : "var(--panel-bg)",
          cursor: permissions?.can_edit === false ? "not-allowed" : "text",
        }}
      />
    </div>
  );
}
