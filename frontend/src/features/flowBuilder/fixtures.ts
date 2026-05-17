/**
 * Flow Builder Shell Fixtures
 *
 * Fixture data for the future Flow Builder authoring and proof-surface prototype.
 *
 * This file contains representative fixture data only. It is not runtime proof.
 * Do not use this fixture data as implementation evidence.
 * Do not include real secrets, credentials, real user data, or real external identifiers.
 *
 * All data in this file is fabricated for UI prototyping purposes only.
 */

import type {
  FlowBuilderFixtureData,
  FlowDraftFixture,
  FlowStarterFixture,
  FlowStepFixture,
  TypedStepOutputFixture,
  VariableChipFixture,
  VariableBindingFixture,
  ValidationSummaryFixture,
  ValidationIssueFixture,
  SemanticStepConfigFixture,
  ConditionalContainerFixture,
  ConditionExpressionFixture,
  TestRunSummaryFixture,
  ActivationSummaryFixture,
  RunReceiptSummaryFixture,
  StepReceiptSummaryFixture,
  ActivityEventFixture,
  UncertaintyOutcomeFixture,
  ConditionMetadataFixture,
  SemanticMetadataFixture,
} from "./types";

/**
 * Sample FlowDraft fixture.
 * Mirrors candidate ADR-014/ADR-027 contract shape.
 */
const sampleFlowDraft: FlowDraftFixture = {
  id: "flow-draft:sample-001",
  title: "Lead Qualification Flow",
  status: "validated",
  runtimeSupport: "none",
  createdAt: "2026-05-10T14:30:00Z",
  updatedAt: "2026-05-15T09:45:00Z",
  provenance: {
    originThreadId: "thread:sample-thread-001",
    originMessageId: "msg:sample-message-001",
    createdFrom: "assistant-suggestion",
  },
};

/**
 * Sample manual starter fixture.
 * Mirrors candidate ADR-006/ADR-027 starter_kind concept.
 */
const sampleStarter: FlowStarterFixture = {
  id: "starter:sample-001",
  kind: "manual",
  label: "Manual trigger",
  config: {
    description: "Triggered manually via Flow Builder shell prototype.",
    requiresApproval: false,
  },
};

/**
 * Sample semantic extract step.
 * Mirrors candidate FB-005 SemanticStep contract with extract kind.
 */
const extractStep: FlowStepFixture = {
  id: "step:extract-leads-001",
  kind: "semantic",
  label: "Extract lead fields",
  position: 1,
  config: {
    semanticStepKind: "extract",
    instruction:
      "Extract contact name, company, email, and qualification score from the provided lead data.",
    inputBindings: [],
    outputDefinitions: [],
    uncertaintyPolicy: {
      knownBehavior: "Return extracted fields with confidence markers.",
      unknownBehavior: "Mark field as unknown and continue.",
      lowConfidenceBehavior: "Return with low_confidence marker.",
      insufficientEvidenceBehavior: "Mark all fields as insufficient_evidence.",
    },
  } as SemanticStepConfigFixture,
  inputBindings: [],
  outputDefinitions: [],
  validationState: "valid",
};

/**
 * Sample semantic summarize step.
 * Mirrors candidate FB-005 SemanticStep contract with summarize kind.
 */
const summarizeStep: FlowStepFixture = {
  id: "step:summarize-qualification-001",
  kind: "semantic",
  label: "Summarize qualification reasoning",
  position: 2,
  config: {
    semanticStepKind: "summarize",
    instruction:
      "Summarize the qualification reasoning and key signals that led to the current score.",
    inputBindings: [],
    outputDefinitions: [],
    uncertaintyPolicy: {
      knownBehavior: "Return concise summary.",
      unknownBehavior: "Return unknown summary placeholder.",
      lowConfidenceBehavior: "Return summary with caveats.",
      insufficientEvidenceBehavior: "Return insufficient evidence notice.",
    },
  } as SemanticStepConfigFixture,
  inputBindings: [],
  outputDefinitions: [],
  validationState: "valid",
};

/**
 * Sample conditional step.
 * Keeps the ordered step list at four top-level steps.
 */
const conditionalStep: FlowStepFixture = {
  id: "step:score-check-001",
  kind: "conditional",
  label: "High score check",
  position: 3,
  config: {
    conditionalContainerId: "container:score-check-001",
  },
  inputBindings: [],
  outputDefinitions: [],
  validationState: "valid",
};

/**
 * Sample conditional container with then-substeps.
 */
