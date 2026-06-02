import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianDelegationTranscriptViewer from "../GuardianDelegationTranscriptViewer";
import type { GuardianDelegationTranscriptResponse } from "@/contracts/guardianDelegationTranscript";

const apiMock = vi.hoisted(() => ({
  delete: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: apiMock,
}));

function transcriptResponse(
  overrides: Partial<GuardianDelegationTranscriptResponse> = {}
): GuardianDelegationTranscriptResponse {
  return {
    approval_mode: "scoped_auto",
    approval_source: "auto",
    approval_state: "approved",
    inspection_only: true,
    intent_id: "gdi_intent_alpha",
    intent_status: "accepted",
    project_id: 7,
    result_delivered_at: null,
    result_message_id: null,
    run_id: "run-alpha",
    run_status: "running",
    source_message_id: 55,
    source_thread_reference: {
      source_message_id: 55,
      thread_id: 42,
    },
    thread_id: 42,
    transcript_items: [
      {
        created_at: "2026-05-27T12:00:00Z",
        item_id: "intent:gdi_intent_alpha:created",
        kind: "intent_created",
        metadata: {
          approval_mode: "scoped_auto",
          intent_id: "gdi_intent_alpha",
          source_message_id: 55,
          thread_id: 42,
        },
        source: "guardian_delegation_intent",
        summary:
          "Guardian delegation intent created for source-thread lineage and inspection.",
      },
      {
        created_at: "2026-05-27T12:01:00Z",
        item_id: "run:run-alpha:status",
        kind: "run_status",
        metadata: {
          intent_id: "gdi_intent_alpha",
          run_id: "run-alpha",
          run_status: "running",
          source_message_id: 55,
          thread_id: 42,
        },
        source: "agent_run",
        summary: "Projected run status is `running`.",
      },
    ],
    visibility_status: "not_posted",
    ...overrides,
  };
}

function mockTranscript(
  overrides: Partial<GuardianDelegationTranscriptResponse> = {}
) {
  apiMock.get.mockResolvedValueOnce({ data: transcriptResponse(overrides) });
}

