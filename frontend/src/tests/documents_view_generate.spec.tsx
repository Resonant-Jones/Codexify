import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
  it("renders the upload affordance instead of the deprecated generate action", () => {
    render(<DocumentsView documents={[]} extColors={EXT_COLORS} />);

    expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /choose files/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /generate document/i })).not.toBeInTheDocument();
  });
});
