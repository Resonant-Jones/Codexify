import {
  FLOW_DRAFT_INITIAL_RUNTIME_SUPPORT,
  FLOW_DRAFT_INITIAL_STATUS,
  FLOW_DRAFT_INITIAL_TITLE,
  type FlowDraftContent,
  type FlowDraftRuntimeSupport,
  type FlowDraftLifecycleStatus,
  createSpecFirstFlowDraft,
} from "./model/flowDraft";

export type FlowBuilderExpertiseDraft = {
  sourceMode: "expertise";
  title: string;
  status: FlowDraftLifecycleStatus;
  runtimeSupport: FlowDraftRuntimeSupport;
  objective: string;
  assumptions: string;
  unknowns: string;
  validationQuestions: string;
};

export function createFlowBuilderExpertiseDraft(): FlowBuilderExpertiseDraft {
  const draft = createSpecFirstFlowDraft();
  return {
    sourceMode: "expertise",
    title: FLOW_DRAFT_INITIAL_TITLE,
    status: FLOW_DRAFT_INITIAL_STATUS,
    runtimeSupport: FLOW_DRAFT_INITIAL_RUNTIME_SUPPORT,
    objective: draft.content.objective,
    assumptions: draft.content.assumptions,
    unknowns: draft.content.unknowns,
    validationQuestions: draft.content.validationQuestions,
  };
}

export type { FlowDraftContent };
