import React from "react";
import { act, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InMemorySessionStateStore } from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";
import {
  useSessionActiveModelId,
  useSessionRailSlice,
} from "@/state/session/hooks";

function SelectorHarness({
  spine,
  counts,
}: {
  spine: SessionSpine;
  counts: {
    rail: number;
    model: number;
  };
}) {
  const rail = useSessionRailSlice(spine);
  const activeModel = useSessionActiveModelId(spine, "default");

  counts.rail += 1;
  counts.model += 1;

  return (
    <div>
      <span>{rail.tabs.length}</span>
      <span>{rail.activeTabId}</span>
      <span>{activeModel}</span>
    </div>
  );
}

describe("session selectors", () => {
  it("do not trigger rail/model rerenders for draft-only updates", async () => {
    const store = new InMemorySessionStateStore();
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });
    await spine.hydrate({ threadId: "101", title: "Alpha", modelId: "default" });

    const active = spine.getActiveTab();
    if (!active) throw new Error("Expected active tab");

    const counts = { rail: 0, model: 0 };
    render(<SelectorHarness spine={spine} counts={counts} />);

    const initialRailRenders = counts.rail;
    const initialModelRenders = counts.model;

    act(() => {
      spine.tabSetDraft(active.tabId, "h");
      spine.tabSetDraft(active.tabId, "he");
      spine.tabSetDraft(active.tabId, "hel");
    });

    expect(counts.rail).toBe(initialRailRenders);
    expect(counts.model).toBe(initialModelRenders);

    act(() => {
      spine.tabSetModel(active.tabId, "gpt-oss");
    });

    expect(counts.rail).toBeGreaterThan(initialRailRenders);
    expect(counts.model).toBeGreaterThan(initialModelRenders);
  });
});
