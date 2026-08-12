import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatView from "@/features/chat/ChatView";
import type { CompletionState } from "@/features/chat/useChat";
import RoomMode from "@/features/rooms/RoomMode";
import type {
  HostedRoomDetail,
  HostedRoomMessage,
} from "@/features/rooms/types";
import api from "@/lib/api";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: apiMocks,
}));

vi.mock("@/features/chat/hooks/useChatAutoScroll", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    useChatAutoScroll: () => ({
      containerRef: React.useRef<HTMLDivElement | null>(null),
      endRef: React.useRef<HTMLDivElement | null>(null),
    }),
  };
});

vi.mock("@/components/ui/ContextMenu", () => ({
  default: () => null,
}));

vi.mock("@/components/modals/ImageGenModal", () => ({
  ImageGenModal: () => null,
}));

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

const roomDetail: HostedRoomDetail = {
  id: "room-owner-1",
  slug: "signal-room",
  title: "Signal Room",
  status: "active",
  backing_thread_id: 77,
  enabled_actors: [],
  active_participant_count: 3,
  pending_invitation_count: 0,
  created_at: "2026-08-12T12:00:00Z",
  updated_at: "2026-08-12T12:00:00Z",
  closed_at: null,
  participants: [
    {
      id: "p-zac",
      display_name: "Zac",
      kind: "human",
      role: "owner",
      state: "active",
      joined_at: "2026-08-12T12:00:00Z",
    },
    {
      id: "p-jones",
      display_name: "Jones",
      kind: "human",
      role: "member",
      state: "active",
      joined_at: "2026-08-12T12:00:00Z",
    },
    {
      id: "p-guardian",
      display_name: "Guardian",
      kind: "agent",
      role: "agent",
      state: "active",
      joined_at: "2026-08-12T12:00:00Z",
      actor_source: "resident",
      actor_ref: "guardian",
    },
  ],
  invitations: [],
};

const initialMessages: HostedRoomMessage[] = [
  {
    id: 42,
    role: "user",
    content: "hello from the Room",
    created_at: "2026-08-12T12:01:00Z",
    sender: {
      participant_id: "p-zac",
      display_name: "Zac",
    },
  },
  {
    id: 43,
    role: "assistant",
    content: "Guardian is listening.",
    created_at: "2026-08-12T12:02:00Z",
    sender: {
      participant_id: "p-guardian",
      display_name: "Guardian",
    },
  },
];

const idleCompletion: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
  requestState: null,
};

function installActiveRoomApi(messages = initialMessages) {
  mockApi.get.mockImplementation(async (path: string) => {
    if (path === "/api/hosted-rooms/room-owner-1") {
      return { data: roomDetail };
    }
    if (path === "/api/hosted-rooms/room-owner-1/messages") {
      return { data: messages };
    }
    throw new Error(`Unexpected GET ${path}`);
  });
}

