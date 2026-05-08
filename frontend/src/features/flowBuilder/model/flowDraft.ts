import type { FlowBuilderMode } from "../flowBuilderRoute";

export type FlowDraftStageId =
  | "select-source"
  | "define-constraints"
  | "set-outcomes"
  | "add-steps"
  | "insert-conditions"
  | "validation-gates"
  | "review-validate";

export type FlowDraftNodeKind = "stage" | "summary" | "validation" | "support";
export type FlowDraftEdgeKind = "sequence" | "dependency" | "note";
export type FlowDraftValidationSeverity = "info" | "warning" | "error";
export type FlowDraftLifecycleStatus = "draft-only";
export type FlowDraftRuntimeSupport = "none";
export type FlowDraftCreationOrigin =
  | "manual"
  | "stage-rail"
  | "graph-edit"
  | "assistant-suggestion";

export interface FlowDraftStageDefinition {
  id: FlowDraftStageId;
  order: number;
  label: string;
  description: string;
  chip: string;
}

export const FLOW_DRAFT_STAGE_REGISTRY = [
  {
    id: "select-source",
    order: 0,
    label: "Select Source",
    description: "Choose the input seam that should anchor the first draft.",
    chip: "01",
  },
  {
    id: "define-constraints",
    order: 1,
    label: "Define Constraints",
    description: "Set the bounds, limits, and non-negotiables that shape the draft.",
    chip: "02",
  },
  {
    id: "set-outcomes",
    order: 2,
    label: "Set Outcomes",
    description: "Name the intended result before the flow starts to harden.",
    chip: "03",
  },
  {
    id: "add-steps",
    order: 3,
    label: "Add Steps",
    description: "Lay out the explicit steps that make the plan inspectable.",
    chip: "04",
  },
  {
    id: "insert-conditions",
    order: 4,
    label: "Insert Conditions",
    description: "Mark the branch points where the draft needs a choice or guardrail.",
    chip: "05",
  },
  {
    id: "validation-gates",
    order: 5,
    label: "Validation Gates",
    description: "Keep the checks visible so unresolved edges stay honest.",
    chip: "06",
  },
  {
    id: "review-validate",
    order: 6,
    label: "Review & Validate",
    description: "Shape the handoff into a readable artifact for review.",
    chip: "07",
  },
] as const satisfies readonly FlowDraftStageDefinition[];

export type FlowDraftStageRegistry = typeof FLOW_DRAFT_STAGE_REGISTRY;

export interface FlowDraftProvenanceRef {
  originThreadId?: string;
  originMessageId?: string;
  originRequestId?: string;
  createdFrom?: FlowDraftCreationOrigin;
}

export interface FlowDraftMeta {
  id: string;
  title: string;
  status: FlowDraftLifecycleStatus;
  runtimeSupport: FlowDraftRuntimeSupport;
  createdAt: string;
  updatedAt: string;
  provenance?: FlowDraftProvenanceRef;
}

export interface FlowDraftContent {
  objective: string;
  assumptions: string;
  unknowns: string;
  validationQuestions: string;
}

export interface FlowDraftNode {
  id: string;
  kind: FlowDraftNodeKind;
  stageId?: FlowDraftStageId;
  label: string;
  summary: string;
  order: number;
  fields: Record<string, string>;
  visible?: boolean;
  provenance?: FlowDraftProvenanceRef;
}

export interface FlowDraftEdge {
  id: string;
  kind: FlowDraftEdgeKind;
  fromNodeId: string;
  toNodeId: string;
  label: string;
  visible?: boolean;
  provenance?: FlowDraftProvenanceRef;
}

export interface FlowDraftSelection {
  stageId: FlowDraftStageId;
  nodeId: string;
  edgeId?: string | null;
}

export interface FlowDraftValidationIssue {
  id: string;
  severity: FlowDraftValidationSeverity;
  message: string;
  stageId?: FlowDraftStageId;
  nodeId?: string;
  fieldPath?: string;
  source?: string;
}

export interface FlowDraft {
  meta: FlowDraftMeta;
  content: FlowDraftContent;
  nodes: FlowDraftNode[];
  edges: FlowDraftEdge[];
  validationIssues: FlowDraftValidationIssue[];
}

export interface FlowBuilderViewState {
  mode: FlowBuilderMode;
  selection: FlowDraftSelection;
  supportChatOpen: boolean;
}

export interface FlowDraftValidationSummary {
  total: number;
  infoCount: number;
  warningCount: number;
  errorCount: number;
  label: string;
  primarySeverity: FlowDraftValidationSeverity | "none";
}

export interface FlowDraftStageProgress {
  stage: FlowDraftStageDefinition;
  index: number;
  issueCount: number;
  state: "complete" | "current" | "pending";
  isSelected: boolean;
}

export interface FlowDraftSelectionSnapshot {
  stageId: FlowDraftStageId;
  nodeId: string | null;
  edgeId: string | null;
  stage: FlowDraftStageDefinition;
  node: FlowDraftNode | null;
  edge: FlowDraftEdge | null;
}

