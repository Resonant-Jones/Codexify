import { useMemo, useReducer } from "react";

import {
  createSpecFirstFlowDraft,
  FLOW_DRAFT_STAGE_REGISTRY,
  getFlowDraftStageDefinition,
  getFlowDraftStageIndex,
  getFlowDraftStageNodeId,
  getInitialFlowDraftSelection,
  type FlowBuilderViewState,
  type FlowDraft,
  type FlowDraftContent,
  type FlowDraftEdge,
  type FlowDraftNode,
  type FlowDraftStageDefinition,
  type FlowDraftStageProgress,
  type FlowDraftSelectionSnapshot,
  type FlowDraftSupportContextSummary,
  type FlowDraftValidationIssue,
  type FlowDraftValidationSummary,
  type FlowDraftValidationSeverity,
  type FlowBuilderMode,
} from "../model/flowDraft";
import { DEFAULT_FLOW_BUILDER_MODE } from "../flowBuilderRoute";

export interface FlowDraftState {
  draft: FlowDraft;
  view: FlowBuilderViewState;
}

export type FlowDraftNodeFieldPatch = Record<string, string>;
export type FlowDraftNodeMoveDirection = "up" | "down";

export type FlowDraftAction =
  | { type: "selectStage"; stageId: FlowDraftStageDefinition["id"] }
  | { type: "selectNode"; nodeId: string }
  | { type: "selectEdge"; edgeId: string | null }
  | { type: "updateNodeFields"; nodeId: string; fields: FlowDraftNodeFieldPatch }
  | { type: "updateDraftFields"; fields: Partial<FlowDraftContent> }
  | { type: "replaceValidationIssues"; issues: FlowDraftValidationIssue[] }
  | { type: "patchValidationIssues"; issues: Array<Partial<FlowDraftValidationIssue> & { id: string }> }
  | { type: "moveNode"; nodeId: string; direction: FlowDraftNodeMoveDirection }
  | { type: "dismissSupportChatDock" }
  | { type: "reopenSupportChatDock" }
  | { type: "toggleSupportChatDock" }
  | { type: "setMode"; mode: FlowBuilderMode };

function cloneFlowDraftNode(node: FlowDraftNode): FlowDraftNode {
  return {
    ...node,
    fields: { ...node.fields },
  };
}

function normalizeValidationIssues(
  issues: FlowDraftValidationIssue[]
): FlowDraftValidationIssue[] {
  const severityRank: Record<FlowDraftValidationSeverity, number> = {
    error: 0,
    warning: 1,
    info: 2,
  };

  return [...issues].sort((left, right) => {
    const severityDelta = severityRank[left.severity] - severityRank[right.severity];
    if (severityDelta !== 0) {
      return severityDelta;
    }

    const stageDelta =
      (getFlowDraftStageIndex(left.stageId ?? FLOW_DRAFT_STAGE_REGISTRY[0].id) ?? 0) -
      (getFlowDraftStageIndex(right.stageId ?? FLOW_DRAFT_STAGE_REGISTRY[0].id) ?? 0);
    if (stageDelta !== 0) {
      return stageDelta;
    }

    const messageDelta = left.message.localeCompare(right.message);
    if (messageDelta !== 0) {
      return messageDelta;
    }

    return left.id.localeCompare(right.id);
  });
}

function upsertValidationIssues(
  existingIssues: FlowDraftValidationIssue[],
  patches: Array<Partial<FlowDraftValidationIssue> & { id: string }>
): FlowDraftValidationIssue[] {
  const nextIssues = [...existingIssues];

  for (const patch of patches) {
    const index = nextIssues.findIndex((issue) => issue.id === patch.id);
    if (index === -1) {
      nextIssues.push({
        id: patch.id,
        severity: patch.severity ?? "warning",
        message: patch.message ?? "Validation issue updated.",
        stageId: patch.stageId,
        nodeId: patch.nodeId,
        fieldPath: patch.fieldPath,
        source: patch.source,
      });
      continue;
    }

    nextIssues[index] = {
      ...nextIssues[index],
      ...patch,
      severity: patch.severity ?? nextIssues[index].severity,
      message: patch.message ?? nextIssues[index].message,
    };
  }

  return normalizeValidationIssues(nextIssues);
}

function moveArrayItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  if (fromIndex === toIndex) {
    return items;
  }

  const nextItems = [...items];
  const [item] = nextItems.splice(fromIndex, 1);
  nextItems.splice(toIndex, 0, item);
  return nextItems;
}

function createSequenceEdges(nodes: FlowDraftNode[]): FlowDraftEdge[] {
  return nodes.slice(0, -1).map((node, index) => ({
    id: `flow-draft-edge:${node.id}->${nodes[index + 1]?.id ?? "unknown"}`,
    kind: "sequence",
    fromNodeId: node.id,
    toNodeId: nodes[index + 1]?.id ?? node.id,
    label: `${node.label} to ${nodes[index + 1]?.label ?? node.label}`,
  }));
}

export function createInitialFlowDraftState(
  initialMode: FlowBuilderMode = DEFAULT_FLOW_BUILDER_MODE,
  now: string = new Date().toISOString()
): FlowDraftState {
  return {
    draft: createSpecFirstFlowDraft(now, { createdFrom: "manual" }),
    view: {
      mode: initialMode,
      selection: getInitialFlowDraftSelection(initialMode),
      supportChatOpen: true,
    },
  };
}

export function flowDraftReducer(
  state: FlowDraftState,
  action: FlowDraftAction
): FlowDraftState {
  switch (action.type) {
    case "selectStage": {
      const selectedNodeId = getFlowDraftStageNodeId(action.stageId);
      return {
        ...state,
        view: {
          ...state.view,
          selection: {
            stageId: action.stageId,
            nodeId: selectedNodeId,
            edgeId: null,
          },
        },
      };
    }

    case "selectNode": {
      const selectedNode = state.draft.nodes.find((node) => node.id === action.nodeId);
      if (!selectedNode) {
        return state;
      }

      return {
        ...state,
        view: {
          ...state.view,
          selection: {
            stageId: selectedNode.stageId ?? state.view.selection.stageId,
            nodeId: selectedNode.id,
            edgeId: null,
          },
        },
      };
    }

    case "selectEdge":
      return {
        ...state,
        view: {
          ...state.view,
          selection: {
            ...state.view.selection,
            edgeId: action.edgeId,
          },
        },
      };

    case "updateNodeFields": {
      const nextNodes = state.draft.nodes.map((node) =>
        node.id === action.nodeId
          ? {
              ...cloneFlowDraftNode(node),
              fields: {
                ...node.fields,
                ...action.fields,
              },
            }
          : cloneFlowDraftNode(node)
      );

      return {
        ...state,
        draft: {
          ...state.draft,
          nodes: nextNodes,
        },
      };
    }

    case "updateDraftFields":
      return {
        ...state,
        draft: {
          ...state.draft,
          content: {
            ...state.draft.content,
            ...action.fields,
          },
        },
      };

    case "replaceValidationIssues":
      return {
        ...state,
        draft: {
          ...state.draft,
          validationIssues: normalizeValidationIssues(action.issues),
        },
      };

    case "patchValidationIssues":
      return {
        ...state,
        draft: {
          ...state.draft,
          validationIssues: upsertValidationIssues(state.draft.validationIssues, action.issues),
        },
      };

    case "moveNode": {
      const fromIndex = state.draft.nodes.findIndex((node) => node.id === action.nodeId);
      if (fromIndex === -1) {
        return state;
      }

      const toIndex =
        action.direction === "up"
          ? Math.max(0, fromIndex - 1)
          : Math.min(state.draft.nodes.length - 1, fromIndex + 1);
      if (fromIndex === toIndex) {
        return state;
      }

      const reordered = moveArrayItem(
        state.draft.nodes.map((node) => cloneFlowDraftNode(node)),
        fromIndex,
        toIndex
      ).map((node, order) => ({
        ...node,
        order,
      }));

      return {
        ...state,
        draft: {
          ...state.draft,
          nodes: reordered,
          edges: createSequenceEdges(reordered),
        },
      };
    }

    case "dismissSupportChatDock":
      return {
        ...state,
        view: {
          ...state.view,
          supportChatOpen: false,
        },
      };

    case "reopenSupportChatDock":
      return {
        ...state,
        view: {
          ...state.view,
          supportChatOpen: true,
        },
      };

    case "toggleSupportChatDock":
      return {
        ...state,
        view: {
          ...state.view,
          supportChatOpen: !state.view.supportChatOpen,
        },
      };

    case "setMode":
      if (state.view.mode === action.mode) {
        return state;
      }

      return {
        ...state,
        view: {
          ...state.view,
          mode: action.mode,
        },
      };

    default:
      return state;
  }
}

