import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImageGenModal } from "@/components/modals/ImageGenModal";
import api from "@/lib/api";


describe("ImageGenModal", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/");
    vi.restoreAllMocks();
  });

  it("posts to the image generation endpoint using explicit scope context", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onImageGenerated = vi.fn();

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: { src_url: "https://example.com/image.png" },
    } as AxiosResponse);

    render(
      <ImageGenModal
        open
        onOpenChange={onOpenChange}
        onImageGenerated={onImageGenerated}
        projectId={42}
        threadId={99}
        userId="user-42"
      />
    );

    await user.type(screen.getByLabelText(/prompt/i), "  neon city  ");
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith(
        "/api/media/generate/image",
        expect.objectContaining({
          prompt: "neon city",
          model: "dall-e-3",
          project_id: 42,
          thread_id: 99,
          user_id: "user-42",
        })
      );
    });

    await waitFor(() => {
      expect(onImageGenerated).toHaveBeenCalledWith(
        "https://example.com/image.png"
      );
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("derives scope context from active thread route and persisted project scope", async () => {
    window.localStorage.setItem("cfy.lastProjectId", "7");
    window.history.replaceState({}, "", "/chat/123");

    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: { src_url: "https://example.com/image.png" },
    } as AxiosResponse);

    render(<ImageGenModal open onOpenChange={onOpenChange} />);

    await user.type(screen.getByLabelText(/prompt/i), " scoped skyline ");
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith(
        "/api/media/generate/image",
        expect.objectContaining({
          prompt: "scoped skyline",
          project_id: 7,
          thread_id: 123,
          user_id: "default",
        })
      );
    });

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