export interface FlowDraftSupportContextSummary {
  draftTitle: string;
  modeLabel: string;
  selectedStageLabel: string;
  selectedNodeLabel: string;
  validationLabel: string;
  provenanceLabel: string;
  dockStateLabel: string;
}

export const FLOW_DRAFT_INITIAL_TITLE = "Draft specification";
export const FLOW_DRAFT_INITIAL_STATUS: FlowDraftLifecycleStatus = "draft-only";
export const FLOW_DRAFT_INITIAL_RUNTIME_SUPPORT: FlowDraftRuntimeSupport = "none";
export const FLOW_DRAFT_DEFAULT_CONTENT: FlowDraftContent = {
  objective:
    "Describe the desired outcome, domain vocabulary, and scope before any runnable path is considered.",
  assumptions:
    "List what is being inferred from expertise versus what still needs confirmation.",
  unknowns:
    "Record missing steps, unresolved dependencies, and any boundary that needs review.",
  validationQuestions:
    "Write the questions that must be answered before this draft can be considered stable.",
};

export function getFlowDraftStageDefinition(stageId: FlowDraftStageId): FlowDraftStageDefinition {
  const stage = FLOW_DRAFT_STAGE_REGISTRY.find((entry) => entry.id === stageId);
  if (!stage) {
    return FLOW_DRAFT_STAGE_REGISTRY[0];
  }

  return stage;
}

export function getFlowDraftStageNodeId(stageId: FlowDraftStageId): string {
  return `flow-draft-stage-node:${stageId}`;
}

export function getFlowDraftStageIndex(stageId: FlowDraftStageId): number {
  return FLOW_DRAFT_STAGE_REGISTRY.findIndex((entry) => entry.id === stageId);
}

export function getInitialFlowDraftSelection(mode: FlowBuilderMode): FlowDraftSelection {
  const stageId: FlowDraftStageId =
    mode === "expertise" ? "define-constraints" : FLOW_DRAFT_STAGE_REGISTRY[0].id;

  return {
    stageId,
    nodeId: getFlowDraftStageNodeId(stageId),
    edgeId: null,
  };
}

function createFlowDraftStageNodes(
  content: FlowDraftContent,
  provenance: FlowDraftProvenanceRef | undefined
): FlowDraftNode[] {
  return FLOW_DRAFT_STAGE_REGISTRY.map((stage) => {
    const fieldSeed =
      stage.id === "select-source"
        ? {
            source: "Build from process or build from expertise.",
          }
        : stage.id === "define-constraints"
          ? {
              objective: content.objective,
              assumptions: content.assumptions,
            }
          : stage.id === "set-outcomes"
            ? {
                outcome: "Keep the intended result visible before the draft hardens.",
              }
            : stage.id === "add-steps"
              ? {
                  steps: "Lay out the explicit steps that make the plan inspectable.",
                }
              : stage.id === "insert-conditions"
                ? {
                    conditions: "Mark branches and guardrails instead of hiding them.",
                  }
                : stage.id === "validation-gates"
                  ? {
                      validationQuestions: content.validationQuestions,
                    }
                  : {
                      review: "Keep the handoff readable and draft-only.",
                    };

    return {
      id: getFlowDraftStageNodeId(stage.id),
      kind: "stage",
      stageId: stage.id,
      label: stage.label,
      summary: stage.description,
      order: stage.order,
      fields: fieldSeed,
      provenance,
    };
  });
}

function createFlowDraftEdges(nodes: FlowDraftNode[]): FlowDraftEdge[] {
  return nodes.slice(0, -1).map((node, index) => ({
    id: `flow-draft-edge:${node.id}->${nodes[index + 1]?.id ?? "unknown"}`,
    kind: "sequence",
    fromNodeId: node.id,
    toNodeId: nodes[index + 1]?.id ?? node.id,
    label: `${node.label} to ${nodes[index + 1]?.label ?? node.label}`,
  }));
}

export function createSpecFirstFlowDraft(
  now: string = new Date().toISOString(),
  provenance?: FlowDraftProvenanceRef
): FlowDraft {
  const normalizedProvenance = provenance ?? { createdFrom: "manual" };
  const content = { ...FLOW_DRAFT_DEFAULT_CONTENT };
  const nodes = createFlowDraftStageNodes(content, normalizedProvenance);

  return {
    meta: {
      id: "flow-draft:spec-first",
      title: FLOW_DRAFT_INITIAL_TITLE,
      status: FLOW_DRAFT_INITIAL_STATUS,
      runtimeSupport: FLOW_DRAFT_INITIAL_RUNTIME_SUPPORT,
      createdAt: now,
      updatedAt: now,
      provenance: normalizedProvenance,
    },
    content,
    nodes,
    edges: createFlowDraftEdges(nodes),
    validationIssues: [
      {
        id: "flow-draft-validation:spec-first-warning",
        severity: "warning",
        message: "This draft is still spec-first; execution remains out of scope.",
        stageId: "review-validate",
        source: "initial-seed",
      },
    ],
  };
}
