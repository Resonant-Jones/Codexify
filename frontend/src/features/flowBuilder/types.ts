/**
 * Flow Builder Shell Fixture Types
 *
 * These are frontend-only TypeScript types for fixture rendering of the
 * future Flow Builder authoring and proof-surface concepts.
 *
 * NOT backend API contracts. NOT runtime truth. NOT canonical token registries.
 * These types support fixture-only UI prototyping.
 *
 * Do not import these as runtime data contracts.
 * Do not export these as canonical runtime tokens.
 */

import type {
  FlowDraftStageId,
  FlowDraftValidationSeverity,
} from "./model/flowDraft";

/**
 * Fixture type for a FlowDraft artifact.
 * Mirrors candidate ADR-014/ADR-027 contract shape for UI rendering.
 */
export interface FlowDraftFixture {
  id: string;
  title: string;
  status: string;
  runtimeSupport: string;
  createdAt: string;
  updatedAt: string;
  provenance: FlowDraftProvenanceFixture;
}

/**
 * Fixture provenance reference for FlowDraft.
 */
export interface FlowDraftProvenanceFixture {
  originThreadId?: string;
  originMessageId?: string;
  createdFrom?: string;
}

/**
 * Fixture type for a Flow Starter.
 * Mirrors candidate ADR-006/ADR-027 starter_kind concept.
 */
export interface FlowStarterFixture {
  id: string;
  kind: "manual" | "schedule" | "event";
  label: string;
  config: Record<string, unknown>;
}

/**
 * Fixture type for a Flow Step.
 * Mirrors candidate ADR-027 ActionStep and SemanticStep concepts.
 */
export interface FlowStepFixture {
  id: string;
  kind: "command" | "semantic" | "conditional" | "transform" | "notification" | "document" | "task";
  label: string;
  position: number;
  config: Record<string, unknown>;
  inputBindings: VariableBindingFixture[];
  outputDefinitions: TypedStepOutputFixture[];
  validationState: string;
}

/**
 * Fixture type for a typed step output.
 * Mirrors candidate FB-003 TypedStepOutput contract.
 */
export interface TypedStepOutputFixture {
  id: string;
  sourceRef: string;
  name: string;
  displayLabel: string;
  valueType: VariableValueTypeFixture;
  cardinality: "single" | "optional" | "list";
  nullable: boolean;
  sensitive: boolean;
}

/**
 * Fixture type for a variable chip.
 * Mirrors candidate FB-003 VariableChip concept.
 */
export interface VariableChipFixture {
  outputId: string;
  sourceRef: string;
  displayLabel: string;
  valueType: VariableValueTypeFixture;
  iconHint?: string;
  scope: VariableBindingScopeFixture;
  compatibilitySummary: string;
  sensitive: boolean;
}

/**
 * Fixture type for a variable binding.
 * Mirrors candidate FB-003 VariableBinding contract.
 */
export interface VariableBindingFixture {
  id: string;
  consumerRef: string;
  consumerField: string;
  outputRef: string;
  scope: VariableBindingScopeFixture;
  path: string;
  valueType: VariableValueTypeFixture;
  required: boolean;
}

/**
 * Fixture variable value types.
 * Mirrors candidate flow-builder-token-domains.md variable_value_type domain.
 */
export type VariableValueTypeFixture =
  | "text"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "email_address"
  | "url"
  | "document_ref"
  | "file_ref"
  | "person_ref"
  | "json_object"
  | "list";

/**
 * Fixture variable binding scopes.
 * Mirrors candidate flow-builder-token-domains.md variable_binding_scope domain.
 */
export type VariableBindingScopeFixture =
  | "starter"
  | "step_output"
  | "flow_input"
  | "system";

/**
 * Fixture validation issue.
 * Mirrors candidate FB-004 ValidationIssue contract.
 */
export interface ValidationIssueFixture {
  id: string;
  code: ValidationIssueCodeFixture;
  severity: ValidationSeverityFixture;
  scope: "flow" | "starter" | "step" | "variable_binding" | "typed_output" | "conditional_container";
  targetRef: string;
  message: string;
  blocking: boolean;
  createdAt: string;
}

/**
 * Fixture validation issue codes.
 * Mirrors candidate flow-builder-token-domains.md validation_issue_code domain.
 */