describe("GuardianDelegationTranscriptViewer", () => {
  beforeEach(() => {
    apiMock.delete.mockReset();
    apiMock.get.mockReset();
    apiMock.patch.mockReset();
    apiMock.post.mockReset();
    apiMock.put.mockReset();
  });

  it("renders_loaded_transcript_projection", async () => {
    mockTranscript();

    render(<GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />);

    expect(await screen.findByText("Inspection only")).toBeInTheDocument();
    expect(screen.getByText("Guardian delegation transcript")).toBeInTheDocument();
    expect(screen.getAllByText("gdi_intent_alpha").length).toBeGreaterThan(0);
    expect(screen.getAllByText("42").length).toBeGreaterThan(0);
    expect(screen.getAllByText("55").length).toBeGreaterThan(0);
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getAllByText("run-alpha").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Approval mode").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Approval state").length).toBeGreaterThan(0);
    expect(screen.getByText("Intent status")).toBeInTheDocument();
    expect(screen.getAllByText("Run status").length).toBeGreaterThan(0);
    expect(screen.getByText("Visibility status")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Guardian delegation intent created for source-thread lineage and inspection."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Projected run status is `running`.")).toBeInTheDocument();
  });

  it("renders_pending_manual_without_run_controls", async () => {
    mockTranscript({
      approval_mode: "manual",
      approval_source: "none",
      approval_state: "pending",
      intent_status: "awaiting_approval",
      project_id: null,
      run_id: null,
      run_status: "not_enqueued",
      transcript_items: [
        {
          created_at: "2026-05-27T12:00:00Z",
          item_id: "intent:gdi_pending:approval",
          kind: "approval_state",
          metadata: {
            approval_mode: "manual",
            approval_source: "none",
            approval_state: "pending",
            intent_id: "gdi_intent_alpha",
            intent_status: "awaiting_approval",
            source_message_id: 55,
            thread_id: 42,
          },
          source: "guardian_delegation_intent",
          summary: "Intent is awaiting human approval.",
        },
      ],
    });

    render(<GuardianDelegationTranscriptViewer intentId="gdi_pending" />);

    expect(await screen.findByText("Intent is awaiting human approval.")).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    expect(screen.queryByText("run-alpha")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /start/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^run$/i })).not.toBeInTheDocument();
  });

  it("renders_delivered_result_metadata", async () => {
    mockTranscript({
      result_delivered_at: "2026-05-27T13:00:00Z",
      result_message_id: 777,
      visibility_status: "result_posted",
      transcript_items: [
        {
          created_at: "2026-05-27T13:00:00Z",
          item_id: "intent:gdi_intent_alpha:delivery",
          kind: "delivery_result",
          metadata: {
            delivery_key: "delivery-gdi-intent-alpha",
            intent_id: "gdi_intent_alpha",
            result_message_id: 777,
            run_id: "run-alpha",
            visibility_status: "result_posted",
          },
          source: "chat_message",
          summary: "One terminal result message was posted to the source thread.",
        },
      ],
    });

    render(<GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />);

    expect(await screen.findByText("Result metadata")).toBeInTheDocument();
    expect(screen.getAllByText("777").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2026-05-27T13:00:00Z").length).toBeGreaterThan(0);
  });

  it("viewer_truncates_long_safe_metadata_values", async () => {
    const longDeliveryKey = `delivery-${"a".repeat(220)}`;
    const truncatedDeliveryKey = `${longDeliveryKey.slice(0, 137)}...`;
    mockTranscript({
      transcript_items: [
        {
          created_at: "2026-05-27T13:00:00Z",
          item_id: "intent:gdi_intent_alpha:delivery",
          kind: "delivery_result",
          metadata: {
            delivery_key: longDeliveryKey,
            intent_id: "gdi_intent_alpha",
            run_id: "run-alpha",
            visibility_status: "result_posted",
          },
          source: "chat_message",
          summary: "One terminal result message was posted to the source thread.",
        },
      ],
    });

    const { container } = render(
      <GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />
    );

    expect(await screen.findByText(truncatedDeliveryKey)).toBeInTheDocument();
    expect(screen.queryByText(longDeliveryKey)).not.toBeInTheDocument();
    expect(container.textContent).not.toContain(`"delivery_key":"${longDeliveryKey}"`);
    expect(container.textContent).not.toContain("delivery_key");
  });

  it("does_not_render_raw_metadata_or_context_blobs", async () => {
    mockTranscript({
      transcript_items: [
        {
          created_at: "2026-05-27T12:00:00Z",
          item_id: "intent:gdi_intent_alpha:unsafe",
          kind: "plan_prepared",
          metadata: {
            context_basis: "unsafe context_basis value",
            intent_id: "gdi_intent_alpha",
            project_kb_excerpt: "project kb excerpt must stay hidden",
            raw_log: "raw log must stay hidden",
            secret: "sk-secret-1234567890",
            standardized_task_prompt: "standardized task prompt must stay hidden",
            thread_id: 42,
          },
          source: "guardian_delegation_intent",
          summary: "Work plan prepared from selected-turn lineage only.",
        },
      ],
    });

    render(<GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />);

    expect(
      await screen.findByText("Work plan prepared from selected-turn lineage only.")
    ).toBeInTheDocument();
    expect(screen.queryByText("unsafe context_basis value")).not.toBeInTheDocument();
    expect(screen.queryByText("standardized task prompt must stay hidden")).not.toBeInTheDocument();
    expect(screen.queryByText("project kb excerpt must stay hidden")).not.toBeInTheDocument();
    expect(screen.queryByText("raw log must stay hidden")).not.toBeInTheDocument();
    expect(screen.queryByText("sk-secret-1234567890")).not.toBeInTheDocument();
  });

  it("does_not_use_dangerous_html_rendering", async () => {
    mockTranscript({
      transcript_items: [
        {
          created_at: "2026-05-27T12:00:00Z",
          item_id: "intent:gdi_intent_alpha:html",
          kind: "agent_run_event",
          metadata: {
            intent_id: "gdi_intent_alpha",
          },
          source: "agent_run_event",
          summary: "<strong>Do not render as markup</strong><img src=x>",
        },
      ],
    });

    const { container } = render(
      <GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />
    );

    expect(
      await screen.findByText("<strong>Do not render as markup</strong><img src=x>")
    ).toBeInTheDocument();
    expect(container.querySelector("strong")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders_not_found_state", async () => {
    apiMock.get.mockRejectedValueOnce({
      response: {
        data: { detail: "guardian_delegation_intent_not_found" },
        status: 404,
      },
    });

    render(<GuardianDelegationTranscriptViewer intentId="gdi_missing" />);

    expect(
      await screen.findByText("No Guardian delegation intent exists for that id.")
    ).toBeInTheDocument();
  });

  it("renders_unavailable_state_when_route_flag_disabled_or_unmounted", async () => {
    apiMock.get.mockRejectedValueOnce({
      response: {
        data: { detail: "Not Found" },
        status: 404,
      },
    });

    render(<GuardianDelegationTranscriptViewer intentId="gdi_internal" />);

    expect(
      await screen.findByText(
        "Guardian delegation transcript inspection is internal-only or unavailable in this runtime posture."
      )
    ).toBeInTheDocument();
  });

  it("does_not_call_mutation_endpoints", async () => {
    mockTranscript();

    render(<GuardianDelegationTranscriptViewer intentId="gdi_intent_alpha" />);

    await waitFor(() => {
      expect(apiMock.get).toHaveBeenCalledWith(
        "/api/guardian/delegations/gdi_intent_alpha/transcript"
      );
    });
    expect(apiMock.post).not.toHaveBeenCalled();
    expect(apiMock.patch).not.toHaveBeenCalled();
    expect(apiMock.put).not.toHaveBeenCalled();
    expect(apiMock.delete).not.toHaveBeenCalled();
  });
});