const conditionalContainer: ConditionalContainerFixture = {
  id: "container:score-check-001",
  kind: "conditional",
  label: "High score check",
  position: 3,
  condition: {
    id: "condition:score-gte-70",
    lhs: "step:extract-leads-001.output.qualification_score",
    operator: "greater_than",
    rhs: "70",
    negated: false,
    valueType: "number",
  } as ConditionExpressionFixture,
  substeps: [
    {
      id: "step:notify-high-priority-001",
      kind: "notification",
      label: "Notify sales team",
      position: 0,
      config: {
        notificationType: "slack",
        channel: "#sales-leads",
        messageTemplate:
          "High-priority lead detected: {{contact_name}} at {{company}}",
      },
      inputBindings: [],
      outputDefinitions: [],
      validationState: "valid",
    },
  ],
  elseSubsteps: [
    {
      id: "step:log-low-priority-001",
      kind: "document",
      label: "Log to low-priority queue",
      position: 0,
      config: {
        action: "log_entry",
        target: "lead_queue",
        entryTemplate:
          "Low-priority lead: {{contact_name}} - score {{qualification_score}}",
      },
      inputBindings: [],
      outputDefinitions: [],
      validationState: "valid",
    },
  ],
  validationState: "valid",
};

/**
 * Sample notification action step.
 */
const notificationStep: FlowStepFixture = {
  id: "step:send-summary-001",
  kind: "notification",
  label: "Send qualification summary",
  position: 4,
  config: {
    notificationType: "email",
    recipientTemplate: "{{contact_email}}",
    subjectTemplate: "Lead qualification complete: {{contact_name}}",
    bodyTemplate:
      "Your lead {{contact_name}} at {{company}} has been qualified with score {{qualification_score}}.",
  },
  inputBindings: [],
  outputDefinitions: [],
  validationState: "valid",
};

/**
 * Sample typed step outputs.
 * Mirrors candidate FB-003 TypedStepOutput contract.
 */
const sampleTypedOutputs: TypedStepOutputFixture[] = [
  {
    id: "output:extract-contact-name-001",
    sourceRef: "step:extract-leads-001",
    name: "contact_name",
    displayLabel: "Contact Name",
    valueType: "text",
    cardinality: "single",
    nullable: false,
    sensitive: false,
  },
  {
    id: "output:extract-company-001",
    sourceRef: "step:extract-leads-001",
    name: "company",
    displayLabel: "Company",
    valueType: "text",
    cardinality: "single",
    nullable: false,
    sensitive: false,
  },
  {
    id: "output:extract-email-001",
    sourceRef: "step:extract-leads-001",
    name: "email",
    displayLabel: "Email Address",
    valueType: "email_address",
    cardinality: "single",
    nullable: false,
    sensitive: true,
  },
  {
    id: "output:extract-score-001",
    sourceRef: "step:extract-leads-001",
    name: "qualification_score",
    displayLabel: "Qualification Score",
    valueType: "number",
    cardinality: "single",
    nullable: false,
    sensitive: false,
  },
  {
    id: "output:summarize-reasoning-001",
    sourceRef: "step:summarize-qualification-001",
    name: "reasoning_summary",
    displayLabel: "Reasoning Summary",
    valueType: "text",
    cardinality: "single",
    nullable: false,
    sensitive: false,
  },
];

/**
 * Sample variable chips.
 * Mirrors candidate FB-003 VariableChip concept.
 */
const sampleVariableChips: VariableChipFixture[] = [
  {
    outputId: "output:extract-contact-name-001",
    sourceRef: "step:extract-leads-001",
    displayLabel: "Contact Name",
    valueType: "text",
    iconHint: "user",
    scope: "step_output",
    compatibilitySummary: "Compatible with text input fields",
    sensitive: false,
  },
  {
    outputId: "output:extract-company-001",
    sourceRef: "step:extract-leads-001",
    displayLabel: "Company",
    valueType: "text",
    iconHint: "building",
    scope: "step_output",
    compatibilitySummary: "Compatible with text input fields",
    sensitive: false,
  },
  {
    outputId: "output:extract-email-001",
    sourceRef: "step:extract-leads-001",
    displayLabel: "Email Address",
    valueType: "email_address",
    iconHint: "mail",
    scope: "step_output",
    compatibilitySummary:
      "Compatible with email_address input fields. Marked sensitive: external binding requires approval.",
    sensitive: true,
  },
  {
    outputId: "output:extract-score-001",
    sourceRef: "step:extract-leads-001",
    displayLabel: "Qualification Score",
    valueType: "number",
    iconHint: "trending-up",
    scope: "step_output",
    compatibilitySummary: "Compatible with number input fields and condition expressions",
    sensitive: false,
  },
  {
    outputId: "output:summarize-reasoning-001",
    sourceRef: "step:summarize-qualification-001",
    displayLabel: "Reasoning Summary",
    valueType: "text",
    iconHint: "message-square",
    scope: "step_output",
    compatibilitySummary: "Compatible with text input fields",
    sensitive: false,
  },
];

