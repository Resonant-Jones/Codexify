import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceShelfPanel from "../components/WorkspaceShelfPanel";

vi.mock("@/components/ui/PreviewTile", () => ({
  default: ({
    children,
    onClick,
    className,
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    className?: string;
  }) => (
    <button type="button" className={className} onClick={onClick}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/documents/DocumentTile", () => ({
  default: ({
    file,
    onClick,
  }: {
    file: { name?: string; ext?: string };
    onClick?: () => void;
  }) => (
    <button type="button" onClick={onClick} data-testid="document-tile">
      {file?.name || "Untitled"}
    </button>
  ),
}));

function mockFetch(data: unknown) {
  const response = {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  } as Response;
  return vi.fn().mockResolvedValue(response);
}

describe("WorkspaceShelfPanel", () => {
  let globalFetch: jest.Mock;

  beforeEach(() => {
    globalFetch = mockFetch({ documents: [], images: [] });
    vi.stubGlobal("fetch", globalFetch);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("empty states", () => {
    it("shows empty state when neither threadId nor projectId is provided", async () => {
      const user = userEvent.setup();
      render(<WorkspaceShelfPanel threadIdentity={null} projectId={null} />);

      expect(
        await screen.findByText(/Select a thread or project to see linked items/i)
      ).toBeInTheDocument();
    });

    it("shows loading then empty when thread has no items", async () => {
      const user = userEvent.setup();
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ documents: [], images: [] }),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ documents: [], images: [] }),
      });

      render(<WorkspaceShelfPanel threadIdentity="123" projectId={null} />);

      expect(screen.getByTestId("workspace-shelf-status")).toHaveTextContent(
        /loading/i
      );

      expect(
        await screen.findByText(/No items linked to this context yet/i)
      ).toBeInTheDocument();
    });

    it("shows offline message when fetch fails", async () => {
      const user = userEvent.setup();
      globalFetch.mockRejectedValueOnce(new Error("Network error"));

      render(<WorkspaceShelfPanel threadIdentity="123" projectId={null} />);

      expect(
        await screen.findByText(/Failed to load shelf/i)
      ).toBeInTheDocument();
    });
  });

  describe("thread-linked items", () => {
    it("renders thread documents when available", async () => {
      const user = userEvent.setup();
      const threadDocs = {
        documents: [
          {
            id: "doc-1",
            filename: "thread-doc.pdf",
            src_url: "/media/documents/doc-1.pdf",
            mime_type: "application/pdf",
            thread_id: 123,
          },
        ],
        images: [],
      };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadDocs),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] }),
      });

      render(<WorkspaceShelfPanel threadIdentity="123" projectId={null} />);

      expect(await screen.findByTestId("workspace-shelf-thread-label")).toHaveTextContent(
        /thread/i
      );
      expect(screen.getByText("thread-doc.pdf")).toBeInTheDocument();
    });

    it("renders thread images when available", async () => {
      const threadImgs = {
        images: [
          {
            id: "img-1",
            filename: "thread-img.png",
            src_url: "/media/images/img-1.png",
            thread_id: 123,
          },
        ],
        documents: [],
      };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ documents: [] }),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadImgs),
      });

      render(<WorkspaceShelfPanel threadIdentity="123" projectId={null} />);

      expect(await screen.findByTestId("workspace-shelf-thread-label")).toHaveTextContent(
        /thread/i
      );
      expect(screen.getByText("thread-img.png")).toBeInTheDocument();
    });
  });

  describe("project-linked items", () => {
    it("renders project documents when available (no thread id)", async () => {
      const projectDocs = {
        documents: [
          {
            id: "doc-p1",
            filename: "project-doc.pdf",
            src_url: "/media/documents/doc-p1.pdf",
            mime_type: "application/pdf",
            project_id: 7,
          },
        ],
        images: [],
      };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(projectDocs),
      });

      render(<WorkspaceShelfPanel threadIdentity={null} projectId="7" />);

      expect(await screen.findByTestId("workspace-shelf-project-label")).toHaveTextContent(
        /project/i
      );
      expect(screen.getByText("project-doc.pdf")).toBeInTheDocument();
    });
  });

  describe("both thread and project items", () => {
    it("renders both thread and project sections when both have items", async () => {
      const threadDocs = {
        documents: [
          {
            id: "doc-t1",
            filename: "thread-doc.pdf",
            src_url: "/media/documents/doc-t1.pdf",
            thread_id: 123,
          },
        ],
        images: [],
      };
      const projectDocs = {
        documents: [
          {
            id: "doc-p1",
            filename: "project-doc.pdf",
            src_url: "/media/documents/doc-p1.pdf",
            project_id: 7,
          },
        ],
        images: [],
      };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadDocs),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] }),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(projectDocs),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ images: [] }),
      });

      render(<WorkspaceShelfPanel threadIdentity="123" projectId="7" />);

      expect(await screen.findByTestId("workspace-shelf-thread-label")).toHaveTextContent(
        /thread/i
      );
      expect(screen.getByTestId("workspace-shelf-project-label")).toHaveTextContent(
        /project/i
      );
      expect(screen.getByText("thread-doc.pdf")).toBeInTheDocument();
      expect(screen.getByText("project-doc.pdf")).toBeInTheDocument();
    });
  });

  describe("status display", () => {
    it("shows accurate count of docs and images", async () => {
      const threadDocs = {
        documents: [
          { id: "doc-1", filename: "doc1.pdf", src_url: "/media/documents/doc-1.pdf" },
          { id: "doc-2", filename: "doc2.pdf", src_url: "/media/documents/doc-2.pdf" },
        ],
        images: [],
      };
      const threadImgs = {
        images: [
          { id: "img-1", filename: "img1.png", src_url: "/media/images/img-1.png" },
        ],
      };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadDocs),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadImgs),
      });

      render(<WorkspaceShelfPanel threadIdentity="123" projectId={null} />);

      const status = await screen.findByTestId("workspace-shelf-status");
      expect(status).toHaveTextContent(/2 docs · 1 images/i);
    });
  });

  describe("item interaction", () => {
    it("calls onItemClick with document item when clicked", async () => {
      const user = userEvent.setup();
      const threadDocs = {
        documents: [
          {
            id: "doc-1",
            filename: "thread-doc.pdf",
            src_url: "/media/documents/doc-1.pdf",
            mime_type: "application/pdf",
          },
        ],
        images: [],
      };
      const threadImgs = { images: [] };

      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadDocs),
      });
      globalFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(threadImgs),
      });

      const onItemClick = vi.fn();
      render(
        <WorkspaceShelfPanel
          threadIdentity="123"
          projectId={null}
          onItemClick={onItemClick}
        />
      );

      await user.click(await screen.findByText("thread-doc.pdf"));

      expect(onItemClick).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: "document",
          item: expect.objectContaining({ id: "doc-1" }),
        })
      );
    });
  });
});
