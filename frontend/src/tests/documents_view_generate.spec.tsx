import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentsView from "@/components/documents/DocumentsView";
import type { ExtColors } from "@/types/ui";


const EXT_COLORS: ExtColors = {
  pdf: "#111111",
  doc: "#111111",
  md: "#111111",
  png: "#111111",
  sketch: "#111111",
  txt: "#111111",
  docx: "#111111",
  jpeg: "#111111",
  codex: "#111111",
};

describe("DocumentsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("dispatches a generate document event", async () => {
    const user = userEvent.setup();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<DocumentsView documents={[]} extColors={EXT_COLORS} />);

    await user.click(
      screen.getByRole("button", { name: /generate document/i })
    );

    const fired = dispatchSpy.mock.calls.some(
      ([event]) => (event as Event).type === "cfy:documents:generate"
    );
    expect(fired).toBe(true);
  });
});