export type ValidationIssueCodeFixture =
  | "missing_required_field"
  | "incompatible_variable_type"
  | "missing_substep"
  | "inaccessible_resource"
  | "deleted_or_unavailable_reference"
  | "unsupported_manual_value"
  | "permission_risk"
  | "unknown_semantic_output"
  | "receipt_required"
  | "invalid_token_value";

/**
 * Fixture validation severity levels.
 * Mirrors candidate flow-builder-token-domains.md validation_severity domain.
 */
export type ValidationSeverityFixture = "info" | "warning" | "error" | "blocking";

/**
 * Fixture validation summary.
 * Aggregates validation issues for a draft.
 */
export interface ValidationSummaryFixture {
  state: ValidationSeverityFixture;
  eligibleForTestRun: boolean;
  eligibleForActivation: boolean;
  issues: ValidationIssueFixture[];
  blockingCount: number;
  warningCount: number;
  validatedAt: string;
  validatorVersion: string;
}

/**
 * Fixture semantic step config.
 * Mirrors candidate FB-005 SemanticStep contract.
 */
export interface SemanticStepConfigFixture {
  semanticStepKind: SemanticStepKindFixture;
  instruction: string;
  inputBindings: VariableBindingFixture[];
  outputDefinitions: TypedStepOutputFixture[];
  uncertaintyPolicy: UncertaintyPolicyFixture;
}

/**
 * Fixture semantic step kinds.
 * Mirrors candidate flow-builder-token-domains.md semantic_step_kind domain.
 */
export type SemanticStepKindFixture =
  | "extract"
  | "classify"
  | "summarize"
  | "decide"
  | "transform"
  | "route";

/**
 * Fixture uncertainty policy for semantic steps.
 */
export interface UncertaintyPolicyFixture {
  knownBehavior: string;
  unknownBehavior: string;
  lowConfidenceBehavior: string;
  insufficientEvidenceBehavior: string;
}

/**
 * Fixture conditional container.
 * Mirrors candidate FB-006 ConditionalContainer contract.
 */
export interface ConditionalContainerFixture {
  id: string;
  kind: "conditional";
  label: string;
  position: number;
  condition: ConditionExpressionFixture;
  substeps: FlowStepFixture[];
  elseSubsteps: FlowStepFixture[];
  validationState: string;
}

/**
 * Fixture condition expression.
 * Mirrors candidate FB-006 ConditionExpression contract.
 */
export interface ConditionExpressionFixture {
  id: string;
  lhs: string;
  operator: ConditionalOperatorFixture;
  rhs?: string;
  conjunction?: "and" | "or";
  negated: boolean;
  valueType: VariableValueTypeFixture;
}

/**
 * Fixture conditional operators.
 * Mirrors candidate flow-builder-token-domains.md conditional_operator domain.
 */
export type ConditionalOperatorFixture =
  | "is_true"
  | "is_false"
  | "equals"
  | "not_equals"
  | "contains"
  | "not_contains"
  | "greater_than"
  | "less_than"
  | "exists"
  | "is_empty";

/**
 * Fixture TestRun summary.
 * Mirrors candidate FB-007 TestRun contract.
 */
export interface TestRunSummaryFixture {
  id: string;
  flowDraftId: string;
  state: TestRunStateFixture;
  initiatedByUserId: string;
  validationSnapshotRef: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  failureReason?: string;
}

/**
 * Fixture TestRun states.
 * Mirrors candidate flow-builder-token-domains.md test_run_state domain.
 */
export type TestRunStateFixture =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/**
 * Fixture Activation summary.
 * Mirrors candidate FB-007 Activation contract.
 */
export interface ActivationSummaryFixture {
  id: string;
  flowDraftId: string;
  state: ActivationStateFixture;
  activatedByUserId: string;
  starterRef: string;
  validationSnapshotRef: string;
  createdAt: string;
  activatedAt?: string;
  pausedAt?: string;
  disabledAt?: string;
  failureReason?: string;
}

/**
 * Fixture Activation states.
 * Mirrors candidate flow-builder-token-domains.md activation_state domain.
 */
export type ActivationStateFixture =
  | "inactive"
  | "active"
  | "paused"
  | "disabled"
  | "error";

/**
 * Fixture RunReceipt summary.
 * Mirrors candidate FB-008 RunReceipt contract.
 */
