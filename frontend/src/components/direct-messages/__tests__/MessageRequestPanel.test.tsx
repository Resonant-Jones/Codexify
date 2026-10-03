import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MessageRequestPanel from "../MessageRequestPanel";
import {
  archiveMessageRequest,
  claimSocialIdentityUsername,
  fetchMessageRequests,
  fetchMessageRequestHistoryPreference,
  fetchOwnSocialIdentity,
  sendMessageRequest,
  setMessageRequestHistoryPreference,
  transitionMessageRequest,
  type DirectMessageRequest,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/direct-messages")>()),
  archiveMessageRequest: vi.fn(),
  claimSocialIdentityUsername: vi.fn(),
  fetchMessageRequests: vi.fn(),
  fetchMessageRequestHistoryPreference: vi.fn(),
  fetchOwnSocialIdentity: vi.fn(),
  sendMessageRequest: vi.fn(),
  setMessageRequestHistoryPreference: vi.fn(),
  transitionMessageRequest: vi.fn(),
}));

const alice: DirectMessageSocialProfile = {
  node_id: "local",
  profile_id: "alice-profile",
  username: "alice",
  username_state: "active",
  display_name: "Alice",
  avatar_url: null,
};
const bob: DirectMessageSocialProfile = {
  ...alice,
  profile_id: "bob-profile",
  username: "bob",
  display_name: "Bob",
};
const pending: DirectMessageRequest = {
  request_id: "request-1",
  relationship_id: "pair",
  sender_profile_id: bob.profile_id,
  recipient_profile_id: alice.profile_id,
  peer: bob,
  note: "Hello Alice",
  state: "pending",
  created_at: "2026-10-02T00:00:00Z",
  expires_at: "2026-11-01T00:00:00Z",
  transitioned_at: null,
  conversation_id: null,
  first_message_id: null,
  outgoing: false,
};
const onIdentity = vi.fn();
const onAccepted = vi.fn().mockResolvedValue(undefined);
const onClose = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchOwnSocialIdentity).mockResolvedValue(alice);
  vi.mocked(fetchMessageRequests).mockResolvedValue([]);
  vi.mocked(fetchMessageRequestHistoryPreference).mockResolvedValue(false);
});
const show = (introPeer: DirectMessageSocialProfile | null = null) =>
  render(
    <MessageRequestPanel
      introPeer={introPeer}
      onIntroClose={onClose}
      onIdentity={onIdentity}
      onAccepted={onAccepted}
    />,
  );

describe("human message requests", () => {
  it("claims an intentional username without changing the Profile address", async () => {
    vi.mocked(fetchOwnSocialIdentity).mockResolvedValueOnce({
      ...alice,
      username: null,
      username_state: "unset",
    });
    vi.mocked(claimSocialIdentityUsername).mockResolvedValue(alice);
    show();
    await screen.findByRole("form", { name: "Choose messaging username" });
    fireEvent.change(screen.getByLabelText("Messaging username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Claim username" }));
    await waitFor(() =>
      expect(claimSocialIdentityUsername).toHaveBeenCalledWith("alice"),
    );
    await screen.findByText("Your username: @alice");
    expect(onIdentity).toHaveBeenLastCalledWith(alice);
  });

  it("sends one intro with a stable retry key and only the social destination", async () => {
    vi.mocked(sendMessageRequest).mockRejectedValueOnce(
      new Error("Network unavailable"),
    );
    vi.mocked(sendMessageRequest).mockResolvedValueOnce({
      ...pending,
      outgoing: true,
    });
    show(bob);
    fireEvent.change(screen.getByLabelText("Introductory note"), {
      target: { value: "Hi Bob" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await screen.findByRole("alert");
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Send request" }),
      ).not.toBeDisabled(),
    );
    const firstKey = vi.mocked(sendMessageRequest).mock.calls[0][2];
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(sendMessageRequest).toHaveBeenNthCalledWith(
      2,
      bob,
      "Hi Bob",
      firstKey,
    );
    expect(onAccepted).not.toHaveBeenCalled();
  });

  it("presents the safe policy message when request admission fails", async () => {
    vi.mocked(sendMessageRequest).mockRejectedValueOnce(Object.assign(new Error("Request failed with status code 429"), {
      response: { status: 429, data: { detail: { error: "message_request_rate_limited", message: "Too many requests. Please try later.", recipient_policy: "private" } } },
    }));
    show(bob);
    fireEvent.change(screen.getByLabelText("Introductory note"), { target: { value: "Hello Bob" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests. Please try later.");
    expect(screen.getByRole("alert")).not.toHaveTextContent("private");
    expect(onAccepted).not.toHaveBeenCalled();
  });

  it("accepts incoming requests and opens the returned conversation", async () => {
    vi.mocked(fetchMessageRequests).mockResolvedValue([pending]);
    vi.mocked(transitionMessageRequest).mockResolvedValue({
      ...pending,
      state: "accepted",
      conversation_id: "conversation-1",
    });
    show();
    fireEvent.click(
      await screen.findByRole("button", { name: "Accept request" }),
    );
    await waitFor(() =>
      expect(onAccepted).toHaveBeenCalledWith("conversation-1"),
    );
    expect(transitionMessageRequest).toHaveBeenCalledWith(
      "request-1",
      "accept",
    );
    expect(
      screen.queryByRole("button", { name: "Withdraw request" }),
    ).not.toBeInTheDocument();
  });

  it("offers decline to a recipient and withdrawal to a sender", async () => {
    vi.mocked(fetchMessageRequests).mockResolvedValue([pending]);
    vi.mocked(transitionMessageRequest).mockResolvedValue({
      ...pending,
      state: "declined",
    });
    const view = show();
    fireEvent.click(
      await screen.findByRole("button", { name: "Decline request" }),
    );
    await waitFor(() =>
      expect(transitionMessageRequest).toHaveBeenCalledWith(
        "request-1",
        "decline",
      ),
    );
    view.unmount();
    vi.mocked(fetchMessageRequests).mockResolvedValue([
      { ...pending, outgoing: true },
    ]);
    vi.mocked(transitionMessageRequest).mockResolvedValue({
      ...pending,
      outgoing: true,
      state: "withdrawn",
    });
    show();
    fireEvent.click(
      await screen.findByRole("button", { name: "Withdraw request" }),
    );
    await waitFor(() =>
      expect(transitionMessageRequest).toHaveBeenCalledWith(
        "request-1",
        "withdraw",
      ),
    );
    expect(
      screen.queryByRole("button", { name: "Accept request" }),
    ).not.toBeInTheDocument();
  });

  it("refreshes and exposes retained expired history with local cleanup controls", async () => {
    vi.mocked(fetchMessageRequests).mockImplementation(async (history) =>
      history ? [{ ...pending, state: "expired" }] : [],
    );
    show();
    await screen.findByText("Your username: @alice");
    fireEvent.click(screen.getByRole("button", { name: "Refresh requests" }));
    await waitFor(() => expect(fetchMessageRequests).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Request history" }));
    await screen.findByText(/From Bob · expired/);
    fireEvent.click(
      screen.getByRole("button", { name: "Remove from my history" }),
    );
    await waitFor(() =>
      expect(archiveMessageRequest).toHaveBeenCalledWith("request-1"),
    );
    await waitFor(() =>
      expect(screen.getByRole("checkbox")).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() =>
      expect(setMessageRequestHistoryPreference).toHaveBeenCalledWith(true),
    );
    expect(
      screen.getByText(/History cleanup affects your view only/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Accept request" }),
    ).not.toBeInTheDocument();
  });
});
