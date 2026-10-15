import { describe, expect, it } from "vitest";
import {
  describeTaskFailureDetailText,
  GENERIC_PROVIDER_FAILURE_DETAIL_TEXT,
  PROVIDER_TIMEOUT_DETAIL_TEXT,
  PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT,
} from "@/features/chat/requestFailurePresentation";

const deadline = { failure_code: "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED" };

describe("authoritative deadline failure presentation", () => {
  it.each([
    { failed_after_state: "QUEUED", provider_request_started: false, first_output_observed: false },
    { failed_after_state: "STREAMING", provider_request_started: true, first_output_observed: true },
    { transport_classification: "timeout", failure_kind: "provider_timeout" },
  ])("keeps deadline identity separate from provider failure %j", (metadata) => {
    const detail = describeTaskFailureDetailText({ ...metadata, ...deadline });
    expect(detail).toMatch(/request.*time limit/i);
    expect(detail).not.toMatch(/provider|cancel|completed|offline/i);
  });

  it("retains genuine provider timeout and first-token timeout controls", () => {
    expect(describeTaskFailureDetailText({ failure_kind: "provider_timeout" })).toBe(PROVIDER_TIMEOUT_DETAIL_TEXT);
    expect(describeTaskFailureDetailText({
      transport_classification: "timeout", failed_after_state: "AWAITING_FIRST_TOKEN",
      provider_request_started: true, first_output_observed: false,
    })).toBe(PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT);
  });

  it("does not infer the canonical deadline error from a message or unknown code", () => {
    expect(describeTaskFailureDetailText({ error: "Deadline might have expired" })).toBe(GENERIC_PROVIDER_FAILURE_DETAIL_TEXT);
    expect(describeTaskFailureDetailText({ failure_code: "unknown" })).toBe(GENERIC_PROVIDER_FAILURE_DETAIL_TEXT);
  });
});
