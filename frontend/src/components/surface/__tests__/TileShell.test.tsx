import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TileShell, type TileShellSizeVariant } from "../TileShell";

describe("TileShell size variants", () => {
  it.each([
    ["document", "112px"],
    ["dashboard-image", "192px"],
    ["gallery-image", "256px"],
  ] as const)("keeps %s at %s square", (sizeVariant, size) => {
    const { container } = render(
      <TileShell sizeVariant={sizeVariant as TileShellSizeVariant}>Tile</TileShell>
    );
    const tile = container.firstElementChild as HTMLElement;
    expect(tile.style.getPropertyValue("--tile-size")).toBe(size);
    expect(tile.style.width).toBe("var(--tile-size)");
    expect(tile.style.height).toBe("var(--tile-size)");
  });
});
