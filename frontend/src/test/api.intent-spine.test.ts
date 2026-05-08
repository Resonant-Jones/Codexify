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

import { dispatchGuardianIntent } from "@/lib/api";

describe("guardian intent dispatch API", () => {
  it("posts intent envelopes to the Guardian intent spine with the actor header", async () => {
    postSpy.mockResolvedValue({
      data: {
        intent_id: "intent-123",
        status: "accepted",
        dispatch_target: "command_bus",
        receipt_ref: "run-123",
      },
    });

    await expect(
      dispatchGuardianIntent({
        actor: {
          kind: "human",
          id: "local",
        },
        source_surface: "chat",
        intent_kind: "command_bus.invoke",
        target: {
          command_id: "op::guardian.profile.switch",
          arguments: {
            path_params: { thread_id: 1 },
            body: { profile_id: "local_mode" },
          },
          idempotency_key: "chat-profile-switch:1:local_mode",
        },
        scope: {
          thread_id: 1,
          project_id: 9,
        },
        policy: {
          approval_required: false,
          allow_write_execution: true,
        },
      })
    ).resolves.toEqual({
      intent_id: "intent-123",
      status: "accepted",
      dispatch_target: "command_bus",
      receipt_ref: "run-123",
    });

    expect(postSpy).toHaveBeenCalledWith(
      "/api/guardian/intents/dispatch",
      expect.objectContaining({
        source_surface: "chat",
        intent_kind: "command_bus.invoke",
        actor: { kind: "human", id: "local" },
        target: expect.objectContaining({
          command_id: "op::guardian.profile.switch",
          idempotency_key: "chat-profile-switch:1:local_mode",
        }),
      }),
      expect.objectContaining({
        headers: { "X-User-Id": "local" },
      })
    );
  });
});
