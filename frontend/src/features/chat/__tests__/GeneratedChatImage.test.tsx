import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { GeneratedChatImage } from "../components/GeneratedChatImage";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn() } }));
vi.mock("@/hooks/useRenderableMediaSrc", () => ({
  useRenderableMediaSrc: (src: string) => ({ src, status: src ? "ready" : "idle" }),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("reloads by durable id and opens a newly signed image", async () => {
  vi.mocked(api.get).mockResolvedValue({
    data: {
      id: "saved-image",
      src_url: "/media/fox.png?fresh-signature",
      prompt: "A fox",
      model: "sunburst",
    },
  });
  render(<GeneratedChatImage id="saved-image" />);
  const button = await screen.findByRole("button", { name: "Open generated image" });
  expect(api.get).toHaveBeenCalledWith("/api/media/generated-images/saved-image");
  expect(screen.getByRole("img", { name: "A fox" })).toHaveAttribute(
    "src",
    expect.stringContaining("fresh-signature")
  );
  fireEvent.click(button);
  expect(await screen.findByRole("dialog")).toBeVisible();
  expect(screen.getByRole("button", { name: "Zoom in" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Close image viewer" }));
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("handles access refusal without rendering another account's image", async () => {
  vi.mocked(api.get).mockRejectedValue(new Error("Forbidden"));
  render(<GeneratedChatImage id="private-image" />);
  expect(await screen.findByText("Image unavailable")).toBeVisible();
  expect(screen.queryByRole("img")).toBeNull();
});
