import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ShareButton } from "../ShareButton";

describe("ShareButton", () => {
  beforeEach(() => {
    // Reset window.location.origin
    delete (window as any).location;
    (window as any).location = { origin: "http://localhost:3000" };
  });

  it("renders share button", () => {
    render(<ShareButton targetType="thread" targetId={1} />);
    const button = screen.getByRole("button", { name: /share/i });
    expect(button).toBeInTheDocument();
    expect(button).not.toBeDisabled();
  });

  it("disables button while loading", async () => {
    const mockFetch = jest.fn(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve(
                new Response(
                  JSON.stringify({
                    ok: true,
                    token: "test_token",
                    url: "/share/test_token",
                  }),
                  { status: 200 }
                )
              ),
            100
          )
        )
    );

    global.fetch = mockFetch;

    render(<ShareButton targetType="thread" targetId={1} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Creating...");

    await waitFor(() => {
      expect(button).not.toBeDisabled();
      expect(button).toHaveTextContent("Share");
    });
  });

  it("sends correct request for thread", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            token: "test_token",
            url: "/share/test_token",
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(() => Promise.resolve()),
      },
    });

    render(<ShareButton targetType="thread" targetId={42} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("/api/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: "thread",
          target_id: 42,
        }),
        credentials: "include",
      });
    });
  });

  it("sends correct request for document", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            token: "doc_token",
            url: "/share/doc_token",
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(() => Promise.resolve()),
      },
    });

    render(<ShareButton targetType="document" targetId={99} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("/api/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: "document",
          target_id: 99,
        }),
        credentials: "include",
      });
    });
  });

  it("copies link to clipboard", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            token: "test_token",
            url: "/share/test_token",
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    const mockClipboard = jest.fn(() => Promise.resolve());
    Object.assign(navigator, {
      clipboard: {
        writeText: mockClipboard,
      },
    });

    render(<ShareButton targetType="thread" targetId={1} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);

    await waitFor(() => {
      expect(mockClipboard).toHaveBeenCalledWith(
        "http://localhost:3000/share/test_token"
      );
    });
  });

  it("shows success toast on successful share", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: true,
            token: "test_token",
            url: "/share/test_token",
          }),
          { status: 200 }
        )
      )
    );

    global.fetch = mockFetch;

    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(() => Promise.resolve()),
      },
    });

    render(<ShareButton targetType="thread" targetId={1} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);

    await waitFor(() => {
      expect(
        screen.getByText(/http:\/\/localhost:3000\/share\/test_token/)
      ).toBeInTheDocument();
    });
  });

  it("shows error toast on failure", async () => {
    const mockFetch = jest.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Thread not found" }), {
          status: 404,
        })
      )
    );

    global.fetch = mockFetch;

    render(<ShareButton targetType="thread" targetId={999} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Failed to create share link/)).toBeInTheDocument();
    });
  });
});
