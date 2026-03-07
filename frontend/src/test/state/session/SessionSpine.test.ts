import { describe, expect, it } from "vitest";

import { SessionSpine } from "@/state/session/SessionSpine";
import { InMemorySessionStateStore } from "@/state/session/SessionStateStore";

function createSpine() {
  return new SessionSpine({
    userId: "user-1",
    deviceId: "device-1",
    store: new InMemorySessionStateStore(),
  });
}

describe("SessionSpine tab activation order", () => {
  it("cycles next and previous with wrap-around", async () => {
    const spine = createSpine();
    await spine.hydrate({ title: "Tab 1" });

    const tabOneId = spine.getActiveTabId();
    const tabTwoId = spine.tabOpen(undefined, "Tab 2").tabId;
    const tabThreeId = spine.tabOpen(undefined, "Tab 3").tabId;

    expect(tabOneId).toBeTruthy();
    expect(spine.getActiveTabId()).toBe(tabThreeId);

    spine.tabActivate(tabOneId!);
    spine.tabActivateNext();
    expect(spine.getActiveTabId()).toBe(tabTwoId);

    spine.tabActivateNext();
    expect(spine.getActiveTabId()).toBe(tabThreeId);

    spine.tabActivateNext();
    expect(spine.getActiveTabId()).toBe(tabOneId);

    spine.tabActivatePrevious();
    expect(spine.getActiveTabId()).toBe(tabThreeId);
  });

  it("keeps active tab unchanged when only one tab exists", async () => {
    const spine = createSpine();
    await spine.hydrate({ title: "Only Tab" });
    const tabId = spine.getActiveTabId();

    spine.tabActivateNext();
    expect(spine.getActiveTabId()).toBe(tabId);

    spine.tabActivatePrevious();
    expect(spine.getActiveTabId()).toBe(tabId);
  });
});
