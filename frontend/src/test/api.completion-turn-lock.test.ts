import { afterEach, describe, expect, it } from "vitest";

import api, {
  clearInFlightCompletionTurnId,
  getInFlightCompletionTurnId,
} from "@/lib/api";

describe("completion turn tracking", () => {
  afterEach(() => {
    clearInFlightCompletionTurnId(42);
  });

  it("drops provisional in-flight turn id after 429 turn_in_flight", async () => {
    const requestFulfilled = (api.interceptors.request as any).handlers[0]
      ?.fulfilled;
    const responseRejected = (api.interceptors.response as any).handlers[0]
      ?.rejected;

    expect(typeof requestFulfilled).toBe("function");
    expect(typeof responseRejected).toBe("function");

    const requestConfig = await requestFulfilled({
      method: "post",
      url: "/chat/42/complete",
      data: {},
      headers: {},
    });

    const provisionalTurnId = requestConfig.__cfyCompletionTurnId as string;
    expect(provisionalTurnId).toBeTruthy();
    expect(getInFlightCompletionTurnId(42)).toBe(provisionalTurnId);

    await expect(
      responseRejected({
        config: requestConfig,
        response: {
          status: 429,
          data: {
            detail: "turn_in_flight",
          },
        },
      })
    ).rejects.toBeTruthy();

    expect(getInFlightCompletionTurnId(42)).toBeNull();
  });
});
