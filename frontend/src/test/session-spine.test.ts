import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  InMemorySessionStateStore,
  RedisSessionStateStore,
  type SessionStateStore,
} from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from "@/lib/api";

const sampleState = {
  userId: "user-1",
  deviceId: "device-1",
  tabs: [
    {
      tabId: "tab-1",
      threadId: "101",
      title: "Alpha",
      modelId: "default",
      createdAt: "2026-02-14T00:00:00.000Z",
      updatedAt: "2026-02-14T00:00:00.000Z",
    },
  ],
  activeTabId: "tab-1",
  drafts: { "tab-1": "draft" },
  version: 1,
  updatedAt: "2026-02-14T00:00:00.000Z",
};

describe("SessionSpine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("supports open/close/activate/reorder intents", async () => {
    const store = new InMemorySessionStateStore();
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });

    await spine.hydrate({ threadId: "101", title: "Alpha", modelId: "default" });
    const first = spine.getActiveTab();
    expect(first?.threadId).toBe("101");

    const second = spine.tabOpen("202", "Beta");
    const third = spine.tabOpen("303", "Gamma");
    expect(spine.getTabs()).toHaveLength(3);
    expect(spine.getActiveTabId()).toBe(third.tabId);

    if (!first) throw new Error("Expected initial tab");
    spine.tabActivate(first.tabId);
    expect(spine.getActiveTabId()).toBe(first.tabId);

    spine.tabReorder([third.tabId, first.tabId, second.tabId]);
    expect(spine.getTabs().map((tab) => tab.tabId)).toEqual([
      third.tabId,
      first.tabId,
      second.tabId,
    ]);

    spine.tabClose(third.tabId);
    expect(spine.getTabs().map((tab) => tab.tabId)).toEqual([
      first.tabId,
      second.tabId,
    ]);
  });

  it("hydrates from an existing persisted state", async () => {
    const store = new InMemorySessionStateStore();
    await store.setSessionState("user-1", "device-1", sampleState as any, 1000);
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });

    const hydrated = await spine.hydrate();
    expect(hydrated.activeTabId).toBe("tab-1");
    expect(hydrated.tabs[0].threadId).toBe("101");
    expect(spine.getDraft("tab-1")).toBe("draft");
  });

  it("persists draft + model updates", async () => {
    const store = new InMemorySessionStateStore();
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });
    await spine.hydrate({ threadId: "101", title: "Alpha" });

    const active = spine.getActiveTab();
    if (!active) throw new Error("Expected active tab");

    spine.tabSetModel(active.tabId, "gpt-oss");
    spine.tabSetDraft(active.tabId, "hello draft");
    await new Promise((resolve) => setTimeout(resolve, 350));

    const persisted = await store.getSessionState("user-1", "device-1");
    expect(persisted?.tabs[0].modelId).toBe("gpt-oss");
    expect(persisted?.drafts?.[active.tabId]).toBe("hello draft");
  });

  it("coalesces rapid draft persistence writes", async () => {
    const store = new InMemorySessionStateStore();
    const setSpy = vi.spyOn(store, "setSessionState");
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });
    await spine.hydrate({ threadId: "101", title: "Alpha", modelId: "default" });
    setSpy.mockClear();

    const active = spine.getActiveTab();
    if (!active) throw new Error("Expected active tab");

    spine.tabSetDraft(active.tabId, "h");
    spine.tabSetDraft(active.tabId, "he");
    spine.tabSetDraft(active.tabId, "hel");
    await new Promise((resolve) => setTimeout(resolve, 350));

    expect(setSpy).toHaveBeenCalledTimes(1);
    const persisted = await store.getSessionState("user-1", "device-1");
    expect(persisted?.drafts?.[active.tabId]).toBe("hel");
  });

  it("closing the final tab always leaves one valid active tab", async () => {
    const store = new InMemorySessionStateStore();
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });
    await spine.hydrate({ threadId: "101", title: "Alpha", modelId: "default" });

    const only = spine.getActiveTab();
    if (!only) throw new Error("Expected a tab");

    expect(() => spine.tabClose(only.tabId)).not.toThrow();

    const tabs = spine.getTabs();
    expect(tabs).toHaveLength(1);
    expect(spine.getActiveTabId()).toBe(tabs[0].tabId);
    expect(tabs[0].modelId).toBe("default");
  });

  it("closing an active tab falls back to most recently active remaining tab", async () => {
    const store = new InMemorySessionStateStore();
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });
    await spine.hydrate({ threadId: "101", title: "Alpha", modelId: "default" });

    const tabA = spine.getActiveTab();
    if (!tabA) throw new Error("Expected initial tab");
    const tabB = spine.tabOpen("202", "Beta");
    const tabC = spine.tabOpen("303", "Gamma");

    // Make C the previously active tab, then switch to A and close A.
    spine.tabActivate(tabC.tabId);
    spine.tabActivate(tabA.tabId);
    spine.tabClose(tabA.tabId);

    expect(spine.getActiveTabId()).toBe(tabC.tabId);
    expect(spine.getTabs().map((tab) => tab.tabId)).toEqual([
      tabB.tabId,
      tabC.tabId,
    ]);
  });

  it("hydrates empty tabs to a default one-tab state", async () => {
    const store = new InMemorySessionStateStore();
    await store.setSessionState(
      "user-1",
      "device-1",
      {
        userId: "user-1",
        deviceId: "device-1",
        tabs: [],
        activeTabId: "missing",
        version: 1,
        updatedAt: "2026-02-14T00:00:00.000Z",
      } as any,
      1000
    );

    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
    });

    const hydrated = await spine.hydrate();
    expect(hydrated.tabs).toHaveLength(1);
    expect(hydrated.activeTabId).toBe(hydrated.tabs[0].tabId);
  });

  it("normalizes missing or invalid active tab ids during hydration", async () => {
    const missingActiveStore = new InMemorySessionStateStore();
    await missingActiveStore.setSessionState(
      "user-1",
      "device-1",
      {
        userId: "user-1",
        deviceId: "device-1",
        tabs: [
          {
            tabId: "tab-a",
            modelId: "default",
            createdAt: "2026-02-14T00:00:00.000Z",
            updatedAt: "2026-02-14T00:00:00.000Z",
          },
        ],
        version: 1,
        updatedAt: "2026-02-14T00:00:00.000Z",
      } as any,
      1000
    );

    const missingActiveSpine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store: missingActiveStore,
      defaultModelId: "default",
    });
    const missingActive = await missingActiveSpine.hydrate();
    expect(missingActive.activeTabId).toBe("tab-a");

    const invalidActiveStore = new InMemorySessionStateStore();
    await invalidActiveStore.setSessionState(
      "user-2",
      "device-2",
      {
        userId: "user-2",
        deviceId: "device-2",
        tabs: [
          {
            tabId: "tab-b",
            modelId: "default",
            createdAt: "2026-02-14T00:00:00.000Z",
            updatedAt: "2026-02-14T00:00:00.000Z",
          },
        ],
        activeTabId: "not-present",
        version: 1,
        updatedAt: "2026-02-14T00:00:00.000Z",
      } as any,
      1000
    );

    const invalidActiveSpine = new SessionSpine({
      userId: "user-2",
      deviceId: "device-2",
      store: invalidActiveStore,
      defaultModelId: "default",
    });
    const invalidActive = await invalidActiveSpine.hydrate();
    expect(invalidActive.activeTabId).toBe("tab-b");
  });

  it("falls back to default state when store hydration throws", async () => {
    const failingStore: SessionStateStore = {
      async getSessionState() {
        throw new Error("boom");
      },
      async setSessionState() {
        return;
      },
      async patchSessionState() {
        return null;
      },
      async deleteSessionState() {
        return;
      },
    };

    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store: failingStore,
      defaultModelId: "default",
    });

    const hydrated = await spine.hydrate({ modelId: "default" });
    expect(hydrated.tabs).toHaveLength(1);
    expect(hydrated.activeTabId).toBe(hydrated.tabs[0].tabId);
  });

  it("skips backend hydration when auth gate blocks hydrate", async () => {
    const store = new InMemorySessionStateStore();
    const getSpy = vi.spyOn(store, "getSessionState");
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
      canHydrate: () => false,
    });

    const hydrated = await spine.hydrate({ threadId: "101", modelId: "default" });
    expect(getSpy).not.toHaveBeenCalled();
    expect(hydrated.tabs).toHaveLength(1);
    expect(hydrated.tabs[0].threadId).toBe("101");
  });

  it("skips persistence when auth gate blocks persist", async () => {
    const store = new InMemorySessionStateStore();
    const setSpy = vi.spyOn(store, "setSessionState");
    const spine = new SessionSpine({
      userId: "user-1",
      deviceId: "device-1",
      store,
      defaultModelId: "default",
      canPersist: () => false,
    });

    await spine.hydrate({ threadId: "101", modelId: "default" });
    const active = spine.getActiveTab();
    if (!active) throw new Error("Expected active tab");

    spine.tabSetDraft(active.tabId, "gated draft");
    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(setSpy).not.toHaveBeenCalled();
  });
});

describe("RedisSessionStateStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("serializes get/set/patch requests with user + device keying", async () => {
    const store = new RedisSessionStateStore();

    (api.get as any).mockResolvedValue({
      data: { ok: true, state: sampleState },
    });
    const loaded = await store.getSessionState("user-1", "device-1");
    expect(loaded?.activeTabId).toBe("tab-1");
    expect(api.get).toHaveBeenCalledWith("/ui/session", {
      params: { user_id: "user-1", device_id: "device-1" },
    });

    await store.setSessionState("user-1", "device-1", sampleState as any, 900);
    expect(api.put).toHaveBeenCalledWith("/ui/session", {
      user_id: "user-1",
      device_id: "device-1",
      state: sampleState,
      ttl_seconds: 900,
    });

    (api.patch as any).mockResolvedValue({
      data: { ok: true, state: { ...sampleState, activeTabId: "tab-2" } },
    });
    await store.patchSessionState(
      "user-1",
      "device-1",
      { activeTabId: "tab-2" } as any,
      300
    );
    expect(api.patch).toHaveBeenCalledWith("/ui/session", {
      user_id: "user-1",
      device_id: "device-1",
      patch: { activeTabId: "tab-2" },
      ttl_seconds: 300,
    });
  });
});
