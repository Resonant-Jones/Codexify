import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MigrationModal from "./MigrationModal";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("MigrationModal", () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders migration modal header when open", () => {
    // Mock fetch to return a simple response
    mockFetch.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    });

    render(<MigrationModal open={true} onClose={() => {}} filePath="test.json" />);

    expect(screen.getByText(/ChatGPT.*Migration/i)).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<MigrationModal open={false} onClose={() => {}} filePath="test.json" />);

    expect(screen.queryByText(/ChatGPT.*Migration/i)).not.toBeInTheDocument();
  });

  it("shows initializing message when starting", () => {
    // Mock fetch to never resolve
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<MigrationModal open={true} onClose={() => {}} filePath="test.json" />);

    expect(screen.getByText(/Initializing migration/i)).toBeInTheDocument();
  });

  it("calls migration API endpoint with file path", async () => {
    const mockReader = {
      read: vi.fn().mockResolvedValueOnce({ done: true, value: undefined }),
    };

    mockFetch.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    render(<MigrationModal open={true} onClose={() => {}} filePath="/path/to/test.json" />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/migrate",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ filePath: "/path/to/test.json" }),
        })
      );
    });
  });

  it("displays success button when migration completes", async () => {
    const encoder = new TextEncoder();
    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode("✨ Migration complete\n"),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    };

    mockFetch.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    render(<MigrationModal open={true} onClose={() => {}} filePath="test.json" />);

    await waitFor(() => {
      expect(screen.getByText(/Welcome Home/i)).toBeInTheDocument();
    });
  });

  it("displays error button when migration fails", async () => {
    mockFetch.mockRejectedValue(new Error("Migration failed"));

    render(<MigrationModal open={true} onClose={() => {}} filePath="test.json" />);

    await waitFor(() => {
      expect(screen.getByText(/Close/i)).toBeInTheDocument();
    });
  });

  it("streams output lines as they arrive", async () => {
    const encoder = new TextEncoder();
    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode("Line 1\n"),
        })
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode("Line 2\n"),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    };

    mockFetch.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    render(<MigrationModal open={true} onClose={() => {}} filePath="test.json" />);

    await waitFor(() => {
      expect(screen.getByText("Line 1")).toBeInTheDocument();
      expect(screen.getByText("Line 2")).toBeInTheDocument();
    });
  });
});
