import { describe, expect, it } from "vitest";

import {
  createInitialFlowDraftState,
  flowDraftReducer,
  getCurrentNodeSelection,
  getGraphVisibleNodes,
  getOrderedStageProgress,
  getSupportChatContextSummary,
  getValidationSummary,
} from "../hooks/useFlowDraftState";
import {
  FLOW_DRAFT_STAGE_REGISTRY,
  createSpecFirstFlowDraft,
  getFlowDraftStageNodeId,
} from "../model/flowDraft";

describe("flow draft model", () => {
  it("creates the canonical spec-first draft and stage registry", () => {
    const draft = createSpecFirstFlowDraft("2026-04-30T00:00:00.000Z");

    expect(draft.meta.title).toBe("Draft specification");
    expect(draft.meta.status).toBe("draft-only");
    expect(draft.meta.runtimeSupport).toBe("none");
    expect(draft.nodes.map((node) => node.stageId)).toEqual(
      FLOW_DRAFT_STAGE_REGISTRY.map((stage) => stage.id)
    );
    expect(draft.edges).toHaveLength(FLOW_DRAFT_STAGE_REGISTRY.length - 1);
    expect(getValidationSummary(draft)).toMatchObject({
      total: 1,
      warningCount: 1,
      errorCount: 0,
      label: "1 warning",
    });
  });

  it("keeps stage selection, node selection, and graph order on one reducer spine", () => {
    let state = createInitialFlowDraftState("process", "2026-04-30T00:00:00.000Z");

    expect(state.view.selection.stageId).toBe("select-source");
    expect(state.view.selection.nodeId).toBe(getFlowDraftStageNodeId("select-source"));

    state = flowDraftReducer(state, { type: "selectStage", stageId: "set-outcomes" });
    expect(getCurrentNodeSelection(state.draft, state.view)).toMatchObject({
      stage: { id: "set-outcomes", label: "Set Outcomes" },
      node: { id: getFlowDraftStageNodeId("set-outcomes") },
    });

    state = flowDraftReducer(state, {
      type: "updateNodeFields",
      nodeId: getFlowDraftStageNodeId("set-outcomes"),
      fields: { outcome: "Keep the desired result visible." },
    });

    expect(getCurrentNodeSelection(state.draft, state.view).node?.fields.outcome).toBe(
      "Keep the desired result visible."
    );

    state = flowDraftReducer(state, {
      type: "moveNode",
      nodeId: getFlowDraftStageNodeId("set-outcomes"),
      direction: "up",
    });

    expect(getGraphVisibleNodes(state.draft).map((node) => node.stageId)).toEqual([
      "select-source",
      "set-outcomes",
      "define-constraints",
      "add-steps",
      "insert-conditions",
      "validation-gates",
      "review-validate",
    ]);
    expect(getCurrentNodeSelection(state.draft, state.view).node?.id).toBe(
      getFlowDraftStageNodeId("set-outcomes")
    );
    expect(getOrderedStageProgress(state.draft, state.view).find((item) => item.isSelected)?.stage.id).toBe(
      "set-outcomes"
    );
  });

  it("replaces and patches validation issues without losing the shared summary", () => {
    let state = createInitialFlowDraftState("expertise", "2026-04-30T00:00:00.000Z");

    state = flowDraftReducer(state, {
      type: "replaceValidationIssues",
      issues: [
        {
          id: "issue-error",
          severity: "error",
          message: "Missing execution boundary.",
          stageId: "review-validate",
        },
      ],
    });

    expect(getValidationSummary(state.draft)).toMatchObject({
      total: 1,
      errorCount: 1,
      warningCount: 0,
      primarySeverity: "error",
      label: "1 error",
    });

    state = flowDraftReducer(state, {
      type: "patchValidationIssues",
      issues: [
        {
          id: "issue-error",
          message: "Missing execution boundary before compile support can exist.",
        },
        {
          id: "issue-note",
          severity: "info",
          message: "Draft remains inspectable only.",
          stageId: "define-constraints",
        },
      ],
    });

    expect(getValidationSummary(state.draft)).toMatchObject({
      total: 2,
      errorCount: 1,
      infoCount: 1,
      warningCount: 0,
      primarySeverity: "error",
      label: "1 error",
    });
    expect(
      getSupportChatContextSummary(state.draft, state.view)
    ).toMatchObject({
      selectedStageLabel: "Define Constraints",
      validationLabel: "1 error",
      dockStateLabel: "Open",
    });
  });

  it("dismisses and reopens the support dock without mutating the draft content", () => {
    let state = createInitialFlowDraftState("process", "2026-04-30T00:00:00.000Z");

    state = flowDraftReducer(state, {
      type: "updateDraftFields",
      fields: {
        objective: "Hold the canonical draft together across the dock toggle.",
      },
    });
    state = flowDraftReducer(state, { type: "dismissSupportChatDock" });
    expect(state.view.supportChatOpen).toBe(false);
    expect(state.draft.content.objective).toBe(
      "Hold the canonical draft together across the dock toggle."
    );

    state = flowDraftReducer(state, { type: "reopenSupportChatDock" });
    expect(state.view.supportChatOpen).toBe(true);
    expect(state.draft.content.objective).toBe(
      "Hold the canonical draft together across the dock toggle."
    );
  });
});
