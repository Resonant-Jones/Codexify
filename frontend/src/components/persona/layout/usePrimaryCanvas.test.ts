import { act, renderHook } from "@testing-library/react";
import { expect, it } from "vitest";
import type { WorkspaceLayoutMode } from "@/features/workspace/state/useWorkspaceLayoutMode";
import { usePrimaryCanvas } from "./usePrimaryCanvas";

it("holds one automatic winner across edge jitter and honors an explicit per-thread mode first", () => {
  const initialProps = { width: 1000, scope: "a", mode: null as WorkspaceLayoutMode | null };
  const { result, rerender } = renderHook(({ width, scope, mode }) => usePrimaryCanvas(true, width, scope, mode), { initialProps });
  act(() => result.current.recordUse("workspace"));
  rerender({ ...initialProps, width: 715 });
  expect(result.current.pane).toBe("workspace");
  act(() => result.current.recordUse("chat"));
  for (const width of [716, 710, 727]) {
    rerender({ ...initialProps, width });
    expect(result.current.pane).toBe("workspace");
  }
  rerender({ ...initialProps, width: 728 });
  expect(result.current.pane).toBeNull();
  rerender({ ...initialProps, width: 702, mode: "workspace_focus" });
  expect(result.current.pane).toBe("workspace");
  rerender({ ...initialProps, width: 1300, mode: "workspace_focus" });
  expect(result.current.pane).toBe("workspace");
  rerender({ ...initialProps, width: 710, scope: "b" });
  expect(result.current.pane).toBe("chat");
});
