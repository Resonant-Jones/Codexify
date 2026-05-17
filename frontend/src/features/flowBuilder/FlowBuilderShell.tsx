/**
 * Flow Builder Shell Prototype
 *
 * A fixture-backed UI prototype for the future Flow Builder authoring
 * and proof-surface concepts.
 *
 * This component renders against local fixture data only.
 * - No API calls
 * - No mutation
 * - No live execution
 * - Any action-like controls are disabled or labeled "Prototype only"
 *
 * This is NOT runtime proof. NOT backend implementation. NOT release support.
 */

import React from "react";

import type {
  FlowBuilderFixtureData,
  FlowStarterFixture,
  FlowStepFixture,
  VariableChipFixture,
  ValidationSummaryFixture,
  TestRunSummaryFixture,
  ActivationSummaryFixture,
  RunReceiptSummaryFixture,
  StepReceiptSummaryFixture,
  ActivityEventFixture,
  ConditionalContainerFixture,
} from "./types";

import { flowBuilderFixture } from "./fixtures";

import "./FlowBuilderShell.css";

/**
 * Props for the FlowBuilderShell component.
 */
export interface FlowBuilderShellProps {
  /** Fixture data to render. Defaults to the sample fixture. */
  fixture?: FlowBuilderFixtureData;
  /** Optional class name for custom styling. */
  className?: string;
}

/**
 * Section header component for shell regions.
 */
function SectionHeader({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`fb-shell-section-header ${className}`}>
      <h2>{children}</h2>
    </div>
  );
}

/**
 * Draft overview card component.
 */
function DraftOverviewCard({
  draft,
}: {
  draft: FlowBuilderFixtureData["draft"];
}) {
  return (
    <section className="fb-shell-card fb-draft-overview" aria-labelledby="draft-overview-heading">
      <h3 id="draft-overview-heading">Draft Overview</h3>
      <dl className="fb-draft-meta">
        <div className="fb-draft-meta-row">
          <dt>Title</dt>
          <dd>{draft.title}</dd>
        </div>
        <div className="fb-draft-meta-row">
          <dt>Status</dt>
          <dd>
            <span className="fb-status-badge">{draft.status}</span>
          </dd>
        </div>
        <div className="fb-draft-meta-row">
          <dt>Runtime Support</dt>
          <dd>{draft.runtimeSupport}</dd>
        </div>
        <div className="fb-draft-meta-row">
          <dt>Updated</dt>
          <dd>{new Date(draft.updatedAt).toLocaleString()}</dd>
        </div>
      </dl>
    </section>
  );
}

/**
 * Starter card component.
 */
function StarterCard({ starter }: { starter: FlowStarterFixture }) {
  return (
    <section className="fb-shell-card fb-starter-card" aria-labelledby="starter-heading">
      <h3 id="starter-heading">Starter</h3>
      <dl className="fb-starter-meta">
        <div className="fb-meta-row">
          <dt>Label</dt>
          <dd>{starter.label}</dd>
        </div>
        <div className="fb-meta-row">
          <dt>Kind</dt>
          <dd>{starter.kind}</dd>
        </div>
        <div className="fb-meta-row">
          <dt>Description</dt>
          <dd>{String(starter.config.description ?? "Prototype starter fixture")}</dd>
        </div>
        <div className="fb-meta-row">
          <dt>Requires Approval</dt>
          <dd>{String(Boolean(starter.config.requiresApproval))}</dd>
        </div>
      </dl>
    </section>
  );
}

/**
 * Step badge component showing step kind.
 */
function StepBadge({ kind }: { kind: FlowStepFixture["kind"] }) {
  return <span className={`fb-step-badge fb-step-badge-${kind}`}>{kind}</span>;
}

/**
 * Semantic step badge with specific semantic kind.
 */
