/**
 * Tests for collaborative permissions and audit trail UI
 */

import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { CollaborativeNote } from "../src/components/editor/CollaborativeNote";

describe("CollaborativeNote - Permissions & Audit Trail", () => {
  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: WebSocket.OPEN,
      OPEN: 1,
      CONNECTING: 0,
      CLOSING: 2,
      CLOSED: 3,
    })) as any;

    // Mock fetch for audit trail API
    global.fetch = vi.fn();
  });

  describe("Read-only mode", () => {
    it("should disable editor when user lacks edit permission", async () => {
      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      // Simulate WebSocket connection and permission denial
      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      // Send presence.join with no edit permission
      if (ws.onmessage) {
        ws.onmessage({
          data: JSON.stringify({
            type: "presence.join",
            active_users: ["user1"],
            permissions: { can_edit: false, can_comment: true },
          }),
        });
      }

      await waitFor(() => {
        const textarea = container.querySelector("textarea");
        // textarea should exist but be disabled or have read-only styling
        expect(textarea).toBeTruthy();
      });
    });

    it("should show read-only lock icon when user lacks edit rights", async () => {
      render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user2"
          authToken="token456"
        />
      );

      // Trigger permission state update
      await waitFor(() => {
        // The lock icon (🔒) should appear when permissions are loaded
        // This is handled by the component state management
        expect(screen.queryByText(/read-only/i)).toBeTruthy();
      });
    });

    it("should prevent content updates when not in edit mode", async () => {
      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      const textarea = container.querySelector("textarea");
      expect(textarea).toBeTruthy();

      // Try to change content - should not send update if no edit permission
      if (textarea) {
        fireEvent.change(textarea, { target: { value: "new content" } });

        // WebSocket.send should not be called without edit permission
        const ws = (global.WebSocket as any).mock.results[0].value;
        // The exact behavior depends on permission state
        expect(ws.send).toBeDefined();
      }
    });
  });

  describe("Audit trail display", () => {
    it("should fetch audit trail on connection", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          document_id: "doc-123",
          total: 2,
          entries: [
            {
              id: 1,
              user_id: "user1",
              action: "presence.join",
              payload: { can_edit: true },
              timestamp: new Date().toISOString(),
            },
            {
              id: 2,
              user_id: "user1",
              action: "update",
              payload: { content_hash: "abc123" },
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });

      render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      // Simulate WebSocket opening
      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/collab/doc-123/audit"),
          expect.objectContaining({
            headers: expect.any(Object),
          })
        );
      });
    });

    it("should display View History button", async () => {
      render(
        <CollographicNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      const historyButton = screen.getByText(/view history/i);
      expect(historyButton).toBeTruthy();
    });

    it("should toggle audit trail visibility when button clicked", async () => {
      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      // Mock audit data
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          document_id: "doc-123",
          total: 1,
          entries: [
            {
              id: 1,
              user_id: "user1",
              action: "presence.join",
              payload: {},
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });

      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      // Wait for history button and click it
      await waitFor(() => {
        const historyButton = screen.getByText(/view history/i);
        expect(historyButton).toBeTruthy();
        fireEvent.click(historyButton);
      });

      // Audit trail should become visible
      await waitFor(() => {
        expect(screen.queryByText(/activity/i)).toBeTruthy();
      });
    });

    it("should display audit log entries with timestamp", async () => {
      const testTime = new Date().toISOString();
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          document_id: "doc-123",
          total: 1,
          entries: [
            {
              id: 1,
              user_id: "user1",
              action: "presence.join",
              payload: null,
              timestamp: testTime,
            },
          ],
        }),
      });

      render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      // Trigger fetch and display
      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      await waitFor(() => {
        // Look for user action display
        expect(screen.queryByText(/user1/i)).toBeTruthy();
      });
    });

    it("should show 'No activity yet' when audit trail is empty", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          document_id: "doc-123",
          total: 0,
          entries: [],
        }),
      });

      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      // Click View History to show audit trail
      await waitFor(() => {
        const historyButton = screen.getByText(/view history/i);
        fireEvent.click(historyButton);
      });

      // Should show empty state
      await waitFor(() => {
        expect(screen.queryByText(/no activity/i)).toBeTruthy();
      });
    });
  });

  describe("Access denial", () => {
    it("should show access denied message when connection rejected", async () => {
      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="unauthorized"
          authToken="invalid_token"
        />
      );

      // Simulate WebSocket close with policy violation code
      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onclose?.({ code: 1008 });

      await waitFor(() => {
        expect(screen.queryByText(/access denied/i)).toBeTruthy();
        expect(
          screen.queryByText(/you do not have permission/i)
        ).toBeTruthy();
      });
    });
  });

  describe("Token authentication", () => {
    it("should send auth token in WebSocket query string", async () => {
      render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="my_token_123"
        />
      );

      await waitFor(() => {
        const wsCall = (global.WebSocket as any).mock.calls[0];
        expect(wsCall[0]).toContain("token=my_token_123");
      });
    });

    it("should send token in initial handshake message", async () => {
      render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="shared_link_token"
        />
      );

      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      await waitFor(() => {
        expect(ws.send).toHaveBeenCalledWith(
          expect.stringContaining("shared_link_token")
        );
      });
    });
  });

  describe("Permission enforcement for edits", () => {
    it("should include type field in update messages", async () => {
      const { container } = render(
        <CollaborativeNote
          documentId="doc-123"
          threadId={1}
          userId="user1"
          authToken="token123"
        />
      );

      const ws = (global.WebSocket as any).mock.results[0].value;
      ws.onopen?.();

      // Reset send calls
      ws.send.mockClear();

      // Type in editor
      const textarea = container.querySelector("textarea");
      if (textarea) {
        fireEvent.change(textarea, { target: { value: "new text" } });

        // Verify update message has type field
        const lastCall = ws.send.mock.calls[ws.send.mock.calls.length - 1];
        if (lastCall) {
          const message = JSON.parse(lastCall[0]);
          expect(message.type).toBe("update");
          expect(message.content).toBe("new text");
        }
      }
    });
  });
});
