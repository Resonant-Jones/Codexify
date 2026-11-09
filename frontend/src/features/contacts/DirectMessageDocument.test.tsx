import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import DirectMessageDocument from "./DirectMessageDocument";
import { revokeSharedDocument, type DirectMessageEnvelope } from "@/lib/direct-messages";

vi.mock("@/lib/direct-messages", () => ({
  revokeSharedDocument: vi.fn(async () => {}),
  sharedDocumentDownloadUrl: vi.fn(),
}));

it("offers revocation only to the sender and removes the attachment after confirmation", async () => {
  const message: DirectMessageEnvelope = {
    protocol_version: "1.0",
    message_id: "message",
    conversation_id: "conversation",
    source: { node_id: "node", profile_id: "owner" },
    destination: { node_id: "node", profile_id: "recipient" },
    content: { type: "text/plain", body: "Shared a document." },
    created_at: "2026-11-09T12:00:00Z",
    document_attachment: { available: true, can_revoke: false, filename: "notes.pdf" },
  };
  const { rerender } = render(<DirectMessageDocument message={message} />);
  expect(screen.getByRole("button", { name: "Download notes.pdf" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Revoke access" })).not.toBeInTheDocument();

  const senderMessage = {
    ...message,
    document_attachment: { available: true, can_revoke: true, filename: "notes.pdf" },
  };
  rerender(<DirectMessageDocument message={senderMessage} />);
  await userEvent.setup().click(screen.getByRole("button", { name: "Revoke access" }));
  expect(revokeSharedDocument).toHaveBeenCalledWith(senderMessage);
  expect(await screen.findByText("Access revoked.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Download notes.pdf" })).not.toBeInTheDocument();
});
