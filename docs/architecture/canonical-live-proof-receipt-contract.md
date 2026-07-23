# Canonical Live Proof Receipt Contract

## Purpose

Define the subordinate execution receipt produced when Codexify observes one
explicitly selected, already-running supported Compose project. The receipt
binds the existing machine/Git identity and static runtime identity to bounded
Docker state and a fixed health-probe suite.

The receipt is an intermediate proof artifact under ADR-041 and ADR-042. It is
not accepted canonical evidence by itself, trusted `latest`, proof storage,
promotion authorization, release approval, or a replacement for human decision
authority.

## Governing authority and boundaries

- GitHub `main` remains canonical code authority.
- VaultNode remains the sole canonical runtime and audit authority.
- Resonant Jones remains human decision authority.
- `authority_status` is `CANONICAL` only when the existing machine/Git identity
  collector reports both canonical-machine and canonical-repository candidacy.
- Hostname, project name, service state, Docker health, and successful HTTP
  probes cannot upgrade authority.
- The collector reuses the existing machine/Git and static runtime collectors;
  it does not duplicate their authority, repository, supported-profile,
  Compose, service-set, migration-head, or configuration-hash rules.

## Selected project and role

Every collection names exactly one Compose project and declares its role as
`serving` or `audit`. The static runtime identity retains the audit project and
optional serving project as distinct values. An `audit` observation must select
the declared audit project. A `serving` observation must select the separately
declared serving project. The role does not confer authority.

The selected repository, Compose files, project, and optional Compose
environment-file path are explicit inputs. Compose and environment files are
repository-relative. The environment file may be passed to Docker Compose
argument construction, but the collector does not read or emit its values.

## Read-only Docker command boundary

The collector invokes Docker with argument arrays, `shell=False`, captured
output, and an explicit timeout. Its complete command vocabulary is:

```text
docker version --format json
docker compose -f <compose-file>... [--env-file <repo-relative-file>] -p <project> ps --all --format json
docker compose -f <compose-file>... [--env-file <repo-relative-file>] -p <project> images --format json
```

The collector rejects every other Docker command with
`docker_command_not_allowed`. In particular it cannot invoke `up`, `down`,
`start`, `stop`, `restart`, `build`, `pull`, `run`, `exec`, `rm`, `kill`, or
`create`. It does not inspect logs, raw environment, mounts, arbitrary labels,
raw container configuration, database state, or commands inside containers.

Docker CLI absence, server unavailability, Compose unavailability, a missing
selected project, or an unavailable status prerequisite before observation
begins produces `BLOCKED`. Raw Docker output never enters the receipt. Only
safe client/server version identifiers, normalized supported-service state,
container identity, image identity, health, and exit status are retained.

## Service lifecycle rules

Required and optional service names come from the accepted supported profile.
Unexpected Compose services do not expand the proof scope. Missing optional
services are visible as `OPTIONAL_ABSENT` and do not fail the receipt.

Long-running required services must be `running`. When Docker reports a health
state, it must be `healthy`. The known initialization services `migrator`,
`graph-init`, and `model-prep` are one-shot services; when required, each must
have completed with exit code `0`. Missing, stopped, unhealthy, incomplete, or
failed required services produce `FAIL`, never `PASS`. Container logs are
outside this contract.

## Fixed loopback health suite

Operators provide credential-free API and frontend origins. Each origin must
use HTTP or HTTPS on `localhost`, `127.0.0.1`, or `::1`, without userinfo,
query credentials, fragments, or arbitrary paths. Cross-host redirects are
rejected. Operators cannot add or replace probes.

The ordered suite is:

1. API `GET /ping`: requires 2xx.
2. API `GET /health`: requires 2xx, normalized healthy status, matching and
   valid supported-profile identity, no profile mismatches, `release_hold`
   false, and selected-provider support when reported.
3. API `GET /health/chat`: requires 2xx plus completion-service success, Redis
   reachability, enqueue success, and a fresh worker heartbeat.
4. API `GET /api/health/llm`: requires 2xx, healthy/online status, available
   models, provider-runtime availability, matching supported-profile identity,
   and `release_hold` false.