export function getGraphVisibleNodes(draft: FlowDraft): FlowDraftNode[] {
  return [...draft.nodes]
    .filter((node) => node.visible !== false)
    .sort((left, right) => left.order - right.order)
    .map((node) => ({ ...node, fields: { ...node.fields } }));
}

export function getCurrentNodeSelection(
  draft: FlowDraft,
  view: FlowBuilderViewState
): FlowDraftSelectionSnapshot {
  const stage = getFlowDraftStageDefinition(view.selection.stageId);
  const node = draft.nodes.find((entry) => entry.id === view.selection.nodeId) ?? null;
  const edge = view.selection.edgeId
    ? draft.edges.find((entry) => entry.id === view.selection.edgeId) ?? null
    : null;

  return {
    stageId: view.selection.stageId,
    nodeId: view.selection.nodeId,
    edgeId: view.selection.edgeId ?? null,
    stage,
    node,
    edge,
  };
}

export function getOrderedStageProgress(
  draft: FlowDraft,
  view: FlowBuilderViewState
): FlowDraftStageProgress[] {
  const selectedIndex = getFlowDraftStageIndex(view.selection.stageId);
  return FLOW_DRAFT_STAGE_REGISTRY.map((stage, index) => {
    const issueCount = draft.validationIssues.filter((issue) => issue.stageId === stage.id).length;
    const state: FlowDraftStageProgress["state"] =
      index < selectedIndex ? "complete" : index === selectedIndex ? "current" : "pending";

    return {
      stage,
      index,
      issueCount,
      state,
      isSelected: stage.id === view.selection.stageId,
    };
  });
}

export function getValidationSummary(draft: FlowDraft): FlowDraftValidationSummary {
  const summary = draft.validationIssues.reduce(
    (accumulator, issue) => {
      accumulator.total += 1;
      if (issue.severity === "error") accumulator.errorCount += 1;
      if (issue.severity === "warning") accumulator.warningCount += 1;
      if (issue.severity === "info") accumulator.infoCount += 1;
      return accumulator;
    },
    {
      total: 0,
      infoCount: 0,
      warningCount: 0,
      errorCount: 0,
    }
  );

  const primarySeverity: FlowDraftValidationSummary["primarySeverity"] =
    summary.errorCount > 0 ? "error" : summary.warningCount > 0 ? "warning" : summary.infoCount > 0 ? "info" : "none";

  const label =
    summary.total === 0
      ? "No validation issues"
      : summary.errorCount > 0
        ? `${summary.errorCount} error${summary.errorCount === 1 ? "" : "s"}`
        : summary.warningCount > 0
          ? `${summary.warningCount} warning${summary.warningCount === 1 ? "" : "s"}`
          : `${summary.infoCount} note${summary.infoCount === 1 ? "" : "s"}`;

  return {
    ...summary,
    label,
    primarySeverity,
  };
}

