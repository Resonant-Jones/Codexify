import { useEffect, useRef, useState, useCallback } from "react";

type PresenceUser = {
  user_id: string;
  color: string;
};

const USER_COLORS = [
  "#FF6B6B", // Red
  "#4ECDC4", // Teal
  "#45B7D1", // Blue
  "#FFA07A", // Light Salmon
  "#98D8C8", // Mint
];

export type CollaborativeNoteProps = {
  documentId: string;
  threadId: number;
  userId?: string;
  initialContent?: string;
  onContentChange?: (content: string) => void;
};

export function CollaborativeNote({
  documentId,
  threadId,
  userId = "anonymous",
  initialContent = "",
  onContentChange,
}: CollaborativeNoteProps) {
  const [content, setContent] = useState(initialContent);
  const [activeUsers, setActiveUsers] = useState<PresenceUser[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastAutosave, setLastAutosave] = useState<Date | null>(null);
  const ws = useRef<WebSocket>();
  const autosaveTimer = useRef<NodeJS.Timeout>();
  const userColorMap = useRef<Map<string, string>>(new Map());

  // Assign stable colors to users
  const getUserColor = (uid: string): string => {
    if (!userColorMap.current.has(uid)) {
      const colorIndex = userColorMap.current.size % USER_COLORS.length;
      userColorMap.current.set(uid, USER_COLORS[colorIndex]);
    }
    return userColorMap.current.get(uid)!;
  };

  // Handle incoming remote changes
  const applyRemoteChange = useCallback((message: any) => {
    if (message.type === "update") {
      const { payload } = message;
      if (payload.content !== undefined && payload.content !== content) {
        setContent(payload.content);
        if (onContentChange) {
          onContentChange(payload.content);
        }
      }
    } else if (message.type === "presence.join") {
      setActiveUsers((prevUsers) => {
        const newUsers = message.active_users.map((uid: string) => ({
          user_id: uid,
          color: getUserColor(uid),
        }));
        return newUsers;
      });
    } else if (message.type === "presence.leave") {
      setActiveUsers((prevUsers) => {
        const newUsers = message.active_users.map((uid: string) => ({
          user_id: uid,
          color: getUserColor(uid),
        }));
        return newUsers;
      });
    }
  }, [content, onContentChange]);

  // Initialize WebSocket connection
  useEffect(() => {
    const getApiBase = () => {
      const env = (import.meta as any).env;
      if (env?.VITE_GUARDIAN_API_BASE) {
        return env.VITE_GUARDIAN_API_BASE;
      }
      if (typeof window !== "undefined" && window.location.origin) {
        return window.location.origin;
      }
      return "http://localhost:8000";
    };

    const apiBase = getApiBase();
    const wsProtocol = apiBase.startsWith("https") ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${apiBase.replace(/^https?:\/\//, "")}/api/collab/ws/${documentId}`;

    try {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log(`Connected to collaborative session for document ${documentId}`);
        setIsConnected(true);

        // Send initial presence
        ws.current?.send(
          JSON.stringify({
            type: "presence",
            user_id: userId,
            action: "join",
          })
        );
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          applyRemoteChange(message);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
      };

      ws.current.onclose = () => {
        console.log("Disconnected from collaborative session");
        setIsConnected(false);
      };

      return () => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(
            JSON.stringify({
              type: "presence",
              user_id: userId,
              action: "leave",
            })
          );
        }
        ws.current?.close();
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
      setIsConnected(false);
    }
  }, [documentId, userId, applyRemoteChange]);

  // Auto-save every 15 seconds
  useEffect(() => {
    autosaveTimer.current = setInterval(async () => {
      try {
        const response = await fetch("/api/documents/autosave", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: threadId,
            content,
          }),
        });

        if (response.ok) {
          setLastAutosave(new Date());
        }
      } catch (error) {
        console.error("Autosave failed:", error);
      }
    }, 15000); // 15 seconds

    return () => {
      if (autosaveTimer.current) {
        clearInterval(autosaveTimer.current);
      }
    };
  }, [content, threadId]);

  // Handle local changes
  const handleChange = (value: string) => {
    setContent(value);

    // Send to other clients
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          content: value,
          user_id: userId,
          timestamp: new Date().toISOString(),
        })
      );
    }

    if (onContentChange) {
      onContentChange(value);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "#fff",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid rgba(0,0,0,.08)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
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
        </div>

        {/* Presence indicators */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {activeUsers.length > 0 && (
            <div style={{ display: "flex", gap: 4 }}>
              {activeUsers.map((user) => (
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
                color: "rgba(0,0,0,.5)",
                whiteSpace: "nowrap",
              }}
            >
              Saved {Math.round((Date.now() - lastAutosave.getTime()) / 1000)}s ago
            </span>
          )}
        </div>
      </div>

      {/* Editor area */}
      <textarea
        value={content}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Start typing... (auto-saves every 15s)"
        style={{
          flex: 1,
          padding: "16px",
          border: "none",
          fontFamily: "monospace",
          fontSize: 14,
          lineHeight: 1.6,
          resize: "none",
          outline: "none",
          color: "rgba(0,0,0,.9)",
        }}
      />
    </div>
  );
}