5. Frontend `GET /`: requires a same-loopback-host 2xx or 3xx response.

Observed unhealthy HTTP or semantic results produce `FAIL`. A transport
timeout, malformed required JSON, oversized response, forbidden redirect, or
internal parsing failure after observation begins produces `ERROR`.

## Safe probe projection and secret boundary

Each probe records only its stable ID, `GET` method, fixed path, HTTP status,
start/completion timestamps, duration, outcome, exact response-body SHA-256,
bounded reason codes, and the minimum selected fields needed to evaluate the
contract. Raw bodies and request headers are never stored.

The receipt and result envelope must not include API keys, credentials, tokens,
private keys, database URLs, raw environment values, secret-bearing URLs,
arbitrary absolute host paths, Docker contexts, registry credentials, raw
errors, traces, mounts, labels, or raw command output. Unsafe operator inputs
fail closed. Unknown response fields are ignored rather than copied.

## Receipt identity and ordering

The collector owns `receipt_id`; caller-supplied IDs are forbidden. The form is
`live-proof-receipt-sha256-<lowercase-sha256>`. The digest covers deterministic
canonical JSON encoded as UTF-8 with sorted object keys and compact separators.
It covers the receipt except for `receipt_id` itself, including timestamps,
authority and execution outcome, predecessor identities, selected project and
role, Docker versions, service/image observations, probe hashes and safe
projections, executed command argument arrays, and reason codes.

Commands and probes retain execution order. Compose files retain explicit input
order. Services are ordered by service then container identity. Required and
optional service sets and reason-code arrays are normalized to stable order by
their owning collectors or this collector. Identical normalized observations
with identical timestamps therefore produce the same receipt ID.

## Outcome classification

| Outcome | Meaning |
|---|---|
| `PASS` | Docker prerequisites were available, every required service satisfied its lifecycle contract, every fixed probe passed, and receipt schema validation passed. |
| `FAIL` | The selected live runtime was observed and one or more required service or health assertions failed. |
| `BLOCKED` | A required prerequisite prevented live observation from beginning. |
| `ERROR` | Collection infrastructure, timeout, parsing, output bounds, or schema validation prevented a trustworthy classification after collection began. |

Failures, blockers, and errors remain distinct and visible. A valid `PASS`
receipt is still not canonical manifest acceptance, promotion approval, or
trusted `latest`.

## Schema validation and output

Every generated receipt is checked with the Draft 2020-12 validator against
`schemas/audit/canonical-live-proof-receipt.schema.json`. Validation failure
adds `receipt_schema_validation_failed`, forces collector outcome `ERROR`, and
prevents file output.

The CLI prints a stable result envelope to stdout. Optional `--output` accepts
only a repository-relative path, writes the receipt atomically after successful
schema validation, and refuses overwrite unless `--replace` is explicit. It
does not write a registry, manifest, promotion receipt, or trusted pointer.

## Relationship to canonical evidence

The receipt preserves provenance as an intermediate proof artifact. The
manifest producer now accepts a qualifying `PASS` receipt via
`live_proof_receipt_path` for `CURRENT_LIVE_PROOF` manifest generation.
Receipt bytes and identity are preserved as hashed manifest evidence with
explicit lineage. Receipt `PASS` is necessary but not sufficient for canonical
authority; a `PASS` receipt cannot upgrade provisional authority. The
generated manifest remains unpromoted evidence.

Still deferred are durable evidence storage, freshness evaluation,
cross-record resolution, supersession and contradiction resolution, promotion
receipts, trusted `latest`, consumer migration, and release approval.

## Non-goals

This contract does not add Docker lifecycle management, container execution,
operator-supplied commands, arbitrary probes, chat turns, ingestion proof,
provider mutation, migration execution, database queries, container logs,
manifest generation, evidence storage, freshness calculation, trusted
`latest`, GitHub Actions, or release approval.

## Related documents

- [`ADR-041`](./adr/041-vaultnode-canonical-machine-and-audit-authority.md)
- [`ADR-042`](./adr/042-canonical-audit-evidence-contract.md)
- [`Canonical Audit Evidence Contract`](./canonical-audit-evidence-contract.md)
- [`00 Current State`](./00-current-state.md)