/**
 * Sample variable bindings.
 * Mirrors candidate FB-003 VariableBinding contract.
 */
const sampleVariableBindings: VariableBindingFixture[] = [
  {
    id: "binding:notify-name-001",
    consumerRef: "step:notify-high-priority-001",
    consumerField: "messageTemplate",
    outputRef: "output:extract-contact-name-001",
    scope: "step_output",
    path: "contact_name",
    valueType: "text",
    required: true,
  },
  {
    id: "binding:notify-company-001",
    consumerRef: "step:notify-high-priority-001",
    consumerField: "messageTemplate",
    outputRef: "output:extract-company-001",
    scope: "step_output",
    path: "company",
    valueType: "text",
    required: true,
  },
  {
    id: "binding:notify-email-001",
    consumerRef: "step:notify-high-priority-001",
    consumerField: "recipientTemplate",
    outputRef: "output:extract-email-001",
    scope: "step_output",
    path: "email",
    valueType: "email_address",
    required: true,
  },
  {
    id: "binding:summary-email-001",
    consumerRef: "step:send-summary-001",
    consumerField: "recipientTemplate",
    outputRef: "output:extract-email-001",
    scope: "step_output",
    path: "email",
    valueType: "email_address",
    required: true,
  },
];

/**
 * Sample validation issues.
 * Mirrors candidate FB-004 ValidationIssue contract.
 */
const sampleValidationIssues: ValidationIssueFixture[] = [
  {
    id: "validation:issue-email-sensitivity-001",
    code: "permission_risk",
    severity: "warning",
    scope: "variable_binding",
    targetRef: "binding:notify-email-001",
    message:
      "Email address output is marked sensitive. External notification binding requires user approval before activation.",
    blocking: false,
    createdAt: "2026-05-15T09:45:00Z",
  },
  {
    id: "validation:issue-condition-score-001",
    code: "unknown_semantic_output",
    severity: "warning",
    scope: "step",
    targetRef: "step:extract-leads-001",
    message:
      "The qualification_score output from the extract step may be unknown if input data is incomplete. Condition uses this output without explicit fallback.",
    blocking: false,
    createdAt: "2026-05-15T09:45:00Z",
  },
];

/**
 * Sample validation summary.
 * Mirrors candidate FB-004 ValidationSummary contract.
 * Has warnings but no blocking issues.
 */
const sampleValidationSummary: ValidationSummaryFixture = {
  state: "warning",
  eligibleForTestRun: true,
  eligibleForActivation: false, // Blocked by warnings requiring approval
  issues: sampleValidationIssues,
  blockingCount: 0,
  warningCount: 2,
  validatedAt: "2026-05-15T09:45:00Z",
  validatorVersion: "1.0.0-prototype",
};

/**
 * Sample TestRun summary.
 * Mirrors candidate FB-007 TestRun contract.
 */
const sampleTestRun: TestRunSummaryFixture = {
  id: "test-run:sample-001",
  flowDraftId: "flow-draft:sample-001",
  state: "completed",
  initiatedByUserId: "user:prototype-user-001",
  validationSnapshotRef: "validation:snapshot:sample-001",
  createdAt: "2026-05-15T10:00:00Z",
  startedAt: "2026-05-15T10:00:05Z",
  completedAt: "2026-05-15T10:01:30Z",
};

/**
 * Sample Activation summary.
 * Mirrors candidate FB-007 Activation contract.
 * State is paused (not active).
 */
const sampleActivation: ActivationSummaryFixture = {
  id: "activation:sample-001",
  flowDraftId: "flow-draft:sample-001",
  state: "paused",
  activatedByUserId: "user:prototype-user-001",
  starterRef: "starter:sample-001",
  validationSnapshotRef: "validation:snapshot:sample-001",
  createdAt: "2026-05-15T10:05:00Z",
  activatedAt: "2026-05-15T10:05:00Z",
  pausedAt: "2026-05-15T10:30:00Z",
};

/**
 * Sample semantic metadata for step receipts.
 */
const extractSemanticMetadata: SemanticMetadataFixture = {
  semanticStepKind: "extract",
  uncertaintyOutcome: "known" as UncertaintyOutcomeFixture,
  modelPolicyRef: "model:local-llm-001",
  allowedSourcesSnapshot: "user_provided_input",
  redactionSummary: "No sensitive redaction applied to inputs.",
};