export interface RunReceiptSummaryFixture {
  id: string;
  flowDraftId: string;
  testRunId?: string;
  activationId?: string;
  initiatorRef: string;
  triggerRef?: string;
  state: RunReceiptStateFixture;
  validationSnapshotRef: string;
  permissionSnapshotRef: string;
  stepReceiptRefs: StepReceiptSummaryFixture[];
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  failureReason?: string;
}

/**
 * Fixture RunReceipt states.
 * Mirrors candidate flow-builder-token-domains.md run_receipt_state domain.
 */
export type RunReceiptStateFixture =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "blocked";

/**
 * Fixture StepReceipt summary.
 * Mirrors candidate FB-008 StepReceipt contract.
 */
export interface StepReceiptSummaryFixture {
  id: string;
  runReceiptId: string;
  sourceStepRef: string;
  sourceBranchRef?: string;
  state: StepReceiptStateFixture;
  inputRefs: string[];
  outputRefs: string[];
  valueSummary: string;
  semanticMetadata?: SemanticMetadataFixture;
  conditionMetadata?: ConditionMetadataFixture;
  sideEffectRefs: string[];
  startedAt?: string;
  completedAt?: string;
  skippedAt?: string;
  failureReason?: string;
}

/**
 * Fixture StepReceipt states.
 * Mirrors candidate flow-builder-token-domains.md step_receipt_state domain.
 */
export type StepReceiptStateFixture =
  | "pending"
  | "running"
  | "skipped"
  | "completed"
  | "failed"
  | "blocked";

/**
 * Fixture semantic metadata for step receipts.
 */
export interface SemanticMetadataFixture {
  semanticStepKind: SemanticStepKindFixture;
  uncertaintyOutcome: UncertaintyOutcomeFixture;
  modelPolicyRef?: string;
  allowedSourcesSnapshot?: string;
  redactionSummary?: string;
  failureReason?: string;
}

/**
 * Fixture uncertainty outcomes for semantic steps.
 * Mirrors candidate flow-builder-token-domains.md semantic_uncertainty_outcome domain.
 */
export type UncertaintyOutcomeFixture =
  | "known"
  | "unknown"
  | "low_confidence"
  | "insufficient_evidence";

/**
 * Fixture condition metadata for branch receipts.
 */
export interface ConditionMetadataFixture {
  conditionRef: string;
  conditionResult: boolean;
  evaluatedInputs: string[];
  selectedBranch: "then" | "else";
  skippedStepRefs: string[];
  executedStepRefs: string[];
  uncertaintyOutcome?: UncertaintyOutcomeFixture;
}

/**
 * Fixture ActivityEvent for the proof surface.
 * Mirrors candidate FB-009 proof surface event types.
 * These are candidate UI/activity labels only until promoted into canonical registries.
 */
export interface ActivityEventFixture {
  id: string;
  type: ActivityEventTypeFixture;
  timestamp: string;
  origin: string;
  state: string;
  evidenceRef?: string;
  message: string;
}

/**
 * Fixture activity event types.
 * Candidate UI labels only until promoted into canonical token registries.
 */
export type ActivityEventTypeFixture =
  | "draft_created"
  | "draft_validated"
  | "test_run_started"
  | "test_run_completed"
  | "test_run_failed"
  | "activation_created"
  | "activation_paused"
  | "activation_disabled"
  | "run_started"
  | "run_completed"
  | "run_failed"
  | "run_cancelled"
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "step_skipped"
  | "permission_warning"
  | "side_effect_recorded"
  | "receipt_persisted"
  | "receipt_degraded";

/**
 * Complete Flow Builder fixture shell payload.
 * Aggregates all fixture types for the prototype shell.
 */
export interface FlowBuilderFixtureData {
  draft: FlowDraftFixture;
  starter: FlowStarterFixture;
  steps: FlowStepFixture[];
  conditionalContainer?: ConditionalContainerFixture;
  typedOutputs: TypedStepOutputFixture[];
  variableChips: VariableChipFixture[];
  variableBindings: VariableBindingFixture[];
  validationSummary: ValidationSummaryFixture;
  testRunSummary?: TestRunSummaryFixture;
  activationSummary?: ActivationSummaryFixture;
  runReceiptSummary?: RunReceiptSummaryFixture;
  stepReceiptSummaries: StepReceiptSummaryFixture[];
  activityEvents: ActivityEventFixture[];
}