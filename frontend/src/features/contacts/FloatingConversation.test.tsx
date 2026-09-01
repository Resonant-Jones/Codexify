import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as directMessages from "@/lib/direct-messages";
import type { DirectMessageConversation } from "@/lib/direct-messages";

import FloatingConversation from "./FloatingConversation";
import { usePeopleMessagingState } from "./usePeopleMessagingState";

vi.mock("@/lib/direct-messages", () => {
  class DirectMessageApiError extends Error {}
  return {
    DirectMessageApiError,
    normalizeDirectMessageError: (error: unknown) =>
      error instanceof Error ? error : new Error("request failed"),
    searchDirectMessageProfiles: vi.fn(),
    resolveDirectMessageRelationship: vi.fn(),
    fetchDirectMessageRelationships: vi.fn(),
    fetchDirectMessageConversations: vi.fn(),
    fetchRelationshipConversations: vi.fn(),
    createDirectMessageConversation: vi.fn(),
    fetchDirectMessageConversation: vi.fn(),
    fetchDirectMessageMessages: vi.fn(),
    sendDirectMessage: vi.fn(),
    fetchThreadProjectScope: vi.fn(),
    fetchProjectLabelMap: vi.fn(),
  };
});

function conversationWithOrigin(originProject: number | null): DirectMessageConversation {
  return {
    conversation_id: "c1",
    relationship_id: "relationship-1",
    kind: "direct",
    created_at: "2026-08-31T00:30:00Z",
    latest_activity_at: "2026-08-31T01:00:00Z",
    participants: [
      {
        node_id: "node-local",
        profile_id: "profile-bob",
        username: "bob",
        username_state: "active",
        display_name: "Bob Tester",
        avatar_url: null,
      },
    ],
    peer: {
      node_id: "node-local",
      profile_id: "profile-bob",
      username: "bob",
      username_state: "active",
      display_name: "Bob Tester",
      avatar_url: null,
    },
    origin: {
      created_by_profile_id: "profile-bob",
      origin_project_id: originProject,
      origin_thread_id: null,
      created_at: "2026-08-31T00:30:00Z",
    },
    placement: {
      project_id: null,
      created_at: null,
      updated_at: null,
    },
    latest_message: null,
  };
}

function message(id: string, body: string) {
  return {
    protocol_version: "1.0",
    message_id: id,
    conversation_id: "c1",
    source: { node_id: "node-local", profile_id: "profile-alice" },
    destination: { node_id: "node-local", profile_id: "profile-bob" },
    content: { type: "text/plain" as const, body },
    created_at: "2026-08-31T01:05:00Z",
  };
}

type HarnessProps = {
  children: (state: ReturnType<typeof usePeopleMessagingState>) => React.ReactNode;
  context?: string;
};

function Harness({ children, context }: HarnessProps) {
  const state = usePeopleMessagingState();
  return (
    <>
      <span data-testid="context">{context ?? "guardian"}</span>
      {children(state)}
    </>
  );
}

const mocked = vi.mocked(directMessages);

beforeEach(() => {
  const portal = document.createElement("div");
  portal.id = "cfy-portal-root";
  document.body.appendChild(portal);
  mocked.fetchDirectMessageConversation.mockResolvedValue(conversationWithOrigin(null));
  mocked.fetchDirectMessageMessages.mockResolvedValue([
    message("m1", "hello bob"),
    message("m2", "reply"),
  ]);
  mocked.sendDirectMessage.mockResolvedValue({
    ok: true,
    replayed: false,
    message: message("m3", "people-proof-floating"),
  });
});

afterEach(() => {
  document.body.innerHTML = "";
  vi.clearAllMocks();
});

