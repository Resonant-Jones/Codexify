import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
});
