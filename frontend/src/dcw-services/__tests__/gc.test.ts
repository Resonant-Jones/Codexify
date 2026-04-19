import { beforeEach, describe, expect, it, vi } from "vitest";

import { Tools } from "@/dcw-services/gc";

const apiSpies = vi.hoisted(() => ({
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  invokeCommandBus: async (payload: Record<string, unknown>) => {
    const response = await apiSpies.post(
      "/api/guardian/commands/invoke",
      payload,
      {
        headers: {
          "X-User-Id": String((payload as any)?.actor?.id ?? ""),
        },
      }
    );
    return response?.data ?? {};
  },
}));

describe("dcw-services/gc command bus adapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("routes legacy trigger execution through command bus invoke and caches terminal results", async () => {
    apiSpies.post.mockResolvedValue({
      data: {
        run_id: "run-1",
        status: "completed",
        inline_result: { ok: true, echo: { topic: "alpha" } },
      },
    });

    const execution = await Tools.execute({
      type: "sample.command",
      args: { topic: "alpha" },
    });

    expect(apiSpies.post).toHaveBeenCalledWith(
      "/api/guardian/commands/invoke",
      expect.objectContaining({
        invoke_version: "1.0",
        command_id: "sample.command",
        actor: { kind: "human", id: "local" },
        arguments: {
          body: { topic: "alpha" },
        },
      }),
      expect.objectContaining({
        headers: { "X-User-Id": "local" },
      })
    );
    expect(execution).toEqual({
      jobId: "run-1",
      state: "completed",
      result: { ok: true, echo: { topic: "alpha" } },
    });
    await expect(Tools.job("run-1")).resolves.toEqual({
      state: "completed",
      result: { ok: true, echo: { topic: "alpha" } },
    });
    expect(
      apiSpies.post.mock.calls.some(([url]) => url === "/tools/execute")
    ).toBe(false);
  });
});
