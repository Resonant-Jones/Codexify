import { describe, expect, it } from "vitest";
import {
  describeTaskFailureDetailText,
  getToolCommandFailureReason,
  GENERIC_PROVIDER_FAILURE_DETAIL_TEXT,
  PROVIDER_TIMEOUT_DETAIL_TEXT,
  PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT,
} from "@/features/chat/requestFailurePresentation";

const deadline = { failure_code: "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED" };

describe("authoritative command failure presentation", () => {
  it.each([
    ["tool_command_failed", /action.*failed/i],
    ["tool_command_blocked", /action.*not authorized/i],
  ] as const)("describes %s without blaming the provider", (reason, expected) => {
    const detail = describeTaskFailureDetailText({
      toolTurnState: "failed", loopStopReason: reason,
      error: reason, transport_classification: "timeout",
    });
    expect(detail).toMatch(expected);
    expect(detail).not.toMatch(/provider|offline|completed|switch.*mode/i);
  });

  it("recognizes the contract's snake-case carrier", () => {
    const payload = { tool_turn_state: "failed", loop_stop_reason: "tool_command_blocked" };
    expect(getToolCommandFailureReason(payload)).toBe("tool_command_blocked");
    expect(describeTaskFailureDetailText(payload)).toMatch(/action.*not authorized/i);
  });

  it.each([
    { error: "tool_command_failed" },
    { loopStopReason: "tool_command_failed" },
    { toolTurnState: "completed", loopStopReason: "tool_command_failed" },
    { toolTurnState: "failed", loopStopReason: "unknown" },
  ])("does not infer command failure from incomplete or contradictory evidence %j", (payload) => {
    expect(getToolCommandFailureReason(payload)).toBeNull();
    expect(describeTaskFailureDetailText(payload)).toBe(GENERIC_PROVIDER_FAILURE_DETAIL_TEXT);
  });

  it("preserves authoritative deadline precedence over tool metadata", () => {
    const payload = { ...deadline, toolTurnState: "failed", loopStopReason: "tool_command_failed" };
    expect(getToolCommandFailureReason(payload)).toBeNull();
    expect(describeTaskFailureDetailText(payload)).toMatch(/request.*time limit/i);
  });
});

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
