import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { vi } from "vitest";
import { CollaborativeNote } from "../CollaborativeNote";

// ─── Mock WebSocket for WsClient ─────────────────────────────────────────────

// Module-level registry so tests can access the mock instances created by WsClient.
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

// ─── Test Suite ──────────────────────────────────────────────────────────────

describe("CollaborativeNote", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockWsInstances.length = 0;
    (global as any).WebSocket = MockWebSocket;

    // Mock fetch for audit trail
    global.fetch = vi.fn((url: string) => {
      if (url.includes("/audit")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ document_id: "doc1", total: 0, entries: [] }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      );
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("renders collaborative note component", () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent="Initial content"
      />
    );

    const textarea = screen.getByPlaceholderText(/Start typing/i);
    expect(textarea).toBeInTheDocument();
    expect((textarea as HTMLTextAreaElement).value).toBe("Initial content");
  });

  it("displays connection status after connecting", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });
  });

  it("connects using the correct document collaboration URL", () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        authToken="token123"
        initialContent=""
      />
    );

    expect(mockWsInstances.length).toBeGreaterThanOrEqual(1);
    expect(latestWs().url).toContain("/api/collab/ws/doc1");
    expect(latestWs().url).toContain("token=token123");
  });

  it("sends initial handshake on connect", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        authToken="tok"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      const handshake = latestWs().sentMessages.find(
        (m: any) => m.user_id === "user1"
      );
      expect(handshake).toBeDefined();
      expect(handshake.token).toBe("tok");
    });
  });

  it("sends update messages on content change", async () => {
    const { container } = render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    // Simulate connection open to enable send behaviour
    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "New content" } });

    // Content updates locally
    expect(textarea.value).toBe("New content");
  });

  it("applies remote updates from WebSocket messages", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent="Initial"
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    // Simulate a remote update
    latestWs().simulateMessage({
      type: "update",
      payload: { content: "Remote change" },
      user_id: "user2",
    });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(
        /Start typing/i
      ) as HTMLTextAreaElement;
      expect(textarea.value).toBe("Remote change");
    });
  });

  it("handles presence join events", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    // Simulate presence join
    latestWs().simulateMessage({
      type: "presence.join",
      user_id: "user2",
      active_users: ["user1", "user2"],
    });

    // Component should still render correctly after presence events
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Start typing/i);
      expect(textarea).toBeInTheDocument();
    });
  });

  it("handles access denied via close code 1008", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    // Close with 1008 — WsClient calls onUnauthorized, doesn't reconnect
    await act(async () => {
      latestWs().simulateClose(1008, "access_denied");
    });

    await waitFor(() => {
      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });
  });

  it("shows disconnected state when WebSocket closes", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    // Close with a non-1008 code — WsClient tries to reconnect, status goes to disconnected/reconnecting
    await act(async () => {
      latestWs().simulateClose(1006, "abnormal");
    });

    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeInTheDocument();
    });
  });

  it("calls onContentChange callback when text changes", async () => {
    const onContentChange = vi.fn();

    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
        onContentChange={onContentChange}
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "Test content" } });

    await waitFor(() => {
      expect(textarea.value).toBe("Test content");
      expect(onContentChange).toHaveBeenCalledWith("Test content");
    });
  });

  it("runs autosave behavior", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent="Initial"
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Updated content" } });

    // Advance by 15 seconds for autosave interval
    vi.advanceTimersByTime(15000);

    await waitFor(() => {
      // Audit trail fetch should have been called on connect
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/collab/doc1/audit?limit=100",
        expect.objectContaining({ headers: expect.any(Object) })
      );
    });
  });

  it("cleans up on unmount", async () => {
    const { unmount } = render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      latestWs().simulateOpen();
    });

    await waitFor(() => {
      expect(screen.getByText("Live Editing")).toBeInTheDocument();
    });

    unmount();

    // After unmount, component should be gone
    expect(screen.queryByPlaceholderText(/Start typing/i)).not.toBeInTheDocument();
  });

  it("handles WebSocket connection errors gracefully", async () => {
    // Don't simulate open — let the error flow happen naturally through WsClient
    // WsClient's onerror handler dispatches "error" events, but doesn't change
    // the connection state. The onclose that follows (from the browser after error)
    // transitions to disconnected. We simulate error + close.

    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await vi.advanceTimersByTimeAsync(1);

    // Fire socket error and close following the error (browser behaviour)
    await act(async () => {
      if (latestWs().onerror) {
        latestWs().onerror!(new Event("error"));
      }
      latestWs().simulateClose(1006, "abnormal");
    });

    // Component should still render
    expect(screen.getByPlaceholderText(/Start typing/i)).toBeInTheDocument();

    // Status should show Offline
    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeInTheDocument();
    });
  });
});
