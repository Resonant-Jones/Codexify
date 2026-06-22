# Proof Gates

## Purpose

Define the proof categories, gate decisions, and proof rules that govern campaign progression in the Guardian Maturity Program. Every campaign must pass its proof gate before being considered done.

## Proof Categories

### Docs Proof

Documentation is complete, consistent, and follows Codexify conventions.

Evidence includes:
- Campaign charter, backlog, proof pack, and decision log exist
- Templates follow existing `docs/Campaign/` conventions
- Links resolve to existing files
- Release boundary is explicit

### Backend Seam Proof

API routes exist, return structured responses, and match their contracts.

Evidence includes:
- Route registration is verified in the app router
- Endpoint returns expected HTTP status codes
- Response shape matches contract/schema
- Auth/dependency chain is verified

### Frontend UI Proof

UI components render correctly and display truthful data sourced from verified backend seams.

Evidence includes:
- Component renders without errors
- Data displayed matches backend response
- Loading, empty, and error states are handled
- No button triggers behavior without a verified backend route
- Provider state is not collapsed to false binaries

### Live Supported-Path Proof

Behavior is verifiable on the supported local Docker Compose path.

Evidence includes:
- Chat completion succeeds on the local path
- Health endpoints return correct states
- Model inventory is verified reachable
- Lifecycle state transitions are observable
- Whoosh'd reachability is proven (not assumed from config)

### Operator Usability Proof

An operator can answer key questions without log spelunking, reading source code, or running diagnostic commands.

Evidence includes:
- "Can I run?" is answerable from the Command Center
- "Is my model warming or offline?" is distinguishable visually
- A coding delegation draft can be created and inspected
- Stuck work can be diagnosed from the recovery surface

## Gate Decisions

| Decision | Meaning |
|----------|---------|
| `go` | All required proof collected. Campaign proceeds to next gate or completion. |
| `hold` | Required proof is missing or contradictory. Campaign cannot proceed. |
| `next-proof-needed` | Initial state. Proof has not yet been collected. Campaign is ready to begin proof collection. |

## Proof Rules

These rules govern what counts as valid proof:

1. **Health alone is not enough.** A green health check does not prove the mounted route surface matches the supported profile. Multiple surfaces must agree.

2. **Route presence is not runtime proof.** A registered route may exist but not be wired to the correct backend service, or may return data that does not match the supported posture.

3. **UI presence is not execution proof.** A button in the UI may have no backend route, or the route may exist but return errors. UI components must be verified against live backend responses.

4. **Task acceptance is not completion.** Queue enqueue ≠ worker execution ≠ provider response ≠ persistence ≠ UI receipt. Each layer must be independently verified.

5. **Event publication is not UI receipt.** SSE events may be dropped, delayed, or published without a consumer. Event-based state must be verified end-to-end.

6. **Docs-only scaffold is not release support.** Planning documents prove intent, not capability. Live supported-path proof is required for any release claim.

7. **Catalog presence is not support.** A provider or model appearing in the catalog does not prove it is part of the supported beta posture.

8. **Config presence is not reachability.** A configured provider URL or API key does not prove the provider is reachable, warm, or capable of serving requests.

9. **Smoke defaults are not live proof.** The Gemma E2B smoke default for Whoosh'd is a configuration default, not proof that the model is loaded and reachable.

## Proof Collection Procedure

For each campaign:

1. **Start state**: All proof is `not yet run`. Gate decision is `next-proof-needed`.
2. **Collect evidence**: Run verification commands, inspect endpoints, test UI components.
3. **Record evidence**: Document commands run, results observed, and any gaps.
4. **Make gate decision**: `go` if all required proof categories pass; `hold` if any gap blocks progression.
5. **Document decision**: Record in the campaign's `proof-pack.md` and `decision-log.md`.

## Gate Decision Escalation

If a gate decision is `hold`:

1. Document the specific missing or contradictory evidence.
2. Identify whether the gap is in the campaign scope or a dependency.
3. If in a dependency, escalate to the dependency campaign's backlog.
4. If in the campaign scope, create a task to collect the missing proof.
5. Do not proceed to the next wave until the hold is resolved.