/**
 * Summarize semantic metadata.
 */
const summarizeSemanticMetadata: SemanticMetadataFixture = {
  semanticStepKind: "summarize",
  uncertaintyOutcome: "known" as UncertaintyOutcomeFixture,
  modelPolicyRef: "model:local-llm-001",
  allowedSourcesSnapshot: "extract_step_output",
};

/**
 * Sample condition metadata for skipped step receipt.
 */
const skippedConditionMetadata: ConditionMetadataFixture = {
  conditionRef: "condition:score-gte-70",
  conditionResult: false,
  evaluatedInputs: ["step:extract-leads-001.output.qualification_score"],
  selectedBranch: "else",
  skippedStepRefs: ["step:notify-high-priority-001"],
  executedStepRefs: ["step:log-low-priority-001"],
};

/**
 * Sample StepReceipt summaries.
 * Mirrors candidate FB-008 StepReceipt contract.
 * Includes completed and skipped states.
 */
const sampleStepReceipts: StepReceiptSummaryFixture[] = [
  {
    id: "step-receipt:extract-leads-001",
    runReceiptId: "run-receipt:sample-001",
    sourceStepRef: "step:extract-leads-001",
    state: "completed",
    inputRefs: [],
    outputRefs: [
      "output:extract-contact-name-001",
      "output:extract-company-001",
      "output:extract-email-001",
      "output:extract-score-001",
    ],
    valueSummary: "Extracted 4 fields from lead data",
    semanticMetadata: extractSemanticMetadata,
    sideEffectRefs: [],
    startedAt: "2026-05-15T10:00:10Z",
    completedAt: "2026-05-15T10:00:45Z",
  },
  {
    id: "step-receipt:summarize-qualification-001",
    runReceiptId: "run-receipt:sample-001",
    sourceStepRef: "step:summarize-qualification-001",
    state: "completed",
    inputRefs: ["output:extract-score-001"],
    outputRefs: ["output:summarize-reasoning-001"],
    valueSummary: "Generated qualification reasoning summary",
    semanticMetadata: summarizeSemanticMetadata,
    sideEffectRefs: [],
    startedAt: "2026-05-15T10:00:50Z",
    completedAt: "2026-05-15T10:01:10Z",
  },
  {
    id: "step-receipt:notify-high-priority-001",
    runReceiptId: "run-receipt:sample-001",
    sourceStepRef: "step:notify-high-priority-001",
    sourceBranchRef: "container:score-check-001",
    state: "skipped",
    inputRefs: [],
    outputRefs: [],
    valueSummary: "Step skipped due to condition evaluation",
    conditionMetadata: skippedConditionMetadata,
    sideEffectRefs: [],
    skippedAt: "2026-05-15T10:01:15Z",
  },
  {
    id: "step-receipt:log-low-priority-001",
    runReceiptId: "run-receipt:sample-001",
    sourceStepRef: "step:log-low-priority-001",
    sourceBranchRef: "container:score-check-001",
    state: "completed",
    inputRefs: [],
    outputRefs: [],
    valueSummary: "Logged low-priority lead to queue",
    sideEffectRefs: ["command-run:sample-log-001"],
    startedAt: "2026-05-15T10:01:15Z",
    completedAt: "2026-05-15T10:01:20Z",
  },
  {
    id: "step-receipt:send-summary-001",
    runReceiptId: "run-receipt:sample-001",
    sourceStepRef: "step:send-summary-001",
    state: "completed",
    inputRefs: ["output:extract-email-001", "output:extract-contact-name-001", "output:extract-score-001"],
    outputRefs: [],
    valueSummary: "Sent qualification summary email",
    sideEffectRefs: ["email:outbound-001"],
    startedAt: "2026-05-15T10:01:25Z",
    completedAt: "2026-05-15T10:01:30Z",
  },
];

/**
 * Sample RunReceipt summary.
 * Mirrors candidate FB-008 RunReceipt contract.
 */
const sampleRunReceipt: RunReceiptSummaryFixture = {
  id: "run-receipt:sample-001",
  flowDraftId: "flow-draft:sample-001",
  testRunId: "test-run:sample-001",
  initiatorRef: "user:prototype-user-001",
  triggerRef: "starter:sample-001",
  state: "completed",
  validationSnapshotRef: "validation:snapshot:sample-001",
  permissionSnapshotRef: "permission:snapshot:sample-001",
  stepReceiptRefs: sampleStepReceipts,
  createdAt: "2026-05-15T10:00:00Z",
  startedAt: "2026-05-15T10:00:05Z",
  completedAt: "2026-05-15T10:01:30Z",
};

