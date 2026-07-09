import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { useDocumentCollaboration } from "../useDocumentCollaboration";
import type { UseDocumentCollaborationOptions } from "../useDocumentCollaboration";

// ─── Wrapper without React.StrictMode to prevent double-effect invocation ────

function SimpleWrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(React.Fragment, null, children);
}

function render(options: UseDocumentCollaborationOptions) {
  return renderHook(() => useDocumentCollaboration(options), {
    wrapper: SimpleWrapper,
  });
}

// ─── Mock WebSocket ──────────────────────────────────────────────────────────

const mockWsInstances: MockWebSocket[] = [];

class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  sentMessages: any[] = [];
  closedCode: number | null = null;
  closedReason: string | null = null;

  constructor(url: string) {
    this.url = url;
    mockWsInstances.push(this);
  }

  send(data: string) {
    if (this.readyState === MockWebSocket.OPEN) {
      try {
        this.sentMessages.push(JSON.parse(data));
      } catch {
        this.sentMessages.push(data);
      }
    }
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    this.closedCode = code ?? null;
    this.closedReason = reason ?? null;
    if (this.onclose) {
      this.onclose(
        new CloseEvent("close", { code: code ?? 1000, reason: reason ?? "" })
      );
    }
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: unknown) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(data) })
    );
  }

  simulateClose(code = 1000, reason = "") {
    this.readyState = MockWebSocket.CLOSED;
    this.closedCode = code;
    this.closedReason = reason;
    this.onclose?.(new CloseEvent("close", { code, reason }));
  }
}

function latestWs(): MockWebSocket {
  return mockWsInstances[mockWsInstances.length - 1];
}

function defaultOptions(
  overrides: Partial<UseDocumentCollaborationOptions> = {}
): UseDocumentCollaborationOptions {
  return {
    documentId: "doc1",
    userId: "user1",
    authToken: "tok",
    canEdit: true,
    onRemoteContentUpdate: vi.fn(),
    onAuditRefresh: vi.fn(),
    ...overrides,
  };
}

// ─── Test Suite ──────────────────────────────────────────────────────────────

describe("useDocumentCollaboration", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockWsInstances.length = 0;
    (global as any).WebSocket = MockWebSocket;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("connection lifecycle", () => {
    it("creates a WebSocket client for the document collaboration URL", () => {
      render(defaultOptions());
      expect(mockWsInstances.length).toBeGreaterThanOrEqual(1);
      expect(latestWs().url).toContain("/api/collab/ws/doc1");
    });

    it("appends token to the URL when provided", () => {
      render(defaultOptions({ authToken: "secret" }));
      expect(latestWs().url).toContain("token=secret");
    });

    it("sends initial handshake after connect", async () => {
      render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      const handshake = latestWs().sentMessages.find(
        (m: any) => m.user_id === "user1"
      );
      expect(handshake).toBeDefined();
      expect(handshake.token).toBe("tok");
    });

    it("reports connected status after open", async () => {
      const { result } = render(defaultOptions());

      expect(result.current.isConnected).toBe(false);

      await act(async () => {
        latestWs().simulateOpen();
      });

      expect(result.current.isConnected).toBe(true);
    });

    it("reports disconnected status after close", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });
      expect(result.current.isConnected).toBe(true);

      await act(async () => {
        latestWs().simulateClose(1006, "abnormal");
      });
      expect(result.current.isConnected).toBe(false);
    });

    it("sets access denied on close code 1008", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateClose(1008, "access_denied");
      });

      expect(result.current.accessDenied).toBe(true);
    });

    it("calls onAuditRefresh when connection opens", async () => {
      const onAuditRefresh = vi.fn();
      render(defaultOptions({ onAuditRefresh }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      expect(onAuditRefresh).toHaveBeenCalledTimes(1);
    });

    it("cleans up the client on unmount", () => {
      const { unmount } = render(defaultOptions());

      const ws = latestWs();
      const closeSpy = vi.spyOn(ws, "close");

      unmount();

      expect(closeSpy).toHaveBeenCalled();
    });
  });

  describe("remote updates", () => {
    it("dispatches remote update content to onRemoteContentUpdate", async () => {
      const onRemoteContentUpdate = vi.fn();
      render(defaultOptions({ onRemoteContentUpdate }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: { content: "Remote change" },
          user_id: "user2",
        });
      });

      expect(onRemoteContentUpdate).toHaveBeenCalledWith("Remote change");
    });

    it("handles update messages without a payload wrapper", async () => {
      const onRemoteContentUpdate = vi.fn();
      render(defaultOptions({ onRemoteContentUpdate }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          content: "Direct content",
          user_id: "user2",
        });
      });

      expect(onRemoteContentUpdate).toHaveBeenCalledWith("Direct content");
    });
  });

  describe("presence", () => {
    it("updates active users on presence.join", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.join",
          user_id: "user2",
          active_users: ["user1", "user2"],
        });
      });

      expect(result.current.activeUsers).toHaveLength(2);
      expect(result.current.activeUsers.map((u) => u.user_id)).toEqual([
        "user1",
        "user2",
      ]);
    });

    it("updates active users on presence.leave", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.join",
          user_id: "user2",
          active_users: ["user1", "user2"],
        });
      });

      expect(result.current.activeUsers).toHaveLength(2);

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.leave",
          user_id: "user2",
          active_users: ["user1"],
        });
      });

      expect(result.current.activeUsers).toHaveLength(1);
      expect(result.current.activeUsers[0].user_id).toBe("user1");
    });

    it("assigns stable colours to users", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.join",
          user_id: "user2",
          active_users: ["user1", "user2"],
        });
      });

      expect(result.current.activeUsers).toHaveLength(2);

      const user2color = result.current.activeUsers.find(
        (u) => u.user_id === "user2"
      )?.color;

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.leave",
          user_id: "user2",
          active_users: ["user1"],
        });
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "presence.join",
          user_id: "user2",
          active_users: ["user1", "user2"],
        });
      });

      const rejoinColor = result.current.activeUsers.find(
        (u) => u.user_id === "user2"
      )?.color;
      expect(rejoinColor).toBe(user2color);
    });
  });

  describe("sendContentUpdate", () => {
    it("sends the update payload when connected and editable", async () => {
      const { result } = render(defaultOptions({ canEdit: true }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        result.current.sendContentUpdate("hello world");
      });

      const updates = latestWs().sentMessages.filter(
        (m: any) => m.type === "update"
      );
      expect(updates.length).toBeGreaterThanOrEqual(1);
      expect(updates[updates.length - 1].content).toBe("hello world");
      expect(updates[updates.length - 1].user_id).toBe("user1");
      expect(updates[updates.length - 1].timestamp).toBeDefined();
    });

    it("does not send when canEdit is false", async () => {
      const { result } = render(defaultOptions({ canEdit: false }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        result.current.sendContentUpdate("should not send");
      });

      const updates = latestWs().sentMessages.filter(
        (m: any) => m.type === "update"
      );
      expect(updates.length).toBe(0);
    });

    it("does not send when disconnected", async () => {
      const { result } = render(defaultOptions({ canEdit: true }));

      // Do not open — socket is still connecting
      await act(async () => {
        result.current.sendContentUpdate("should not send");
      });

      const updates = latestWs().sentMessages.filter(
        (m: any) => m.type === "update"
      );
      expect(updates.length).toBe(0);
    });
  });
});
