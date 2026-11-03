# Supported-Compose runtime — current-tip final qualification — 2026-09-22

- Rubric: ../rubrics/supported-compose.md
- Rubric version: 1
- Verdict: HOLD
- Date/time window: 2026-09-22
- Tester alias: automated-architecture-proof
- Tester role: architecture-impact qualification agent
- Prior familiarity: full
- Assistance level peak: 0
- Branch: main
- Commit: 5da79431fa059b7da80688380550cf29d4854b18
- Runtime profile: v1-local-core-web-mcp
- Deployment/environment: local Docker Compose, VaultNode.local, macOS 27.2 arm64
- Device class: workstation
- Browser/client: headed Playwright against the rendered WebUI
- Provider: local
- Model: local-chat

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose
rubric_version: 1
verdict: HOLD
commit: 5da79431fa059b7da80688380550cf29d4854b18
date: 2026-09-22
tester_alias: automated-architecture-proof
tester_kind: automated
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/supported-compose/2026-09-22-current-tip-final-supported-compose-qualification.md
```

## Scope

One exact current-tip supported-Compose qualification against the
`v1-local-core-web-mcp` local-only profile. The run rebuilt and observed the
supported Compose project, created only disposable evaluation data, drove the
real web UI, inspected PostgreSQL and Redis read-only, ran the declared
static gates, and collected the existing canonical live-proof receipt.

The frozen runtime revision remained
`5da79431fa059b7da80688380550cf29d4854b18` through all live evaluation and
static validation. Upstream `origin/main` stood at
`6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`; the branch was 9 ahead / 0
behind.

## Qualification matrix

| Criterion | Result | Observation | Evidence |
| --- | --- | --- | --- |
| Supported topology and startup | PASS | `docker compose config --quiet` succeeded for `docker-compose.yml` + `docker-compose.whooshd-smoke.yml`. Required services `backend`, `worker-chat`, `worker-document-embed` healthy; `graph-init`, `migrator`, `model-prep` exited 0. Last required worker start 61.328s after first container start. | Detailed proof, "Supported topology and startup" |
| Health and inventory | PASS | Health reported `ok` with valid `v1-local-core-web-mcp`, selected provider `local`, and cloud-capable configuration absent. | Detailed proof |
| Ordinary chat and durable readback | PASS | Real-browser cold and warm turns, terminal browser convergence, durable conversation, and reload/re-entry all passed. | Detailed proof |
| Document ingestion and retrieval | PASS | Document ingestion, embedding, project retrieval, and durable document/chunk provenance passed. | Detailed proof |
| Queue/worker lifecycle, turn-lock, F1–F7 static gates | PASS | Queue/worker lifecycle, turn-lock, and the governing static gates passed. | Detailed proof |
| Canonical live-proof receipt | PASS | The canonical live-receipt surface was collected and validated. | Detailed proof |
| Explicit model authority | FAIL | An authenticated completion explicitly selected unavailable local model `missing-local-model-A7K9`. The accepted task did not reject that target: it executed `local-chat`, persisted assistant message `61`, and emitted `task.completed`. Durable selection metadata recorded the requested model as overridden by configured `local-chat`, while execution metadata recorded `fallback_triggered=false`. This is exact-model substitution and a false successful result for a request the accepted fail-closed contract requires to reject. | Detailed proof, "Qualification answer" |
| Browser projection | PASS | Real-browser turns converged to terminal state and survived reload/re-entry. | Detailed proof |
| Restart recovery | UNPROVEN | The planned application-service restart and post-restart ordinary chat were not run. The task's stop gate prohibited further runtime mutation once the exact-model substitution contradiction was durable. | Detailed proof, "Qualification answer" |

## Metrics

```yaml
task_completed: no
assistance_level: 0
wrong_turns: 0
self_recovered: n/a
time_to_first_success_seconds: 61.328
repeat_task_confidence_1_to_5: not_applicable
```

## Observed behavior

The repaired tip passed the supported topology, migration, health,
real-browser cold and warm turns, terminal browser convergence, durable
conversation, reload/re-entry, document ingestion, embedding, project
retrieval, durable document/chunk provenance, queue/worker lifecycle,
turn-lock, the F1–F7 governing static checks, and the canonical live-receipt
surfaces.

The bounded fail-closed lane found one current prerequisite defect. An
explicit request for an unavailable local model was not rejected; it
resolved to `local-chat`, persisted an assistant message, and reported
success.

## Proven

- The supported Compose topology starts and reaches healthy state on the
  evaluated tip with the exact local-only provider contract.
- Ordinary chat completes, persists, and converges in a real browser.
- Document ingestion, embedding, and retrieval with durable provenance work
  on the evaluated tip.
- Queue/worker lifecycle and turn-lock behavior are correct on the evaluated
  tip.
- The canonical live-proof receipt surface is collectable and valid.

## Failed

- **Explicit unavailable model is not rejected before provider execution.**
  The request executed `local-chat`, persisted assistant message `61`, and
  emitted `task.completed`. Durable selection metadata recorded the
  override while execution metadata recorded `fallback_triggered=false`.

## Unproven

- Restart recovery and ordinary chat after an application-service restart.
  Not exercised, because the stop gate forbade further runtime mutation once
  the substitution contradiction was durable.
- Any boundary outside the supported local-only profile.

## Human friction

Not applicable. This was an automated architecture-impact qualification run
with no human tester in the loop.

## Positive signals

- The supported topology, startup, migration head, and durable readback were
  all green on an exact tip.
- The fail-closed lane correctly detected the exact-model substitution
  instead of reporting a false success.

## Highest-priority follow-up

Resolve the exact-model rejection contradiction: an explicitly requested
unavailable model must fail before provider execution, with no substitute
model executed and no assistant persisted.

## Evidence

- Commit: `5da79431fa059b7da80688380550cf29d4854b18`
- Detailed proof: `docs/architecture/proofs/supported-compose/2026-09-22-current-tip-final-supported-compose-qualification.md`
- Related automated tests: the declared static gates recorded in the detailed proof
- Other: canonical live-proof receipt collected during the run

## Freshness

```text
current
```

At the time of the run this receipt described its evaluated commit. The
registry recomputes freshness against the current tip; see
`docs/architecture/00-current-state.md` for release authority.
