import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { serializeDocumentContextMessage } from "@/lib/documentContext";

const runtimeState = vi.hoisted(() => ({
  invokeTauriCommandMock: vi.fn(),
  tauriRuntime: false,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: runtimeState.tauriRuntime ? "tauri" : "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => runtimeState.tauriRuntime,
  invokeTauriCommand: runtimeState.invokeTauriCommandMock,
}));

import ChatBubble from "@/features/chat/components/ChatBubble";

describe("ChatBubble", () => {
  afterEach(() => {
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
    vi.restoreAllMocks();
  });

  it("uses the desktop media fetch contract for backend-owned attachment images in Tauri", async () => {
    runtimeState.tauriRuntime = true;
    runtimeState.invokeTauriCommandMock.mockResolvedValue({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:chat-image"),
    });

    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-tauri-attachment",
          authorId: "bot",
          authorName: "Guardian",
          content: "",
          createdAt: Date.now(),
          attachments: [
            {
              id: "img-tauri-1",
              kind: "image",
              src: "/media/images/chat-tauri.jpg?sig=tile#preview",
              name: "chat-tauri.jpg",
            },
          ],
        }}
      />
    );

    const image = await screen.findByRole("img", { name: "uploaded image" });
    expect(image).toHaveAttribute("src", "blob:chat-image");
    expect(runtimeState.invokeTauriCommandMock).toHaveBeenCalledWith(
      "desktop_fetch_media",
      { path: "/media/images/chat-tauri.jpg" }
    );
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
  });

  it("hides malformed timestamps instead of rendering Invalid Date", () => {
    render(
      <ChatBubble
        isGuardian={false}
        message={{
          id: "msg-1",
          authorId: "me",
          authorName: "You",
          content: "Hello world",
          createdAt: Number.NaN,
        }}
      />
    );

    expect(screen.getByText("Hello world")).toBeInTheDocument();
    expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument();
  });

  it("renders attachment tiles with normalized image URLs", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-2",
          authorId: "bot",
          authorName: "Guardian",
          content: "",
          createdAt: Date.now(),
          attachments: [
            {
              id: "img-1",
              kind: "image",
              src: "/media/images/chat-tile.jpg?sig=tile#preview",
              name: "chat-tile.jpg",
            },
          ],
        }}
      />
    );

    expect(screen.getByRole("img", { name: "uploaded image" })).toHaveAttribute(
      "src",
      "http://backend.test/media/images/chat-tile.jpg?sig=tile#preview"
    );
  });

  it("renders assistant markdown images from relative /media sources", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-3",
          authorId: "bot",
          authorName: "Guardian",
          content: "![Chat image](/media/images/chat-inline.jpg?sig=inline#viewer)",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByRole("img", { name: "Chat image" })).toHaveAttribute(
      "src",
      "http://backend.test/media/images/chat-inline.jpg?sig=inline#viewer"
    );
  });

  it("renders assistant markdown images from relative media sources without a leading slash", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-4",
          authorId: "bot",
          authorName: "Guardian",
          content: "![Relative chat image](media/images/chat-inline-2.jpg?sig=inline2#viewer)",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByRole("img", { name: "Relative chat image" })).toHaveAttribute(
      "src",
      "http://backend.test/media/images/chat-inline-2.jpg?sig=inline2#viewer"
    );
  });

  it("leaves external assistant markdown image URLs untouched", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-5",
          authorId: "bot",
          authorName: "Guardian",
          content: "![External image](https://cdn.example.com/image.jpg?x=1#hero)",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByRole("img", { name: "External image" })).toHaveAttribute(
      "src",
      "https://cdn.example.com/image.jpg?x=1#hero"
    );
  });

  it("renders assistant fenced code blocks with rich code UI", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-6",
          authorId: "bot",
          authorName: "Guardian",
          content: "```ts\nconst total = 1;\n```",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(screen.getByText("TS")).toBeInTheDocument();
    expect(screen.getByText("const total = 1;")).toBeInTheDocument();
  });

  it("keeps long assistant content and code blocks bounded on phone shells", () => {
    const longToken = "a".repeat(160);

    const { container } = render(
      <ChatBubble
        isGuardian
        isPhoneShell
        message={{
          id: "msg-phone-wrap",
          authorId: "bot",
          authorName: "Guardian",
          content: `Phone-safe wrap token: ${longToken}\n\n\`\`\`ts\nconst payload = "${longToken}";\n\`\`\``,
          createdAt: Date.now(),
        }}
      />
    );

    const prose = container.querySelector(".prose");
    expect(prose).toHaveStyle({
      overflowWrap: "anywhere",
      wordBreak: "break-word",
    });
    expect(container.querySelector(".codexifyCodeBlock")).toHaveClass(
      "max-w-full",
      "min-w-0"
    );
    expect(container.querySelector(".codexifyCodeBlockPre")).toBeInTheDocument();
  });

  it("normalizes TeX-style arrows in assistant prose without breaking markdown", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-6b",
          authorId: "bot",
          authorName: "Guardian",
          content:
            "**Bold intro**\n\n- First item\n- Second item\n\nUser engages with Persona $\\rightarrow$ User transforms $\\rightarrow$ Project advances",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByText("Bold intro")).toBeInTheDocument();
    expect(screen.getByText("First item")).toBeInTheDocument();
    expect(screen.getByText("Second item")).toBeInTheDocument();
    expect(
      screen.getByText(
        "User engages with Persona → User transforms → Project advances"
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/\\rightarrow/)).not.toBeInTheDocument();
  });

  it("leaves inline and fenced code untouched while normalizing prose arrows", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          id: "msg-6c",
          authorId: "bot",
          authorName: "Guardian",
          content:
            "Normal prose: $\\rightarrow$\n\nInline code: `$\\rightarrow$`\n\n```txt\nconst arrow = \"$\\rightarrow$\";\n```",
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByText("Normal prose: →")).toBeInTheDocument();
    expect(screen.getByText("$\\rightarrow$", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByText('const arrow = "$\\rightarrow$";')).toBeInTheDocument();
  });

  it("renders user multiline code as plaintext without copy affordances", () => {
    const pastedCode = "function demo() {\n  const total = 1;\n  return total;\n}";

    const { container } = render(
      <ChatBubble
        isGuardian={false}
        message={{
          id: "msg-7",
          authorId: "me",
          authorName: "You",
          content: pastedCode,
          createdAt: Date.now(),
        }}
      />
    );

    const plainText = container.querySelector(".whitespace-pre-wrap");
    expect(plainText).not.toBeNull();
    expect(plainText?.textContent).toBe(pastedCode);
    expect(screen.queryByRole("button", { name: "Copy" })).not.toBeInTheDocument();
    expect(container.querySelector(".codexifyCodeBlock")).not.toBeInTheDocument();
  });

  it("centers user message text within the bubble", () => {
    const centeredText = `Centered user message ${"x".repeat(1300)}`;
    const { container } = render(
      <ChatBubble
        isGuardian={false}
        message={{
          id: "msg-center-user",
          authorId: "me",
          authorName: "You",
          content: centeredText,
          createdAt: Date.now(),
        }}
      />
    );

    const content = container.querySelector(
      '[data-testid="guardian-user-message-content"]'
    );
    expect(content).toHaveClass("text-center");
  });

  it("renders document tiles inline without exposing the full document body", () => {
    const content = serializeDocumentContextMessage("Please review", [
      {
        tile: {
          id: "doc-1",
          title: "Project Brief",
          preview: "Short excerpt",
          type: "document",
        },
        content: "Full document body",
      },
    ]);

    render(
      <ChatBubble
        isGuardian={false}
        message={{
          id: "msg-doc-tile",
          authorId: "me",
          authorName: "You",
          content,
          createdAt: Date.now(),
        }}
      />
    );

    expect(screen.getByTestId("document-context-tile")).toBeInTheDocument();
    expect(screen.getByText("Please review")).toBeInTheDocument();
    expect(screen.queryByText("Full document body")).not.toBeInTheDocument();
  });
});
