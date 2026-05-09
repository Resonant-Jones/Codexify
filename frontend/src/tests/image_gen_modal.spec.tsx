import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImageGenModal } from "@/components/modals/ImageGenModal";

describe("ImageGenModal", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/");
    vi.restoreAllMocks();
  });

  it("renders the beta gate shell instead of the prompt form", () => {
    const onOpenChange = vi.fn();

    render(<ImageGenModal open onOpenChange={onOpenChange} />);

    expect(screen.getByRole("heading", { name: "Image Generation" })).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/prompt/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate/i })).toBeDisabled();
  });

  it("can be dismissed from the beta gate shell", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    render(<ImageGenModal open onOpenChange={onOpenChange} />);

    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