describe("FloatingConversation", () => {
  it("pops out as a projection of the same Conversation_ID with its own lineage", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(9));
    });
    const window = await screen.findByTestId("floating-conversation");
    expect(window).toHaveAttribute(
      "aria-label",
      "Floating conversation with Bob Tester"
    );
    expect(
      await screen.findByText((content) => content.includes("Project 9"))
    ).toBeInTheDocument();
    expect(mocked.createDirectMessageConversation).not.toHaveBeenCalled();
  });

  it("never titles the window with the caller when peer is absent", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    // Simulate a pre-peer backend payload: participants[0] is the caller
    // (alice).  The window must NOT title itself with the caller.
    const legacy = {
      ...conversationWithOrigin(null),
      peer: null,
      participants: [
        {
          node_id: "node-local",
          profile_id: "profile-alice",
          username: "alice",
          username_state: "active" as const,
          display_name: "Alice Caller",
          avatar_url: null,
        },
        {
          node_id: "node-local",
          profile_id: "profile-bob",
          username: "bob",
          username_state: "active" as const,
          display_name: "Bob Tester",
          avatar_url: null,
        },
      ],
    };
    await act(async () => {
      capturedState?.popOutConversation("c1", legacy);
    });
    const window = await screen.findByTestId("floating-conversation");
    expect(window).toHaveAttribute(
      "aria-label",
      "Floating conversation with Conversation"
    );
    expect(screen.queryByText("Alice Caller")).not.toBeInTheDocument();
  });

  it("preserves an unsent draft through pop-out, minimize, and restore", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(null));
      capturedState?.setDraft("c1", "unsent draft");
    });
    const textarea = await screen.findByLabelText("Message");
    expect(textarea).toHaveValue("unsent draft");

    await act(async () => {
      capturedState?.minimizeFloating();
    });
    expect(screen.getByTestId("floating-conversation-pill")).toBeInTheDocument();

    await act(async () => {
      capturedState?.restoreFloating();
    });
    expect(screen.getByLabelText("Message")).toHaveValue("unsent draft");
  });

  it("survives the People modal closing (state owner lives above the modal)", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.openPeople();
      capturedState?.popOutConversation("c1", conversationWithOrigin(null));
    });
    expect(screen.getByTestId("floating-conversation")).toBeInTheDocument();
    await act(async () => {
      capturedState?.closePeople();
    });
    expect(screen.getByTestId("floating-conversation")).toBeInTheDocument();
  });

  it("closes only the UI projection without touching backend resources", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(null));
    });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Close conversation" }));
    expect(screen.queryByTestId("floating-conversation")).not.toBeInTheDocument();
    expect(capturedState?.floatingConversationId).toBeNull();
    expect(mocked.sendDirectMessage).not.toHaveBeenCalled();
  });

  it("keeps the active portable conversation when asked to pop out another", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(null));
      capturedState?.setDraft("c1", "keep me");
    });
    let secondPopOut = true;
    await act(async () => {
      secondPopOut = capturedState?.popOutConversation("c2") ?? true;
    });
    expect(secondPopOut).toBe(false);
    expect(capturedState?.floatingConversationId).toBe("c1");
    expect(screen.getByLabelText("Message")).toHaveValue("keep me");
  });

  it("does not rebind lineage when surrounding app context changes", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    const { rerender } = render(
      <Harness context="guardian">
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(9));
    });
    expect(
      await screen.findByText((content) => content.includes("Project 9"))
    ).toBeInTheDocument();
    // Navigation elsewhere: the People surface unmounts nothing — the
    // floating window keeps its own lineage from the cached conversation.
    rerender(
      <Harness context="documents">
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    expect(screen.getByTestId("context").textContent).toBe("documents");
    expect(
      await screen.findByText((content) => content.includes("Project 9"))
    ).toBeInTheDocument();
    expect(mocked.createDirectMessageConversation).not.toHaveBeenCalled();
  });

  it("sends from the floating composer and renders the durable message once", async () => {
    let capturedState: ReturnType<typeof usePeopleMessagingState> | null = null;
    render(
      <Harness>
        {(state) => {
          capturedState = state;
          return <FloatingConversation state={state} />;
        }}
      </Harness>
    );
    await act(async () => {
      capturedState?.popOutConversation("c1", conversationWithOrigin(null));
    });
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Message"), "people-proof-floating");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() =>
      expect(mocked.sendDirectMessage).toHaveBeenCalledWith(
        "c1",
        "people-proof-floating",
        expect.any(String)
      )
    );
    expect(await screen.findByText("people-proof-floating")).toBeInTheDocument();
    expect(screen.getAllByText("people-proof-floating")).toHaveLength(1);
  });
});
