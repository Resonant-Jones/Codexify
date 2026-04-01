import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceInspectorPanel from "../components/WorkspaceInspectorPanel";

describe("WorkspaceInspectorPanel", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("empty state", () => {
    it("shows empty state when no item is selected", () => {
      render(<WorkspaceInspectorPanel selectedItem={null} />);

      expect(
        screen.getByText(/Select a document from the Shelf to preview it here/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Phase 1 shell only/i)).toBeInTheDocument();
    });

    it("shows image preview not available message for image items", () => {
      const imageItem = {
        kind: "image" as const,
        item: {
          id: "img-1",
          src_url: "/media/images/img-1.png",
          filename: "test-image.png",
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={imageItem} />);

      expect(
        screen.getByText(/Image preview not yet available/i)
      ).toBeInTheDocument();
    });
  });

  describe("document preview", () => {
    it("renders document name when selected", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          filename: "test-document.pdf",
          src_url: "/media/documents/doc-1.pdf",
          mime_type: "application/pdf",
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText("test-document.pdf")).toBeInTheDocument();
    });

    it("renders document provenance when thread_id is available", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          filename: "thread-doc.pdf",
          src_url: "/media/documents/doc-1.pdf",
          thread_id: 123,
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText(/Thread #123/i)).toBeInTheDocument();
    });

    it("renders document provenance when project_id is available", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          filename: "project-doc.pdf",
          src_url: "/media/documents/doc-1.pdf",
          project_id: 7,
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText(/Project #7/i)).toBeInTheDocument();
    });

    it("renders file size when available", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          filename: "small-doc.pdf",
          src_url: "/media/documents/doc-1.pdf",
          filesize: 1024 * 50,
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText(/50.0 KB/i)).toBeInTheDocument();
    });

    it("renders mime type when available", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          filename: "doc.pdf",
          src_url: "/media/documents/doc-1.pdf",
          mime_type: "application/pdf",
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText("application/pdf")).toBeInTheDocument();
    });

    it("renders Untitled Document when filename is missing", () => {
      const docItem = {
        kind: "document" as const,
        item: {
          id: "doc-1",
          src_url: "/media/documents/doc-1.pdf",
        },
      };
      render(<WorkspaceInspectorPanel selectedItem={docItem} />);

      expect(screen.getByText("Untitled Document")).toBeInTheDocument();
    });
  });
});
