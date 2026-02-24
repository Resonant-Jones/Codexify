import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("Draft thread route invariants", () => {
  it("uses create-on-send /chat/messages for null thread sends", () => {
    const source = readFileSync(
      resolve(process.cwd(), "features/chat/GuardianChat.tsx"),
      "utf8"
    );

    expect(source).toContain('api.post("/chat/messages"');
    expect(source).toContain("thread_id: null");
  });

  it("does not create threads from dashboard new-thread flow", () => {
    const source = readFileSync(
      resolve(process.cwd(), "components/persona/layout/AppShell.tsx"),
      "utf8"
    );
    const start = source.indexOf("const createThreadFromDashboard");
    const end = source.indexOf("const activeWallpaper");
    const slice = start >= 0 && end > start ? source.slice(start, end) : source;

    expect(slice).toContain("cfy:chat:new-draft");
    expect(slice).not.toContain('api.post("/chat/threads"');
  });
});
