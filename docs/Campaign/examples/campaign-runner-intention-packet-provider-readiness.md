# Campaign Runner Intention Packet

This is an illustrative example packet for operator review. It has not been run and does not provide live runtime proof.

## Packet Metadata

- Packet title: Campaign Runner provider-broker readiness audit
- Author/operator: Example operator
- Date: 2026-06-08
- Intended repo/root: Codexify local checkout
- Related contracts or ADRs:
  - `docs/architecture/00-current-state.md`
  - `docs/architecture/campaign-runner-intention-packet-contract.md`
  - `docs/architecture/pi-invocation-boundary-contract.md`
  - `docs/architecture/agent-tool-loop-contract.md`
  - `docs/architecture/agent-protocol-operations.md`
  - `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
  - `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
  - `docs/architecture/adr/036-campaign-runner-provider-adapter-contract.md`
  - `docs/architecture/adr/037-campaign-runner-pi-provider-broker.md`
- Intended runner usage: `--intention-packet-file docs/Campaign/examples/campaign-runner-intention-packet-provider-readiness.md`

## Objective

Audit Campaign Runner provider-broker readiness for the current Pi-broker-first posture, with emphasis on whether the repo preserves fail-closed behavior and provider receipt evidence without implying release-supported autonomous execution.

## Why This Matters

Campaign Runner planning depends on provider-broker governance staying explicit. Operators need evidence that Stage A and Stage B can distinguish implemented Pi adapter seams, provider receipts, and fail-closed direct-provider behavior from broader provider or execution claims that are not release-proven.

## Scope

- Pi adapter wiring in Campaign Runner provider selection and runner invocation paths.
- Provider receipt preservation and run metadata surfaces.
- Direct Codex and Claude fail-closed behavior in active Campaign Runner surfaces.
- Dirty-tree and branch safety checks before runner execution.
- Tests that cover provider dispatch, TUI provider state, runner preflight safety, and provider receipt metadata.
- Architecture docs governing provider governance, Pi boundaries, Guardian ownership, and current release truth.

## Out of Scope

- UI dispatch or Command Center execution dispatch.
- Release-claim widening for provider support or autonomous execution.
- Merge automation, auto-push, or auto-release behavior.
- New provider routing, new provider adapters, or provider catalog expansion.
- End-to-end wet execution proof.
- Queue, worker, route, database, or UI changes.

## Evidence Requirements

- Cite concrete repo paths and line hints for provider selection, Pi adapter wiring, direct-provider rejection, receipt persistence, and dirty-tree or branch checks.
- Identify the exact tests that prove or fail to prove each readiness claim.
- Mark explicit unknowns where a receipt, test, or safety path is not discoverable.
- Treat old docs, vendored references, and examples as supporting context only, not proof of active provider behavior.
- Keep `docs/architecture/00-current-state.md` as the release-truth authority.

## Stage A Audit Posture

- Prefer discovery findings over speculative implementation when provider-broker evidence is incomplete.
- Separate repo-grounded evidence from this operator intent.
- Distinguish active Campaign Runner provider behavior from historical Codex/Claude mentions elsewhere in the repo.
- Do not treat Pi boundary contracts or packet language as proof of live Pi SDK execution.
- Do not infer release-supported autonomous execution from adapter wiring, route presence, tests, or docs.

## Stage B Campaign Posture

- Produce at most one campaign.
- The campaign may contain one to three independently mergeable tasks.
- Include only tasks supported by Stage-A evidence.
- Prefer a discovery or test-hardening task when readiness is ambiguous.
- Do not invent provider support, release support, UI dispatch, lease allocation, live agent execution, or merge automation tasks.

## Task-Lane Expectations

- Use architecture-impact classification for any task touching contracts, provider governance, Pi boundaries, Guardian ownership, provider receipt semantics, or release-truth interpretation.
- Keep each task file-bounded and independently mergeable.
- Require targeted tests for provider dispatch, TUI provider state, preflight safety, or receipt metadata when those surfaces are touched.
- Do not add git instructions to generated tasks.

## Release-Truth Constraints

- `docs/architecture/00-current-state.md` remains authoritative.
- The supported release path remains local Docker Compose with local-only provider posture.
- Pi `disable-tools` or provider-broker options must not be treated as widened release support.
- This packet is planning input only. It is not runtime proof, not an ADR, and not evidence that provider-broker readiness has been run end to end.
- Do not claim shipped UI dispatch, lease allocation, live agent execution, merge automation, autonomous self-modification, or provider support beyond current release truth.

## Success Criteria

- Stage A identifies whether Campaign Runner provider-broker readiness is repo-supported, partially supported, or unknown.
- Stage A cites concrete paths and tests for each readiness claim.
- Stage B emits zero campaigns when evidence is insufficient, or one narrow campaign with one to three evidence-backed tasks when follow-through is justified.
- Any generated tasks preserve fail-closed provider behavior and release-truth boundaries.

## Failure / Stop Conditions

- Evidence for active Pi adapter wiring or provider receipt preservation is missing or contradictory.
- Direct Codex or Claude behavior appears permissive rather than fail-closed and cannot be scoped safely.
- Stage A cannot identify tests that cover the relevant provider-broker readiness claims.
- The work would require runtime execution, UI dispatch, queue or worker changes, schema changes, new provider routing, or release-claim widening.

## Notes for Operator Review

- Review `docs/architecture/00-current-state.md` immediately before running this packet.
- Confirm this example has been copied or intentionally used as-is before passing it to `--intention-packet-file`.
- Treat any output as planning evidence only until validated by the requested tests and, where applicable, separate live proof.
