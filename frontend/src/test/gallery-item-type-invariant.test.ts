import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("Gallery item type invariants", () => {
  it("owns the renderable gallery item type outside any component", () => {
    const source = readFileSync(resolve(process.cwd(), "types/gallery.ts"), "utf8");

    expect(source).toContain("export type GalleryItem = {");
  });

  it("keeps the gallery grid and Library off the GalleryView component", () => {
    for (const path of [
      "components/gallery/GalleryGrid.tsx",
      "components/library/LibraryView.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), path), "utf8");

      expect(source).not.toContain("gallery/GalleryView");
      expect(source).toContain("types/gallery");
    }
  });

  it("no longer publishes the gallery item type from the GalleryView component", () => {
    const source = readFileSync(
      resolve(process.cwd(), "components/gallery/GalleryView.tsx"),
      "utf8"
    );

    expect(source).not.toContain("export type GalleryItem");
    expect(source).toContain("types/gallery");
  });
});
