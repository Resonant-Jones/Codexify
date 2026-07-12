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

  describe("typing", () => {
    it("notifyTyping() sends typing.start with user_id and timestamp", async () => {
      render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      const { result } = render(defaultOptions());
      await act(async () => {
        latestWs().simulateOpen();
        result.current.notifyTyping();
      });

      const typingMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "typing.start"
      );
      expect(typingMsgs.length).toBeGreaterThanOrEqual(1);
      expect(typingMsgs[typingMsgs.length - 1].user_id).toBe("user1");
      expect(typingMsgs[typingMsgs.length - 1].timestamp).toBeDefined();
    });

    it("stopTyping() sends typing.stop with user_id and timestamp", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
        result.current.stopTyping();
      });

      const typingMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "typing.stop"
      );
      expect(typingMsgs.length).toBeGreaterThanOrEqual(1);
      expect(typingMsgs[typingMsgs.length - 1].user_id).toBe("user1");
      expect(typingMsgs[typingMsgs.length - 1].timestamp).toBeDefined();
    });

    it("incoming typing.start adds a remote user to typingUsers", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);
      expect(result.current.typingUsers[0].user_id).toBe("user2");
    });

    it("incoming typing.stop removes a remote user from typingUsers", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.stop",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("typing events from the current user are ignored", async () => {
      const { result } = render(defaultOptions({ userId: "user1" }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user1",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("typing users auto-expire after 3000ms", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);

      // Advance past the expiry threshold
      await act(async () => {
        vi.advanceTimersByTime(3_100);
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("typing expiry timer resets on repeated typing.start", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      // Advance 2s — not past expiry yet
      await act(async () => {
        vi.advanceTimersByTime(2_000);
      });

      // Another typing.start resets the timer
      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      // Advance another 2s — still within the reset window
      await act(async () => {
        vi.advanceTimersByTime(2_000);
      });

      expect(result.current.typingUsers).toHaveLength(1);

      // Advance past full expiry
      await act(async () => {
        vi.advanceTimersByTime(1_100);
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("cleans up typing timers on unmount", async () => {
      const { result, unmount } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);

      // Unmount before expiry — should not throw
      unmount();

      // Advance past expiry — timers should have been cleared, no state updates
      await act(async () => {
        vi.advanceTimersByTime(5_000);
      });

      // No assertion needed — just verifying no crash from stale timer
    });

    it("notifyTyping does not send when disconnected", async () => {
      const { result } = render(defaultOptions());

      // Do not open — socket is still connecting
      await act(async () => {
        result.current.notifyTyping();
      });

      const typingMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "typing.start"
      );
      expect(typingMsgs.length).toBe(0);
    });

    it("wrapped update envelope with typing.start adds a remote typing user", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.start",
            user_id: "user2",
            timestamp: new Date().toISOString(),
          },
          user_id: "user2",
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);
      expect(result.current.typingUsers[0].user_id).toBe("user2");
    });

    it("wrapped update envelope with typing.stop removes a remote typing user", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      // Add via direct typing.start first
      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);

      // Remove via wrapped typing.stop
      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.stop",
            user_id: "user2",
            timestamp: new Date().toISOString(),
          },
          user_id: "user2",
        });
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("wrapped typing event from the current user is ignored", async () => {
      const { result } = render(defaultOptions({ userId: "user1" }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.start",
            user_id: "user1",
            timestamp: new Date().toISOString(),
          },
          user_id: "user1",
        });
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("wrapped typing event does not call onRemoteContentUpdate", async () => {
      const onRemoteContentUpdate = vi.fn();
      render(defaultOptions({ onRemoteContentUpdate }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.start",
            user_id: "user2",
            timestamp: new Date().toISOString(),
          },
          user_id: "user2",
        });
      });

      expect(onRemoteContentUpdate).not.toHaveBeenCalled();
    });

    it("wrapped typing user auto-expires after 3000ms", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.start",
            user_id: "user2",
            timestamp: new Date().toISOString(),
          },
          user_id: "user2",
        });
      });

      expect(result.current.typingUsers).toHaveLength(1);

      await act(async () => {
        vi.advanceTimersByTime(3_100);
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("repeated wrapped typing.start resets the expiry timer", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "typing.start",
            user_id: "user2",
            timestamp: new Date().toISOString(),
          },
          user_id: "user2",
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(2_000);
      });

      // Another typing.start resets the timer
      await act(async () => {
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
          timestamp: new Date().toISOString(),
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(2_000);
      });

      expect(result.current.typingUsers).toHaveLength(1);

      await act(async () => {
        vi.advanceTimersByTime(1_100);
      });

      expect(result.current.typingUsers).toHaveLength(0);
    });

    it("ordinary content update still calls onRemoteContentUpdate", async () => {
      const onRemoteContentUpdate = vi.fn();
      render(defaultOptions({ onRemoteContentUpdate }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: { content: "normal update" },
          user_id: "user2",
        });
      });

      expect(onRemoteContentUpdate).toHaveBeenCalledWith("normal update");
    });
  });

  describe("cursor presence", () => {
    it("sendCursorPosition() sends cursor.position with user_id, position, and timestamp", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
        result.current.sendCursorPosition(7);
      });

      const cursorMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "cursor.position"
      );
      expect(cursorMsgs.length).toBeGreaterThanOrEqual(1);
      const last = cursorMsgs[cursorMsgs.length - 1];
      expect(last.user_id).toBe("user1");
      expect(last.position).toBe(7);
      expect(last.timestamp).toBeDefined();
    });

    it("sendCursorPosition() does not send when disconnected", async () => {
      const { result } = render(defaultOptions());

      // Do not open — socket is still connecting
      await act(async () => {
        result.current.sendCursorPosition(7);
      });

      const cursorMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "cursor.position"
      );
      expect(cursorMsgs.length).toBe(0);
    });

    it("sendCursorPosition() does not send invalid positions", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        result.current.sendCursorPosition(-1);
        result.current.sendCursorPosition(Number.NaN);
        result.current.sendCursorPosition("five" as any);
        result.current.sendCursorPosition(Number.POSITIVE_INFINITY);
      });

      const cursorMsgs = latestWs().sentMessages.filter(
        (m: any) => m.type === "cursor.position"
      );
      expect(cursorMsgs.length).toBe(0);
    });

    it("direct incoming cursor.position adds a remote cursor user", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 4,
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.cursorUsers).toHaveLength(1);
      expect(result.current.cursorUsers[0].user_id).toBe("user2");
      expect(result.current.cursorUsers[0].position).toBe(4);
    });

    it("wrapped incoming cursor.position adds a remote cursor user", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: {
            type: "cursor.position",
            user_id: "user2",
            position: 9,
          },
          user_id: "user2",
        });
      });

      expect(result.current.cursorUsers).toHaveLength(1);
      expect(result.current.cursorUsers[0].user_id).toBe("user2");
      expect(result.current.cursorUsers[0].position).toBe(9);
    });

    it("direct incoming cursor.position updates an existing cursor user's position", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 1,
        });
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 8,
        });
      });

      expect(result.current.cursorUsers).toHaveLength(1);
      expect(result.current.cursorUsers[0].position).toBe(8);
    });

    it("cursor events from the current user are ignored", async () => {
      const { result } = render(defaultOptions({ userId: "user1" }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user1",
          position: 3,
        });
      });

      expect(result.current.cursorUsers).toHaveLength(0);
    });

    it("cursor users auto-expire after 5000ms", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 2,
        });
      });

      expect(result.current.cursorUsers).toHaveLength(1);

      await act(async () => {
        vi.advanceTimersByTime(5_100);
      });

      expect(result.current.cursorUsers).toHaveLength(0);
    });

    it("repeated cursor events reset the expiry timer", async () => {
      const { result } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 1,
        });
      });

      // Advance 4s — not past expiry yet
      await act(async () => {
        vi.advanceTimersByTime(4_000);
      });

      // Another cursor event resets the timer
      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 5,
        });
      });

      // Advance another 4s — still within the reset window
      await act(async () => {
        vi.advanceTimersByTime(4_000);
      });

      expect(result.current.cursorUsers).toHaveLength(1);

      // Advance past full expiry
      await act(async () => {
        vi.advanceTimersByTime(1_100);
      });

      expect(result.current.cursorUsers).toHaveLength(0);
    });

    it("cleans up cursor timers on unmount", async () => {
      const { result, unmount } = render(defaultOptions());

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user2",
          position: 2,
        });
      });

      expect(result.current.cursorUsers).toHaveLength(1);

      // Unmount before expiry — should not throw
      unmount();

      // Advance past expiry — timers should have been cleared, no state updates
      await act(async () => {
        vi.advanceTimersByTime(6_000);
      });
    });

    it("cursor presence does not interfere with typing or content updates", async () => {
      const onRemoteContentUpdate = vi.fn();
      const { result } = render(defaultOptions({ onRemoteContentUpdate }));

      await act(async () => {
        latestWs().simulateOpen();
      });

      await act(async () => {
        latestWs().simulateMessage({
          type: "update",
          payload: { content: "content still flows" },
          user_id: "user2",
        });
        latestWs().simulateMessage({
          type: "cursor.position",
          user_id: "user3",
          position: 6,
        });
        latestWs().simulateMessage({
          type: "typing.start",
          user_id: "user2",
        });
      });

      expect(onRemoteContentUpdate).toHaveBeenCalledWith("content still flows");
      expect(result.current.cursorUsers).toHaveLength(1);
      expect(result.current.cursorUsers[0].user_id).toBe("user3");
      expect(result.current.typingUsers).toHaveLength(1);
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
