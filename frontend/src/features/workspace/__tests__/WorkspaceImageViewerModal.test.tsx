import React, { useRef, useState } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import WorkspaceImageViewerModal from "../components/WorkspaceImageViewerModal";
import type { WorkspaceImageRecord } from "../workspaceSelection";

const image: WorkspaceImageRecord = {
  id: "lightbox-image",
  filename: "field-map.png",
  src_url: "/media/images/field-map.png",
};

function ModalHarness({ initialZoom = 150 }: { initialZoom?: number }) {
  const [open, setOpen] = useState(false);
  const [zoom, setZoom] = useState(initialZoom);
  const expandRef = useRef<HTMLButtonElement>(null);

  return (
    <div>
      <button ref={expandRef} type="button" onClick={() => setOpen(true)}>
        Expand from Inspector
      </button>
      <p data-testid="selected-image">Selected: {image.filename}</p>
      {open && (
        <WorkspaceImageViewerModal
          image={image}
          zoom={zoom}
          onZoomChange={setZoom}
          onClose={() => setOpen(false)}
          returnFocusRef={expandRef}
        />
      )}
    </div>
  );
}

describe("WorkspaceImageViewerModal", () => {
  afterEach(() => cleanup());

  it("portals a viewport-level accessible dialog and restores focus on explicit close", async () => {
    const user = userEvent.setup();
    render(<ModalHarness />);

    await user.click(screen.getByRole("button", { name: "Expand from Inspector" }));
    const dialog = screen.getByRole("dialog", { name: "field-map.png" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog.parentElement?.parentElement).toBe(document.body);
    expect(screen.getByTestId("workspace-image-lightbox-backdrop")).toHaveStyle({
      zIndex: "10000",
    });
    expect(document.activeElement).toBe(
      within(dialog).getByRole("button", { name: "Close image viewer" })
    );

    await user.click(within(dialog).getByRole("button", { name: "Close image viewer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Expand from Inspector" })
    );
    expect(screen.getByTestId("selected-image")).toHaveTextContent("field-map.png");
  });

  it("traps keyboard focus and closes with Escape", async () => {
    const user = userEvent.setup();
    render(<ModalHarness />);

    await user.click(screen.getByRole("button", { name: "Expand from Inspector" }));
    const dialog = screen.getByRole("dialog", { name: "field-map.png" });
    const zoomOut = within(dialog).getByRole("button", { name: "Zoom out" });
    const close = within(dialog).getByRole("button", { name: "Close image viewer" });

    await user.tab();
    expect(document.activeElement).toBe(zoomOut);
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(close);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Expand from Inspector" })
    );
  });

  it("keeps the expanded image scrollable and enforces the shared zoom bounds", async () => {
    const user = userEvent.setup();
    render(<ModalHarness initialZoom={400} />);

    await user.click(screen.getByRole("button", { name: "Expand from Inspector" }));
    const dialog = screen.getByRole("dialog", { name: "field-map.png" });
    expect(within(dialog).getByTestId("workspace-image-lightbox-viewport")).toHaveClass(
      "overflow-auto"
    );
    expect(within(dialog).getByTestId("workspace-image-zoom")).toHaveTextContent("400%");
    expect(within(dialog).getByRole("button", { name: "Zoom in" })).toBeDisabled();

    const zoomOut = within(dialog).getByRole("button", { name: "Zoom out" });
    for (let count = 0; count < 14; count += 1) await user.click(zoomOut);
    expect(within(dialog).getByTestId("workspace-image-zoom")).toHaveTextContent("50%");
    expect(zoomOut).toBeDisabled();

    await user.click(within(dialog).getByRole("button", { name: "Reset / Fit" }));
    expect(within(dialog).getByTestId("workspace-image-zoom")).toHaveTextContent("100%");
  });

  it("keeps the dialog explained and closable if the expanded image fails", async () => {
    const user = userEvent.setup();
    render(<ModalHarness />);

    await user.click(screen.getByRole("button", { name: "Expand from Inspector" }));
    const dialog = screen.getByRole("dialog", { name: "field-map.png" });
    fireEvent.click(within(dialog).getByRole("img", { name: "field-map.png" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.error(within(dialog).getByRole("img", { name: "field-map.png" }));

    expect(within(dialog).getByRole("alert")).toHaveTextContent(/could not be loaded/i);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Close image viewer" }));
    expect(screen.getByTestId("selected-image")).toHaveTextContent("field-map.png");
  });
});
