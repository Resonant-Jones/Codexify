import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DocumentGenModal } from "@/components/DocumentGenModal";


describe("DocumentGenModal", () => {
  it("submits captured inputs", async () => {
    const handleOpen = vi.fn();
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <DocumentGenModal
        open
        onOpenChange={handleOpen}
        onSubmit={handleSubmit}
      />
    );

    await user.type(screen.getByLabelText(/title/i), "Launch Brief");
    await user.type(
      screen.getByLabelText(/prompt/i),
      "Draft a launch overview.  "
    );
    await user.selectOptions(screen.getByLabelText(/output format/i), "plain");

    await user.click(screen.getByRole("button", { name: /save draft/i }));

    expect(handleSubmit).toHaveBeenCalledWith({
      title: "Launch Brief",
      prompt: "Draft a launch overview.",
      format: "plain",
    });
    expect(handleOpen).toHaveBeenCalledWith(false);
  });

  it("closes on cancel", async () => {
    const handleOpen = vi.fn();
    const user = userEvent.setup();

    render(
      <DocumentGenModal
        open
        onOpenChange={handleOpen}
        onSubmit={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(handleOpen).toHaveBeenCalledWith(false);
  });

  it("requires a prompt", async () => {
    const handleOpen = vi.fn();
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <DocumentGenModal
        open
        onOpenChange={handleOpen}
        onSubmit={handleSubmit}
      />
    );

    await user.click(screen.getByRole("button", { name: /save draft/i }));
    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/prompt is required/i)).toBeInTheDocument();
  });
});
