import { describe, expect, it } from "vitest";
import { allocatePanels } from "./DockedPanelDivider";

describe("shell allocation", () => {
  it("fits exact two- and three-panel minima and removes the whole Sidepanel track one pixel below", () => {
    for (const [workspace, threshold] of [[false, 696], [true, 1028]] as const) {
      const at = allocatePanels(threshold, true, true, workspace, 470, 600);
      expect(at.side).toBe(300);
      expect(at.work).toBe(workspace ? 320 : 0);
      const below = allocatePanels(threshold - 1, true, true, workspace, 470, 600);
      expect(below.fitsSidebar).toBe(false);
      expect(below.side).toBe(0);
    }
  });

  it("keeps drawer and closed sidepanels out of the allocation", () => {
    expect(allocatePanels(1400, false, true, true, 330, 400).side).toBe(0);
    expect(allocatePanels(1400, true, false, true, 330, 400)).toMatchObject({ side: 0, work: 400 });
  });
});
