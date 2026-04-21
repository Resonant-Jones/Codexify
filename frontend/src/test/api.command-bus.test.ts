import { describe, expect, it, vi } from "vitest";

const { postSpy } = vi.hoisted(() => ({
  postSpy: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      post: postSpy,
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}));

import { invokeCommandBus } from "@/lib/api";

describe("command-bus invoke API", () => {
  it("posts command invocations to the command-bus surface with the actor header", async () => {
    postSpy.mockResolvedValue({
      data: {
        run_id: "run-123",
        status: "completed",
        inline_result: { ok: true },
      },
    });

    await expect(
      invokeCommandBus({
        invoke_version: "1.0",
        command_id: "op::guardian.profile.switch",
        actor: {
          kind: "human",
          id: "local",
        },
        arguments: {
          body: { profile_id: "local_mode" },
        },
      })
    ).resolves.toEqual({
      run_id: "run-123",
      status: "completed",
      inline_result: { ok: true },
    });

    expect(postSpy).toHaveBeenCalledWith(
      "/api/guardian/commands/invoke",
      expect.objectContaining({
        invoke_version: "1.0",
        command_id: "op::guardian.profile.switch",
        actor: { kind: "human", id: "local" },
        arguments: {
          body: { profile_id: "local_mode" },
        },
      }),
      expect.objectContaining({
        headers: { "X-User-Id": "local" },
      })
    );
  });
});
