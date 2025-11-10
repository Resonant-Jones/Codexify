import { render, screen, waitFor } from "@testing-library/react";
import { SharePage } from "../SharePage";

describe("SharePage", () => {
  it("shows loading state initially", () => {
    const mockFetch = jest.fn(
      () =>
        new Promise((resolve) => {
          // Don't resolve to keep loading state
          setTimeout(() => {}, 10000);
        })
    );

    global.fetch = mockFetch;

    render(<SharePage token="test_token" />);
    expect(screen.getByText(/Loading shared content/)).toBeInTheDocument();
  });

  it("displays thread content", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "thread",
            target_id: 1,
            content: {
              id: 1,
              title: "Shared Thread",
              summary: "This is a summary",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
              messages: [
                {
                  id: 1,
                  role: "user",
                  content: "Hello",
                  created_at: "2025-01-01T10:00:00Z",
                },
                {
                  id: 2,
                  role: "assistant",
                  content: "Hi there!",
                  created_at: "2025-01-01T10:05:00Z",
                },
              ],
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="test_token" />);

    await waitFor(() => {
      expect(screen.getByText("Shared Thread")).toBeInTheDocument();
      expect(screen.getByText("This is a summary")).toBeInTheDocument();
      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });
  });

  it("displays document content", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "document",
            target_id: "doc-123",
            content: {
              id: "doc-123",
              title: "Shared Document",
              content: "Document content here",
              format: "md",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="doc_token" />);

    await waitFor(() => {
      expect(screen.getByText("Shared Document")).toBeInTheDocument();
      expect(screen.getByText("Document content here")).toBeInTheDocument();
    });
  });

  it("displays uploaded document info", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "document",
            target_id: "upload-456",
            content: {
              id: "upload-456",
              filename: "report.pdf",
              mime_type: "application/pdf",
              filesize: 51200,
              src_url: "http://example.com/report.pdf",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="upload_token" />);

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
      expect(screen.getByText("application/pdf")).toBeInTheDocument();
      expect(screen.getByText(/50\.00 KB/)).toBeInTheDocument();
      expect(screen.getByText("Download Document")).toBeInTheDocument();
    });
  });

  it("shows empty message when thread has no messages", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "thread",
            target_id: 2,
            content: {
              id: 2,
              title: "Empty Thread",
              summary: "",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
              messages: [],
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="empty_token" />);

    await waitFor(() => {
      expect(screen.getByText("Empty Thread")).toBeInTheDocument();
      expect(screen.getByText(/No messages in this thread/)).toBeInTheDocument();
    });
  });

  it("shows error on fetch failure", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Share link not found" }), {
          status: 404,
        })
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="invalid_token" />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to load shared content/)).toBeInTheDocument();
      expect(screen.getByText(/Share link not found/)).toBeInTheDocument();
    });
  });

  it("shows error on network failure", async () => {
    const mockFetch = jest.fn(() =>
      Promise.reject(new Error("Network error"))
    );

    global.fetch = mockFetch;

    render(<SharePage token="error_token" />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to load shared content/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it("calls correct endpoint with token", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "thread",
            target_id: 1,
            content: {
              id: 1,
              title: "Test",
              summary: "",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
              messages: [],
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="my_special_token" />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("/api/share/my_special_token");
    });
  });

  it("displays message role correctly", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            target_type: "thread",
            target_id: 1,
            content: {
              id: 1,
              title: "Role Test",
              summary: "",
              created_at: "2025-01-01T10:00:00Z",
              updated_at: "2025-01-02T10:00:00Z",
              messages: [
                {
                  id: 1,
                  role: "user",
                  content: "User message",
                  created_at: "2025-01-01T10:00:00Z",
                },
                {
                  id: 2,
                  role: "assistant",
                  content: "Assistant message",
                  created_at: "2025-01-01T10:05:00Z",
                },
              ],
            },
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    render(<SharePage token="role_token" />);

    await waitFor(() => {
      const userRole = screen.getAllByText("USER")[0];
      const assistantRole = screen.getAllByText("ASSISTANT")[0];

      expect(userRole).toBeInTheDocument();
      expect(assistantRole).toBeInTheDocument();
    });
  });
});
