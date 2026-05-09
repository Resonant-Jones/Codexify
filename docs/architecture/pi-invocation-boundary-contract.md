# Pi Invocation Boundary Contract

Implementation status (2026-05-08): backend-only Pi invocation boundary contracts now exist under `guardian/pi` for `PiInvocationEnvelope`, `PiInvocationReceipt`, `PiInvocationArtifact`, `PiHarnessResult`, and `PiInvocationValidationResult`, with pure deterministic validation helpers for envelope, receipt, and harness-result provenance/permission checks.

This seam is contract and validation only:
- no live Pi SDK call exists
- no Minimax provider behavior changed
- no provider routing changed
- no command execution was added
- no worker orchestration was added
- no sandboxing was added
- no runtime dispatch/autonomous execution was added
- no transcript persistence was added
- no HTTP routes were added

Deferred in this task:
- `/docs/architecture/00-current-state.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- provider implementation docs
- command-bus runtime docs
