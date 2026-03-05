import { afterEach, beforeEach, describe, expect, it } from "vitest";

import api, {
  clearInFlightCompletionTurnId,
  getInFlightCompletionTurnId,
} from "@/lib/api";

const UUID_V4ISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function getRequestInterceptor(): (config: any) => Promise<any> | any {
  const handlers = (api.interceptors.request as any)?.handlers ?? [];
  const match = handlers.find(
    (handler: any) => typeof handler?.fulfilled === "function"
  );
  if (!match) {
    throw new Error("request interceptor not found");
  }
  return match.fulfilled;
}

function parsePayload(data: any): Record<string, any> {
  if (typeof data === "string") {
    return JSON.parse(data) as Record<string, any>;
  }
  return (data ?? {}) as Record<string, any>;
}

describe("api completion turn_id generation", () => {
  const threadId = 4242;

  beforeEach(() => {
    clearInFlightCompletionTurnId(threadId);
  });

  afterEach(() => {
    clearInFlightCompletionTurnId(threadId);
  });

  it("generates a fresh turn_id for each completion request without explicit turn_id", async () => {
    const applyInterceptor = getRequestInterceptor();

    const firstConfig = await applyInterceptor({
      method: "post",
      url: `/chat/${threadId}/complete`,
      data: {},
    });
    const firstTurnId = String(parsePayload(firstConfig.data).turn_id || "");
    expect(UUID_V4ISH_RE.test(firstTurnId)).toBe(true);
    expect(getInFlightCompletionTurnId(threadId)).toBe(firstTurnId);

    const secondConfig = await applyInterceptor({
      method: "post",
      url: `/chat/${threadId}/complete`,
      data: {},
    });
    const secondTurnId = String(parsePayload(secondConfig.data).turn_id || "");
    expect(UUID_V4ISH_RE.test(secondTurnId)).toBe(true);
    expect(secondTurnId).not.toBe(firstTurnId);
    expect(getInFlightCompletionTurnId(threadId)).toBe(secondTurnId);
  });

  it("preserves a valid client-supplied turn_id", async () => {
    const applyInterceptor = getRequestInterceptor();
    const explicitTurnId = "11111111-1111-4111-8111-111111111111";

    const config = await applyInterceptor({
      method: "post",
      url: `/chat/${threadId}/complete`,
      data: { turn_id: explicitTurnId },
    });

    const payload = parsePayload(config.data);
    expect(payload.turn_id).toBe(explicitTurnId);
    expect(getInFlightCompletionTurnId(threadId)).toBe(explicitTurnId);
  });
});