function SemanticStepBadge({ semanticKind }: { semanticKind: string }) {
  return (
    <span className="fb-step-badge fb-step-badge-semantic" title={`Semantic step: ${semanticKind}`}>
      semantic:{semanticKind}
    </span>
  );
}

/**
 * Ordered step list component.
 */
function StepList({ steps, conditionalContainer }: {
  steps: FlowStepFixture[];
  conditionalContainer?: ConditionalContainerFixture;
}) {
  return (
    <section className="fb-shell-card fb-step-list" aria-labelledby="step-list-heading">
      <h3 id="step-list-heading">Ordered Steps</h3>
      <ol className="fb-steps" role="list">
        {steps.map((step, index) => {
          const semanticKind = (step.config as Record<string, unknown>)?.semanticStepKind as string | undefined;
          return (
            <li key={step.id} className="fb-step-item">
              <div className="fb-step-item-header">
                <span className="fb-step-position">{index + 1}</span>
                <span className="fb-step-label">{step.label}</span>
                {step.kind === "semantic" && semanticKind ? (
                  <SemanticStepBadge semanticKind={semanticKind} />
                ) : (
                  <StepBadge kind={step.kind} />
                )}
              </div>
              {step.kind === "semantic" && semanticKind && (
                <p className="fb-step-instruction">
                  {(step.config as Record<string, unknown>)?.instruction as string}
                </p>
              )}
              {step.kind === "conditional" && conditionalContainer && (
                <div className="fb-conditional-body">
                  <p className="fb-conditional-condition">
                    Condition: {conditionalContainer.condition.lhs}{" "}
                    <strong>{conditionalContainer.condition.operator}</strong>{" "}
                    {conditionalContainer.condition.rhs}
                  </p>
                  <div className="fb-conditional-branches">
                    <div className="fb-conditional-branch fb-branch-then">
                      <h4>
                        Then branch ({conditionalContainer.substeps.length}
                        {conditionalContainer.substeps.length !== 1 ? " steps" : " step"})
                      </h4>
                      <ul>
                        {conditionalContainer.substeps.map((substep) => (
                          <li key={substep.id}>{substep.label}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="fb-conditional-branch fb-branch-else">
                      <h4>
                        Else branch ({conditionalContainer.elseSubsteps.length}
                        {conditionalContainer.elseSubsteps.length !== 1 ? " steps" : " step"})
                      </h4>
                      <ul>
                        {conditionalContainer.elseSubsteps.map((substep) => (
                          <li key={substep.id}>{substep.label}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ol>
      <div className="fb-step-count">
        {steps.length} total steps
      </div>
    </section>
  );
}

/**
 * Variable chip component.
 */
function VariableChipDisplay({ chip }: { chip: VariableChipFixture }) {
  return (
    <div
      className={`fb-variable-chip ${chip.sensitive ? "fb-chip-sensitive" : ""}`}
      title={`Type: ${chip.valueType} | Scope: ${chip.scope}`}
    >
      {chip.iconHint && <span className="fb-chip-icon">{chip.iconHint}</span>}
      <span className="fb-chip-label">{chip.displayLabel}</span>
      <span className="fb-chip-type">{chip.valueType}</span>
      {chip.sensitive && <span className="fb-chip-sensitive-indicator" title="Sensitive output">⚠</span>}
    </div>
  );
}

/**
 * Variable chips and outputs panel.
 */
function VariableChipsPanel({
  variableChips,
  typedOutputs,
}: {
  variableChips: VariableChipFixture[];
  typedOutputs: { id: string; displayLabel: string; valueType: string }[];
}) {
  return (
    <section className="fb-shell-card fb-variable-panel" aria-labelledby="variable-panel-heading">
      <h3 id="variable-panel-heading">Variable Chips &amp; Outputs</h3>
      <p className="fb-panel-description">
        Typed outputs from steps and their backing chips. Sensitive outputs are marked with ⚠.
      </p>
      <div className="fb-chips-grid">
        {variableChips.map((chip) => (
          <VariableChipDisplay key={chip.outputId} chip={chip} />
        ))}
      </div>
      <details className="fb-outputs-details">
        <summary>View typed output declarations ({typedOutputs.length})</summary>
        <dl className="fb-outputs-list">
          {typedOutputs.map((output) => (
            <div key={output.id} className="fb-output-item">
              <dt>{output.displayLabel}</dt>
              <dd>{output.valueType}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}

/**
 * Validation warning badge.
 */
function ValidationWarningBadge({ issue }: {
  issue: { code: string; severity: string; message: string; blocking: boolean };
}) {
  return (
    <div className={`fb-validation-warning fb-severity-${issue.severity} ${issue.blocking ? "fb-blocking" : ""}`}>
      <span className="fb-validation-code">{issue.code}</span>
      <span className="fb-validation-message">{issue.message}</span>
      {issue.blocking && <span className="fb-blocking-indicator">BLOCKING</span>}
    </div>
  );
}

/**
 * Validation summary panel.
 */
function ValidationSummaryPanel({ validationSummary }: { validationSummary: ValidationSummaryFixture }) {
  return (
    <section className="fb-shell-card fb-validation-panel" aria-labelledby="validation-panel-heading">
      <h3 id="validation-panel-heading">Validation Summary</h3>
      <div className={`fb-validation-state fb-state-${validationSummary.state}`}>
        <span className="fb-validation-state-label">State: {validationSummary.state}</span>
      </div>
      <div className="fb-validation-eligibility">
        <div className={`fb-eligibility-item ${validationSummary.eligibleForTestRun ? "eligible" : "not-eligible"}`}>
          <span className="fb-eligibility-label">TestRun Eligible</span>
          <span className="fb-eligibility-value">{validationSummary.eligibleForTestRun ? "Yes" : "No"}</span>
        </div>
        <div className={`fb-eligibility-item ${validationSummary.eligibleForActivation ? "eligible" : "not-eligible"}`}>
          <span className="fb-eligibility-label">Activation Eligible</span>
          <span className="fb-eligibility-value">{validationSummary.eligibleForActivation ? "Yes" : "No"}</span>
        </div>
      </div>
      <div className="fb-validation-counts">
        <span>Blocking: {validationSummary.blockingCount}</span>
        <span>Warnings: {validationSummary.warningCount}</span>
        <span>Total issues: {validationSummary.issues.length}</span>
      </div>
      {validationSummary.issues.length > 0 && (
        <div className="fb-validation-issues">
          <h4>Issues</h4>
          {validationSummary.issues.map((issue) => (
            <ValidationWarningBadge key={issue.code} issue={issue} />
          ))}
        </div>
      )}
      <p className="fb-validation-note">
        Validator version: {validationSummary.validatorVersion}
      </p>
    </section>
  );
}

/**
 * TestRun and Activation summary panel.
 */
function TestRunActivationPanel({
  testRun,
  activation,
}: {
  testRun?: TestRunSummaryFixture;
  activation?: ActivationSummaryFixture;
}) {
  return (
    <section className="fb-shell-card fb-test-activation-panel" aria-labelledby="test-activation-heading">
      <h3 id="test-activation-heading">TestRun &amp; Activation</h3>

      {testRun && (
        <div className="fb-test-run-section">
          <h4>TestRun</h4>
          <dl className="fb-test-run-meta">
            <div className="fb-meta-row">
              <dt>ID</dt>
              <dd>{testRun.id}</dd>
            </div>
            <div className="fb-meta-row">
              <dt>State</dt>
              <dd>
                <span className={`fb-state-badge fb-state-${testRun.state}`}>{testRun.state}</span>
              </dd>
            </div>
            <div className="fb-meta-row">
              <dt>Created</dt>
              <dd>{new Date(testRun.createdAt).toLocaleString()}</dd>
            </div>
            {testRun.completedAt && (
              <div className="fb-meta-row">
                <dt>Completed</dt>
                <dd>{new Date(testRun.completedAt).toLocaleString()}</dd>
              </div>
            )}
            {testRun.failureReason && (
              <div className="fb-meta-row fb-meta-failure">
                <dt>Failure</dt>
                <dd>{testRun.failureReason}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {activation && (
        <div className="fb-activation-section">
          <h4>Activation</h4>
          <dl className="fb-activation-meta">
            <div className="fb-meta-row">
              <dt>ID</dt>
              <dd>{activation.id}</dd>
            </div>
            <div className="fb-meta-row">
              <dt>State</dt>
              <dd>
                <span className={`fb-state-badge fb-state-${activation.state}`}>{activation.state}</span>
              </dd>
            </div>
            <div className="fb-meta-row">
              <dt>Created</dt>
              <dd>{new Date(activation.createdAt).toLocaleString()}</dd>
            </div>
            {activation.activatedAt && (
              <div className="fb-meta-row">
                <dt>Activated</dt>
                <dd>{new Date(activation.activatedAt).toLocaleString()}</dd>
              </div>
            )}
            {activation.pausedAt && (
              <div className="fb-meta-row">
                <dt>Paused</dt>
                <dd>{new Date(activation.pausedAt).toLocaleString()}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      <div className="fb-action-placeholder">
        <button type="button" disabled className="fb-prototype-button">
          Prototype only: Run Test
        </button>
        <button type="button" disabled className="fb-prototype-button">
          Prototype only: Activate
        </button>
      </div>
    </section>
  );
}

/**
 * Step receipt badge showing state.
 */
function StepReceiptBadge({ receipt }: { receipt: StepReceiptSummaryFixture }) {
  return (
    <div className={`fb-step-receipt fb-receipt-${receipt.state}`}>
      <span className="fb-receipt-label">{receipt.state}</span>
      {receipt.semanticMetadata && (
        <span className="fb-receipt-semantic" title={`Semantic: ${receipt.semanticMetadata.semanticStepKind}`}>
          {receipt.semanticMetadata.semanticStepKind}
        </span>
      )}
    </div>
  );
}

/**
 * Activity event item.
 */
function ActivityEventItem({ event }: { event: ActivityEventFixture }) {
  return (
    <div className={`fb-activity-event fb-event-${event.type.replace(/_/g, "-")}`}>
      <span className="fb-event-time">{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span className="fb-event-type">{event.type}</span>
      <span className={`fb-event-state fb-state-${event.state}`}>{event.state}</span>
      <span className="fb-event-message">{event.message}</span>
      {event.evidenceRef && (
        <span className="fb-event-evidence" title="Evidence reference">
          ↗
        </span>
      )}
    </div>
  );
}

/**
 * Run receipt summary panel.
 */
function RunReceiptPanel({ runReceipt, stepReceipts }: {
  runReceipt?: RunReceiptSummaryFixture;
  stepReceipts: StepReceiptSummaryFixture[];
}) {
  return (
    <section className="fb-shell-card fb-run-receipt-panel" aria-labelledby="run-receipt-heading">
      <h3 id="run-receipt-heading">Run Receipt &amp; Step Receipts</h3>

      {runReceipt && (
        <div className="fb-run-receipt-section">
          <h4>Run Receipt</h4>
          <dl className="fb-run-receipt-meta">
            <div className="fb-meta-row">
              <dt>ID</dt>
              <dd>{runReceipt.id}</dd>
            </div>
            <div className="fb-meta-row">
              <dt>State</dt>
              <dd>
                <span className={`fb-state-badge fb-state-${runReceipt.state}`}>{runReceipt.state}</span>
              </dd>
            </div>
            <div className="fb-meta-row">
              <dt>Initiator</dt>
              <dd>{runReceipt.initiatorRef}</dd>
            </div>
            {runReceipt.startedAt && (
              <div className="fb-meta-row">
                <dt>Started</dt>
                <dd>{new Date(runReceipt.startedAt).toLocaleString()}</dd>
              </div>
            )}
            {runReceipt.completedAt && (
              <div className="fb-meta-row">
                <dt>Completed</dt>
                <dd>{new Date(runReceipt.completedAt).toLocaleString()}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      <div className="fb-step-receipts-section">
        <h4>Step Receipts ({stepReceipts.length})</h4>
        <div className="fb-step-receipts-list">
          {stepReceipts.map((receipt) => (
            <div key={receipt.id} className="fb-step-receipt-item">
              <StepReceiptBadge receipt={receipt} />
              <span className="fb-step-receipt-source">{receipt.sourceStepRef}</span>
              {receipt.conditionMetadata && (
                <span className="fb-step-receipt-branch">
                  Branch: {receipt.conditionMetadata.selectedBranch}
                </span>
              )}
              {receipt.semanticMetadata && (
                <span className="fb-step-receipt-outcome">
                  Outcome: {receipt.semanticMetadata.uncertaintyOutcome}
                </span>
              )}
              <span className="fb-step-receipt-summary">{receipt.valueSummary}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Activity/proof surface panel.
 */
function ActivityProofSurfacePanel({ activityEvents }: { activityEvents: ActivityEventFixture[] }) {
  return (
    <section className="fb-shell-card fb-activity-panel" aria-labelledby="activity-panel-heading">
      <h3 id="activity-panel-heading">Activity &amp; Proof Surface</h3>
      <p className="fb-panel-description">
        Ordered history of draft activity, validation, and run evidence. Proof surface for inspection.
      </p>
      <div className="fb-activity-timeline">
        {activityEvents.map((event) => (
          <ActivityEventItem key={event.id} event={event} />
        ))}
      </div>
      <div className="fb-activity-count">
        {activityEvents.length} activity events
      </div>
    </section>
  );
}

/**
 * Main Flow Builder Shell component.
 */
export function FlowBuilderShell({ fixture = flowBuilderFixture, className = "" }: FlowBuilderShellProps) {
  return (
    <div className={`fb-shell ${className}`} role="region" aria-label="Flow Builder Shell Prototype">
      <header className="fb-shell-header">
        <h1>Flow Builder Shell Prototype</h1>
        <p className="fb-shell-subtitle">
          Fixture-backed UI prototype for future Flow Builder concepts.
          Not runtime proof. Not backend implementation.
        </p>
        <div className="fb-prototype-banner">
          <span>⚠</span>
          <span>This prototype renders fixture data only. No execution, persistence, or API wiring.</span>
        </div>
      </header>

      <main className="fb-shell-content">
        {/* Authoring Lane */}
        <div className="fb-authoring-lane">
          <StarterCard starter={fixture.starter} />
          <DraftOverviewCard draft={fixture.draft} />
          <StepList steps={fixture.steps} conditionalContainer={fixture.conditionalContainer} />
        </div>

        {/* Proof / Activity Panel */}
        <div className="fb-proof-surface">
          <VariableChipsPanel
            variableChips={fixture.variableChips}
            typedOutputs={fixture.typedOutputs}
          />
          <ValidationSummaryPanel validationSummary={fixture.validationSummary} />
          <TestRunActivationPanel
            testRun={fixture.testRunSummary}
            activation={fixture.activationSummary}
          />
          <RunReceiptPanel
            runReceipt={fixture.runReceiptSummary}
            stepReceipts={fixture.stepReceiptSummaries}
          />
          <ActivityProofSurfacePanel activityEvents={fixture.activityEvents} />
        </div>
      </main>

      <footer className="fb-shell-footer">
        <p>
          Prototype only. Fixtures are not runtime proof.
          Does not imply Flow Builder execution, persistence, or release support.
        </p>
      </footer>
    </div>
  );
}

/**
 * Export the shell component for use in tests and prototyping.
 */
export default FlowBuilderShell;
