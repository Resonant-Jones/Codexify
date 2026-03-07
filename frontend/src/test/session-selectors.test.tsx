import React from "react";
import { act, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InMemorySessionStateStore } from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";
import {
  useSessionActiveDraft,
  useSessionActiveModelId,
  useSessionRailSlice,
} from "@/state/session/hooks";

function RailHarness({
  spine,
  countRef,
}: {
  spine: SessionSpine;
  countRef: { current: number };
}) {
  const rail = useSessionRailSlice(spine);
  countRef.current += 1;

  return (
    <div data-testid="rail-harness">
      <span>{rail.tabs.length}</span>
      <span>{rail.activeTabId}</span>
    </div>
  );
}

function ModelHarness({
  spine,
  countRef,
}: {
  spine: SessionSpine;
  countRef: { current: number };
}) {
  const activeModel = useSessionActiveModelId(spine, "default");
  countRef.current += 1;
  return <div data-testid="model-harness">{activeModel}</div>;
}

function DraftHarness({
  spine,
  countRef,
}: {
  spine: SessionSpine;
  countRef: { current: number };
}) {
  const activeDraft = useSessionActiveDraft(spine);
  countRef.current += 1;
  return <div data-testid="draft-harness">{activeDraft}</div>;
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

    const railRenders = { current: 0 };
    const modelRenders = { current: 0 };
    const draftRenders = { current: 0 };
    render(
      <>
        <RailHarness spine={spine} countRef={railRenders} />
        <ModelHarness spine={spine} countRef={modelRenders} />
        <DraftHarness spine={spine} countRef={draftRenders} />
      </>
    );

    const initialRailRenders = railRenders.current;
    const initialModelRenders = modelRenders.current;
    const initialDraftRenders = draftRenders.current;

    act(() => {
      spine.tabSetDraft(active.tabId, "h");
      spine.tabSetDraft(active.tabId, "he");
      spine.tabSetDraft(active.tabId, "hel");
    });

    expect(railRenders.current).toBe(initialRailRenders);
    expect(modelRenders.current).toBe(initialModelRenders);
    expect(draftRenders.current).toBeGreaterThan(initialDraftRenders);

    act(() => {
      spine.tabSetModel(active.tabId, "gpt-oss");
    });

    expect(railRenders.current).toBeGreaterThan(initialRailRenders);
    expect(modelRenders.current).toBeGreaterThan(initialModelRenders);
  });
});
