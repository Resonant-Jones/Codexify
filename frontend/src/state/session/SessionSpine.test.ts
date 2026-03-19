import { beforeEach, describe, expect, it } from "vitest";

import { InMemorySessionStateStore } from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";

const USER_ID = "user-1";
const DEVICE_ID = "device-1";

function createSpine(store = new InMemorySessionStateStore()): SessionSpine {
  return new SessionSpine({
    userId: USER_ID,
    deviceId: DEVICE_ID,
    store,
    defaultModelId: "default",
  });
}

describe("SessionSpine inference mode persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to fast when nothing is stored", async () => {
    const spine = createSpine();

    const hydrated = await spine.hydrate();

    expect(hydrated.tabs[0]?.inferenceMode).toBe("no_think");
    expect(spine.getActiveTab()?.inferenceMode).toBe("no_think");
  });

  it("restores a saved non-default mode on hydration", async () => {
    const store = new InMemorySessionStateStore();
    await store.setSessionState(
      USER_ID,
      DEVICE_ID,
      {
        userId: USER_ID,
        deviceId: DEVICE_ID,
        selectedInferenceMode: "think",
        tabs: [
          {
            tabId: "tab-1",
            threadId: "101",
            pendingThread: false,
            title: "Alpha",
            providerId: null,
            modelId: "default",
            inferenceMode: "default",
            createdAt: "2026-03-19T00:00:00.000Z",
            updatedAt: "2026-03-19T00:00:00.000Z",
          },
        ],
        activeTabId: "tab-1",
        version: 2,
        updatedAt: "2026-03-19T00:00:00.000Z",
      } as any,
      1000
    );

    const spine = createSpine(store);
    const hydrated = await spine.hydrate();

    expect(hydrated.tabs[0]?.inferenceMode).toBe("think");
    expect(spine.getActiveTab()?.inferenceMode).toBe("think");
  });

  it("persists mode changes immediately", async () => {
    const store = new InMemorySessionStateStore();
    const spine = createSpine(store);
    await spine.hydrate();

    const activeTab = spine.getActiveTab();
    if (!activeTab) throw new Error("Expected active tab");

    spine.tabSetInferenceMode(activeTab.tabId, "think");
    await Promise.resolve();

    const persisted = await store.getSessionState(USER_ID, DEVICE_ID);
    expect(persisted?.tabs[0]?.inferenceMode).toBe("think");
  });

  it("does not reset to auto after a simulated send/remount cycle", async () => {
    const store = new InMemorySessionStateStore();
    const firstMount = createSpine(store);
    await firstMount.hydrate();

    const activeTab = firstMount.getActiveTab();
    if (!activeTab) throw new Error("Expected active tab");

    firstMount.tabSetInferenceMode(activeTab.tabId, "think");
    firstMount.tabSetThread(activeTab.tabId, "202", "Beta");
    await Promise.resolve();

    const remounted = createSpine(store);
    const hydrated = await remounted.hydrate({ threadId: "202", title: "Beta" });

    expect(hydrated.tabs[0]?.inferenceMode).toBe("think");
    expect(remounted.getActiveTab()?.inferenceMode).toBe("think");
    expect(remounted.getActiveTab()?.inferenceMode).not.toBe("default");
  });
});
