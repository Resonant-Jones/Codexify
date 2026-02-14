import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  InMemorySessionStateStore,
  RedisSessionStateStore,
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