describe("RoomMode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Room detail, active participants, and canonical sender provenance", async () => {
    installActiveRoomApi();

    render(<RoomMode roomId="room-owner-1" onLeave={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Signal Room" })).toBeInTheDocument();
    expect(screen.getByLabelText("Active Room participants")).toHaveTextContent(
      "Zac · Jones · Guardian"
    );
    expect(await screen.findByText("hello from the Room")).toBeInTheDocument();
    expect(screen.getByTestId("chat-message-author")).toHaveTextContent("Zac");
    expect(screen.getByText("Guardian is listening.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Toggle Coding Loop mode" })
    ).not.toBeInTheDocument();
    expect(screen.queryByText("77")).not.toBeInTheDocument();
    expect(screen.getByTestId("room-mode")).toBeInTheDocument();
  });

  it("keeps ordinary Guardian Chat author presentation unchanged without Room sender data", () => {
    render(
      <ChatView
        threadId={77}
        guardianName="Guardian"
        messages={[
          {
            id: 1,
            thread_id: 77,
            role: "user",
            content: "ordinary personal message",
            created_at: "2026-08-12T12:00:00Z",
          },
        ]}
        loading={false}
        error={null}
        hasMore={false}
        completionState={idleCompletion}
        endCompletion={() => undefined}
      />
    );

    expect(screen.getByText("ordinary personal message")).toBeInTheDocument();
    expect(screen.queryByTestId("chat-message-author")).not.toBeInTheDocument();
    expect(screen.queryByText("Room participant")).not.toBeInTheDocument();
  });

  it("uses a neutral author fallback when canonical Room provenance is absent", async () => {
    installActiveRoomApi([
      {
        id: 45,
        role: "user",
        content: "legacy Room message",
        created_at: "2026-08-12T12:04:00Z",
        sender: null,
      },
    ]);

    render(<RoomMode roomId="room-owner-1" onLeave={vi.fn()} />);

    expect(await screen.findByText("legacy Room message")).toBeInTheDocument();
    expect(screen.getByTestId("chat-message-author")).toHaveTextContent(
      "Room participant"
    );
  });

  it("posts through the owner Room route, refreshes canonical messages, and never calls complete", async () => {
    let transcriptReads = 0;
    const refreshedMessages: HostedRoomMessage[] = [
      ...initialMessages,
      {
        id: 44,
        role: "user",
        content: "persist this once",
        created_at: "2026-08-12T12:03:00Z",
        sender: { participant_id: "p-zac", display_name: "Zac" },
      },
    ];
    mockApi.get.mockImplementation(async (path: string) => {
      if (path === "/api/hosted-rooms/room-owner-1") {
        return { data: roomDetail };
      }
      if (path === "/api/hosted-rooms/room-owner-1/messages") {
        transcriptReads += 1;
        return {
          data: transcriptReads === 1 ? initialMessages : refreshedMessages,
        };
      }
      throw new Error(`Unexpected GET ${path}`);
    });
    mockApi.post.mockResolvedValue({ data: refreshedMessages.at(-1) });

    render(<RoomMode roomId="room-owner-1" onLeave={vi.fn()} />);
    const composer = await screen.findByTestId("composer-textarea");
    fireEvent.change(composer, { target: { value: "persist this once" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith(
        "/api/hosted-rooms/room-owner-1/messages",
        { content: "persist this once" }
      );
    });
    await screen.findByText("persist this once");
    expect(transcriptReads).toBe(2);
    expect(composer).toHaveValue("");
    expect(
      mockApi.post.mock.calls.some(([path]) => String(path).includes("complete"))
    ).toBe(false);
  });

  it("preserves a failed draft and blocks duplicate in-flight posts", async () => {
    installActiveRoomApi();
    let rejectPost: ((reason?: unknown) => void) | null = null;
    mockApi.post.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          rejectPost = reject;
        })
    );

    render(<RoomMode roomId="room-owner-1" onLeave={vi.fn()} />);
    const composer = await screen.findByTestId("composer-textarea");
    fireEvent.change(composer, { target: { value: "keep this draft" } });
    const send = screen.getByRole("button", { name: "Send" });
    fireEvent.click(send);
    fireEvent.click(send);

    expect(mockApi.post).toHaveBeenCalledTimes(1);
    rejectPost?.(new Error("network down"));

    expect(
      await screen.findByText("Message was not sent. Check the connection and try again.")
    ).toBeInTheDocument();
    expect(composer).toHaveValue("keep this draft");
  });

  it("disables posting for closed Rooms and keeps unavailable responses neutral", async () => {
    mockApi.get.mockResolvedValueOnce({
      data: { ...roomDetail, status: "closed", closed_at: "2026-08-12T13:00:00Z" },
    });

    const { unmount } = render(
      <RoomMode roomId="room-owner-1" onLeave={vi.fn()} />
    );

    expect(await screen.findByText("This Room is closed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(mockApi.get).not.toHaveBeenCalledWith(
      "/api/hosted-rooms/room-owner-1/messages"
    );
    unmount();

    vi.clearAllMocks();
    mockApi.get.mockRejectedValueOnce({ response: { status: 404 } });
    render(<RoomMode roomId="room-private" onLeave={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Room unavailable" })).toBeInTheDocument();
    expect(screen.getByText(/current account or runtime posture/i)).toBeInTheDocument();
    expect(screen.queryByText(/belongs to another/i)).not.toBeInTheDocument();
    expect(mockApi.get).toHaveBeenCalledTimes(1);
    expect(mockApi.get).toHaveBeenCalledWith(
      "/api/hosted-rooms/room-private"
    );
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("uses the compact touch composer without turning the Room into a multi-column layout", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 390,
    });
    installActiveRoomApi();

    render(<RoomMode roomId="room-owner-1" onLeave={vi.fn()} />);

    expect(await screen.findByTestId("room-mode")).toBeInTheDocument();
    expect(screen.getByTestId("composer-content-plane").parentElement).toHaveAttribute(
      "data-mobile-compact",
      "true"
    );
    expect(
      screen.getByRole("button", { name: "Leave Room and return to Guardian" })
    ).toHaveClass("min-h-11");
    expect(screen.queryByText("Workspace")).not.toBeInTheDocument();
  });
});
