import type { FlowBuilderMode } from "./flowBuilderRoute";

export type FlowBuilderExpertiseDraft = {
  sourceMode: Extract<FlowBuilderMode, "expertise">;
  title: string;
  status: "draft-only";
  runtimeSupport: "none";
  objective: string;
  assumptions: string;
  unknowns: string;
  validationQuestions: string;
};

export function createFlowBuilderExpertiseDraft(): FlowBuilderExpertiseDraft {
  return {
    sourceMode: "expertise",
    title: "Draft specification",
    status: "draft-only",
    runtimeSupport: "none",
    objective:
      "Describe the desired outcome, domain vocabulary, and scope before any runnable path is considered.",
    assumptions:
      "List what is being inferred from expertise versus what still needs confirmation.",
    unknowns:
      "Record missing steps, unresolved dependencies, and any boundary that needs review.",
    validationQuestions:
      "Write the questions that must be answered before this draft can be considered stable.",
  };
}
