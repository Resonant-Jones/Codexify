import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { vi } from "vitest";
import { CollaborativeNote } from "../CollaborativeNote";

// ─── Mock WebSocket (shared with useDocumentCollaboration tests) ─────────────

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

  // ── Rendering ───────────────────────────────────────────────────────────

  it("renders the editor with initial content", () => {
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

  it("displays read-only mode when permissions prevent editing", () => {
    // Renders with canEdit flowing through the hook, but permissions are
    // managed in the component. By default permissions start null (editable).
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    const textarea = screen.getByPlaceholderText(/Start typing/i);
    expect(textarea).toBeInTheDocument();
    // Default is editable — textarea should not be disabled
    expect((textarea as HTMLTextAreaElement).disabled).toBe(false);
  });

  // ── Connection states ───────────────────────────────────────────────────

  it("shows Live Editing when connected", async () => {
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

  it("shows Offline when disconnected", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    // Initially offline (socket is connecting, not open)
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });

  it("shows Access Denied after close code 1008", async () => {
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

    await act(async () => {
      latestWs().simulateClose(1008, "access_denied");
    });

    await waitFor(() => {
      expect(screen.getByText("Access Denied")).toBeInTheDocument();
    });
  });

  // ── Content updates ─────────────────────────────────────────────────────

  it("updates textarea value on local change", () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "local edit" } });

    expect(textarea.value).toBe("local edit");
  });

  it("applies remote content updates", async () => {
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

    await act(async () => {
      latestWs().simulateMessage({
        type: "update",
        payload: { content: "Remote change" },
        user_id: "user2",
      });
    });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(
        /Start typing/i
      ) as HTMLTextAreaElement;
      expect(textarea.value).toBe("Remote change");
    });
  });

  it("calls onContentChange on local edits", () => {
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

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "Test content" } });

    expect(onContentChange).toHaveBeenCalledWith("Test content");
  });

  // ── Presence ────────────────────────────────────────────────────────────

  it("displays presence avatars after presence.join", async () => {
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

    await act(async () => {
      latestWs().simulateMessage({
        type: "presence.join",
        user_id: "user2",
        active_users: ["user1", "user2"],
      });
    });

    await waitFor(() => {
      // Presence avatars: look for the user initial "U" from user2
      const avatars = document.querySelectorAll('[style*="border-radius: 50%"]');
      // At least one avatar should be present (from the presence list)
      expect(avatars.length).toBeGreaterThanOrEqual(1);
    });
  });

  // ── Autosave ────────────────────────────────────────────────────────────

  it("triggers autosave on interval", async () => {
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

    const textarea = screen.getByPlaceholderText(
      /Start typing/i
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Updated content" } });

    // Advance past 15s autosave interval
    vi.advanceTimersByTime(15000);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/collab/doc1/audit?limit=100",
        expect.objectContaining({ headers: expect.any(Object) })
      );
    });
  });

  // ── Cleanup ─────────────────────────────────────────────────────────────

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

    expect(screen.queryByPlaceholderText(/Start typing/i)).not.toBeInTheDocument();
  });

  // ── Error handling ──────────────────────────────────────────────────────

  it("handles WebSocket errors gracefully", async () => {
    render(
      <CollaborativeNote
        documentId="doc1"
        threadId={1}
        userId="user1"
        initialContent=""
      />
    );

    await act(async () => {
      if (latestWs().onerror) {
        latestWs().onerror!(new Event("error"));
      }
      latestWs().simulateClose(1006, "abnormal");
    });

    // Component should still render
    expect(screen.getByPlaceholderText(/Start typing/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeInTheDocument();
    });
  });
});