/**
 * Sample activity events for the proof surface.
 * Mirrors candidate FB-009 proof surface event types.
 */
const sampleActivityEvents: ActivityEventFixture[] = [
  {
    id: "event:draft-created-001",
    type: "draft_created",
    timestamp: "2026-05-10T14:30:00Z",
    origin: "assistant-suggestion",
    state: "created",
    message: "Flow draft 'Lead Qualification Flow' was created from thread.",
  },
  {
    id: "event:draft-validated-001",
    type: "draft_validated",
    timestamp: "2026-05-15T09:45:00Z",
    origin: "system",
    state: "warning",
    message:
      "Draft validation completed with 0 blocking issues and 2 warnings. TestRun eligible, Activation requires approval.",
  },
  {
    id: "event:test-run-started-001",
    type: "test_run_started",
    timestamp: "2026-05-15T10:00:05Z",
    origin: "user:prototype-user-001",
    state: "running",
    evidenceRef: "test-run:sample-001",
    message: "TestRun 'test-run:sample-001' started against draft 'flow-draft:sample-001'.",
  },
  {
    id: "event:step-completed-001",
    type: "step_completed",
    timestamp: "2026-05-15T10:00:45Z",
    origin: "system",
    state: "completed",
    evidenceRef: "step-receipt:extract-leads-001",
    message:
      "Step 'Extract lead fields' completed. Extracted contact_name, company, email, qualification_score.",
  },
  {
    id: "event:step-skipped-001",
    type: "step_skipped",
    timestamp: "2026-05-15T10:01:15Z",
    origin: "system",
    state: "skipped",
    evidenceRef: "step-receipt:notify-high-priority-001",
    message:
      "Step 'Notify sales team' was skipped. Condition result: false (score 55 <= 70 threshold). Else branch executed.",
  },
  {
    id: "event:run-completed-001",
    type: "run_completed",
    timestamp: "2026-05-15T10:01:30Z",
    origin: "system",
    state: "completed",
    evidenceRef: "run-receipt:sample-001",
    message:
      "Run completed successfully. 5 steps executed, 1 skipped. Duration: 1m 25s.",
  },
  {
    id: "event:receipt-persisted-001",
    type: "receipt_persisted",
    timestamp: "2026-05-15T10:01:32Z",
    origin: "system",
    state: "completed",
    evidenceRef: "run-receipt:sample-001",
    message: "RunReceipt persisted for run 'run-receipt:sample-001'.",
  },
  {
    id: "event:activation-paused-001",
    type: "activation_paused",
    timestamp: "2026-05-15T10:30:00Z",
    origin: "user:prototype-user-001",
    state: "paused",
    evidenceRef: "activation:sample-001",
    message:
      "Activation 'activation:sample-001' was paused. No further automatic runs will trigger.",
  },
];

/**
 * Complete Flow Builder fixture data for the prototype shell.
 * Aggregates all fixture types representing future Flow Builder concepts.
 */
export const flowBuilderFixture: FlowBuilderFixtureData = {
  draft: sampleFlowDraft,
  starter: sampleStarter,
  steps: [extractStep, summarizeStep, conditionalStep, notificationStep],
  conditionalContainer: conditionalContainer,
  typedOutputs: sampleTypedOutputs,
  variableChips: sampleVariableChips,
  variableBindings: sampleVariableBindings,
  validationSummary: sampleValidationSummary,
  testRunSummary: sampleTestRun,
  activationSummary: sampleActivation,
  runReceiptSummary: sampleRunReceipt,
  stepReceiptSummaries: sampleStepReceipts,
  activityEvents: sampleActivityEvents,
};

/**
 * All steps as a flat ordered list for step list rendering.
 * Combines regular steps and conditional container substeps.
 */
export function getOrderedSteps(
  fixture: FlowBuilderFixtureData
): Array<{ step: FlowStepFixture; isConditionalSubstep: boolean; branch: "then" | "else" | null }> {
  const result: Array<{
    step: FlowStepFixture;
    isConditionalSubstep: boolean;
    branch: "then" | "else" | null;
  }> = [];

  for (const step of fixture.steps) {
    result.push({ step, isConditionalSubstep: false, branch: null });
  }

  if (fixture.conditionalContainer) {
    for (const substep of fixture.conditionalContainer.substeps) {
      result.push({ step: substep, isConditionalSubstep: true, branch: "then" });
    }
    for (const substep of fixture.conditionalContainer.elseSubsteps) {
      result.push({ step: substep, isConditionalSubstep: true, branch: "else" });
    }
  }

  return result;
}

/**
 * Re-export type for convenience.
 */
export type { FlowBuilderFixtureData };
