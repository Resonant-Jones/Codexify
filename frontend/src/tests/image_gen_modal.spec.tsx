import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImageGenModal } from "@/components/modals/ImageGenModal";
import api from "@/lib/api";


describe("ImageGenModal", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts to the image generation endpoint and closes on success", async () => {
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
          project_id: 1,
          thread_id: 1,
          user_id: "default",
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
});
