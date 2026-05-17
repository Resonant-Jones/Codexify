/**
 * Flow Builder Shell Feature
 *
 * Frontend-only fixture-backed prototype for future Flow Builder
 * authoring and proof-surface concepts.
 *
 * NOT backend API. NOT runtime truth. NOT release support.
 */

export { FlowBuilderShell, type FlowBuilderShellProps } from "./FlowBuilderShell";
export { flowBuilderFixture } from "./fixtures";
export type {
  FlowBuilderFixtureData,
  FlowDraftFixture,
  FlowStarterFixture,
  FlowStepFixture,
  TypedStepOutputFixture,
  VariableChipFixture,
  VariableBindingFixture,
  ValidationSummaryFixture,
  ValidationIssueFixture,
  ConditionalContainerFixture,
  TestRunSummaryFixture,
  ActivationSummaryFixture,
  RunReceiptSummaryFixture,
  StepReceiptSummaryFixture,
  ActivityEventFixture,
} from "./types";