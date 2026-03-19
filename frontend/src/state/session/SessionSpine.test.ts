import { beforeEach, describe, expect, it } from "vitest";

import { InMemorySessionStateStore } from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";

let sessionCounter = 0;

function createSpine(
  store = new InMemorySessionStateStore(),
  sessionId = `session-${++sessionCounter}`
): SessionSpine {
  return new SessionSpine({
    userId: `user-${sessionId}`,
    deviceId: `device-${sessionId}`,
    store,
    defaultModelId: "default",
  });
}

function requireActiveTab(spine: SessionSpine) {
  const activeTab = spine.getActiveTab();
  if (!activeTab) {
    throw new Error("Expected an active tab");
  }
  return activeTab;
}

describe("SessionSpine inference mode persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    sessionCounter = 0;
  });

  it("defaults to fast when nothing is stored", async () => {
    const spine = createSpine();

    const hydrated = await spine.hydrate();

    expect(hydrated.tabs[0]?.inferenceMode).toBe("no_think");
    expect(spine.getActiveTab()?.inferenceMode).toBe("no_think");
  });

  it("restores a saved non-default mode on hydration", async () => {
    const store = new InMemorySessionStateStore();
    const sessionId = "restore-mode";
    await store.setSessionState(
      `user-${sessionId}`,
      `device-${sessionId}`,
      {
        userId: `user-${sessionId}`,
        deviceId: `device-${sessionId}`,
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

    const spine = createSpine(store, sessionId);
    const hydrated = await spine.hydrate();

    expect(hydrated.tabs[0]?.inferenceMode).toBe("think");
    expect(spine.getActiveTab()?.inferenceMode).toBe("think");
  });

  it("persists mode changes immediately", async () => {
    const store = new InMemorySessionStateStore();
    const spine = createSpine(store);
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetInferenceMode(activeTab.tabId, "think");
    await Promise.resolve();

    const persisted = await store.getSessionState("user-session-1", "device-session-1");
    expect(persisted?.tabs[0]?.inferenceMode).toBe("think");
  });

  it("does not reset to auto after a simulated send/remount cycle", async () => {
    const store = new InMemorySessionStateStore();
    const sessionId = "remount-mode";
    const firstMount = createSpine(store, sessionId);
    await firstMount.hydrate();

    const activeTab = requireActiveTab(firstMount);
    firstMount.tabSetInferenceMode(activeTab.tabId, "think");
    firstMount.tabSetThread(activeTab.tabId, "202", "Beta");
    await Promise.resolve();

    const remounted = createSpine(store, sessionId);
    const hydrated = await remounted.hydrate({ threadId: "202", title: "Beta" });

    expect(hydrated.tabs[0]?.inferenceMode).toBe("think");
    expect(remounted.getActiveTab()?.inferenceMode).toBe("think");
    expect(remounted.getActiveTab()?.inferenceMode).not.toBe("default");
  });
});

describe("SessionSpine completion lifecycle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    sessionCounter = 0;
  });

  it("cancel immediately transitions the active completion to canceled", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "301", "Cancel Test");
    spine.rememberSubmittedDraft("Bring the composer back", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "301",
      taskId: "task-cancel-1",
      turnId: "turn-cancel-1",
    });

    spine.cancelActiveCompletion({ taskId: "task-cancel-1" });

    expect(spine.getActiveCompletion()?.status).toBe("canceled");
  });

  it("cancel immediately re-enables the composer", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "302", "Unlock Test");
    spine.rememberSubmittedDraft("Unlock now", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "302",
      taskId: "task-unlock-1",
      turnId: "turn-unlock-1",
    });

    expect(spine.isComposerBlocked()).toBe(true);

    spine.cancelActiveCompletion({ taskId: "task-unlock-1" });

    expect(spine.isComposerBlocked()).toBe(false);
  });

  it("cancel preserves the draft input", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "303", "Draft Test");
    spine.rememberSubmittedDraft("Keep this draft", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "303",
      taskId: "task-draft-1",
      turnId: "turn-draft-1",
    });
    spine.tabSetDraft(activeTab.tabId, "");

    spine.cancelActiveCompletion({ taskId: "task-draft-1" });

    expect(spine.getDraft(activeTab.tabId)).toBe("Keep this draft");
  });

  it("a second send can start immediately after cancel", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "304", "Retry Test");
    spine.rememberSubmittedDraft("First pass", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "304",
      taskId: "task-retry-1",
      turnId: "turn-retry-1",
    });
    const firstCompletionId = spine.getActiveCompletion()?.completionId;

    spine.cancelActiveCompletion({ taskId: "task-retry-1" });
    spine.rememberSubmittedDraft("Second pass", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "304",
      taskId: "task-retry-2",
      turnId: "turn-retry-2",
    });

    expect(spine.getActiveCompletion()?.completionId).not.toBe(firstCompletionId);
    expect(spine.getActiveCompletion()?.status).toBe("submitting");
    expect(spine.isComposerBlocked()).toBe(true);
  });

  it("late events for the canceled completion are ignored and do not re-lock the composer", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "305", "Late Event Test");
    spine.rememberSubmittedDraft("Ignore the old task", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "305",
      taskId: "task-late-1",
      turnId: "turn-late-1",
    });
    spine.cancelActiveCompletion({ taskId: "task-late-1" });

    const accepted = spine.shouldAcceptLiveEvent("task.progress", {
      task_id: "task-late-1",
      thread_id: "305",
      turn_id: "turn-late-1",
    });

    expect(accepted).toBe(false);
    expect(spine.getActiveCompletion()?.status).toBe("canceled");
    expect(spine.isComposerBlocked()).toBe(false);
  });

  it("a superseded completion cannot overwrite the new active completion state", async () => {
    const spine = createSpine();
    await spine.hydrate();

    const activeTab = requireActiveTab(spine);
    spine.tabSetThread(activeTab.tabId, "306", "Supersede Test");
    spine.rememberSubmittedDraft("Old request", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "306",
      taskId: "task-old",
      turnId: "turn-old",
    });
    spine.cancelActiveCompletion({ taskId: "task-old" });

    spine.rememberSubmittedDraft("New request", { tabId: activeTab.tabId });
    spine.startCompletion({
      tabId: activeTab.tabId,
      threadId: "306",
      taskId: "task-new",
      turnId: "turn-new",
    });

    const accepted = spine.shouldAcceptLiveEvent("task.completed", {
      task_id: "task-old",
      thread_id: "306",
      turn_id: "turn-old",
    });

    expect(accepted).toBe(false);
    expect(spine.getActiveCompletion()?.taskId).toBe("task-new");
    expect(spine.getActiveCompletion()?.status).toBe("submitting");
  });
});