export function getSupportChatContextSummary(
  draft: FlowDraft,
  view: FlowBuilderViewState
): FlowDraftSupportContextSummary {
  const selection = getCurrentNodeSelection(draft, view);
  const validationSummary = getValidationSummary(draft);
  const provenance = draft.meta.provenance;

  return {
    draftTitle: draft.meta.title,
    modeLabel: view.mode === "expertise" ? "Expertise" : "Process",
    selectedStageLabel: selection.stage.label,
    selectedNodeLabel: selection.node?.label ?? selection.stage.label,
    validationLabel: validationSummary.label,
    provenanceLabel: provenance?.originThreadId
      ? `Origin thread ${provenance.originThreadId}`
      : provenance?.createdFrom
        ? `Created from ${provenance.createdFrom.replace("-", " ")}`
        : "No thread binding",
    dockStateLabel: view.supportChatOpen ? "Open" : "Dismissed",
  };
}

export interface FlowDraftActions {
  selectStage: (stageId: FlowDraftStageDefinition["id"]) => void;
  selectNode: (nodeId: string) => void;
  selectEdge: (edgeId: string | null) => void;
  updateNodeFields: (nodeId: string, fields: FlowDraftNodeFieldPatch) => void;
  updateDraftFields: (fields: Partial<FlowDraftContent>) => void;
  replaceValidationIssues: (issues: FlowDraftValidationIssue[]) => void;
  patchValidationIssues: (issues: Array<Partial<FlowDraftValidationIssue> & { id: string }>) => void;
  moveNode: (nodeId: string, direction: FlowDraftNodeMoveDirection) => void;
  dismissSupportChatDock: () => void;
  reopenSupportChatDock: () => void;
  toggleSupportChatDock: () => void;
  setMode: (mode: FlowBuilderMode) => void;
}

export function useFlowDraftState(initialMode: FlowBuilderMode = DEFAULT_FLOW_BUILDER_MODE) {
  const [state, dispatch] = useReducer(flowDraftReducer, initialMode, createInitialFlowDraftState);

  const actions = useMemo<FlowDraftActions>(
    () => ({
      selectStage: (stageId) => dispatch({ type: "selectStage", stageId }),
      selectNode: (nodeId) => dispatch({ type: "selectNode", nodeId }),
      selectEdge: (edgeId) => dispatch({ type: "selectEdge", edgeId }),
      updateNodeFields: (nodeId, fields) =>
        dispatch({ type: "updateNodeFields", nodeId, fields }),
      updateDraftFields: (fields) => dispatch({ type: "updateDraftFields", fields }),
      replaceValidationIssues: (issues) =>
        dispatch({ type: "replaceValidationIssues", issues }),
      patchValidationIssues: (issues) => dispatch({ type: "patchValidationIssues", issues }),
      moveNode: (nodeId, direction) => dispatch({ type: "moveNode", nodeId, direction }),
      dismissSupportChatDock: () => dispatch({ type: "dismissSupportChatDock" }),
      reopenSupportChatDock: () => dispatch({ type: "reopenSupportChatDock" }),
      toggleSupportChatDock: () => dispatch({ type: "toggleSupportChatDock" }),
      setMode: (mode) => dispatch({ type: "setMode", mode }),
    }),
    []
  );

  const derived = useMemo(
    () => ({
      currentSelection: getCurrentNodeSelection(state.draft, state.view),
      graphVisibleNodes: getGraphVisibleNodes(state.draft),
      orderedStageProgress: getOrderedStageProgress(state.draft, state.view),
      validationSummary: getValidationSummary(state.draft),
      supportChatContext: getSupportChatContextSummary(state.draft, state.view),
    }),
    [state.draft, state.view]
  );

  return {
    state,
    draft: state.draft,
    view: state.view,
    actions,
    derived,
  };
}
