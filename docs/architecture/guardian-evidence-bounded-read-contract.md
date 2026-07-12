# Guardian Evidence Bounded Read Contract

## 1. Purpose

This contract defines the future bounded evidence-read seam that may sit between
a validated `ReducerInputBundle` and a future Guardian Evidence Packet
generator. It specifies which explicitly allowed local evidence references may
be read, how read results are bounded, and which interpretations remain
forbidden.

## 2. Status

This is a docs-only contract. It does not implement a bounded evidence reader,
does not read source references, and does not add a runtime or operator read
surface. It does not modify scripts, does not modify Makefile, does not read
`source_ref` targets, does not generate `GuardianEvidencePacket` output, and
does not alter existing packet fixtures.

This contract does not read source_ref targets.
This contract does not generate a `GuardianEvidencePacket` output.
This contract does not add a runtime or operator read surface.
This contract does not implement runtime reducer behavior.
This contract does not implement evidence ingestion.
This contract does not add persistence.
This contract does not add UI.
This contract does not add CI/default release gating.
This contract does not authorize execution.
This contract does not authorize source mutation.
This contract does not authorize Pi Loop invocation.
This contract does not authorize provider execution.
This contract does not authorize Codexify ingestion.
This contract states that a future bounded evidence reader may read only explicitly allowed local source references.
The future bounded evidence reader must not follow network URLs; it must not read secrets; it must not call command bus; it must not call Codex Runner; it must not mutate WorkOrders; and it must not write Execution Ledger entries.

### Implementation status

Local bounded evidence-read tooling now exists at
`scripts/guardian/read_bounded_evidence.py`. It accepts a validated
`ReducerInputBundle` JSON file, validates the bundle before reading source refs,
reads only explicitly referenced local allowlisted `source_ref` files, never
follows network URLs, blocks secret-like paths, and returns bounded read
artifacts with content hashes, bounded excerpts, provenance, warnings, errors,
and limits. It does not generate `GuardianEvidencePacket` output, implement
packet generation or runtime reducer behavior, ingest evidence, or call command
bus, Codex Runner, live validation, orchestration, Pi Loop, provider
execution, source mutation, WorkOrder mutation, or Execution Ledger writes. It
is not CI/default release gating or release support expansion.
The reader returns bounded read artifacts.

Invocation:

```bash
python3 scripts/guardian/read_bounded_evidence.py docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json --json
```

The local Make target `make guardian-evidence-bounded-read` now runs:

```bash
python3 scripts/guardian/read_bounded_evidence.py docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json --json
```

It validates the input bundle before bounded reading, reads only explicitly
referenced local allowlisted `source_ref` files, and returns bounded read
artifacts only. It does not generate `GuardianEvidencePacket` output, implement
packet generation or runtime reducer behavior, ingest evidence, or become CI/
default release gating or release support expansion.

### Static result fixture

The static bounded-read result fixture now exists at
`docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`.
It records the current local-tooling bounded-read output shape as a static proof
fixture only. It is not packet generation, packet output, evidence ingestion,
source truth approval, authority promotion, runtime reducer support,
CI/default release gating, or release support expansion.
This is a static proof fixture only.

The bounded-read fixture can feed local stdout-only packet generator tooling.
Bounded-read success is not packet generation by itself; packet generation is a
separate local tool. Bounded-read output remains not source truth approval,
authority promotion, evidence ingestion, WorkOrder mutation, or Execution
Ledger write.

Stdout-only packet generator tooling now has a local Make target:
`make guardian-evidence-packet-generate`. The bounded-read fixture can feed
this target through generator tooling. Bounded-read success remains not packet
generation by itself. Packet generation remains stdout-only local tooling.
Bounded-read output remains not source truth approval, not authority promotion,
not evidence ingestion, not WorkOrder mutation, and not Execution Ledger write.

## 3. Scope

The contract covers future local-only source-reference resolution, bounded
content excerpts, provenance, hashes, truncation, warnings, and handoff to a
future packet generator. It does not define evidence ingestion, durable truth,
or execution authority.

## 4. Current Truth

- Guardian Evidence work remains local static tooling, contracts, fixtures, and
  diagnostics-only dry-run tooling.
- Static packet and `ReducerInputBundle` templates and fixtures exist.
- Static packet and input-bundle validation exist.
- The dry-run loader maps bundle metadata only and must not read `source_ref`
  targets.
- A docs-only packet generator contract exists, but no packet generator exists.
- No bounded evidence reader exists.
- Static validation does not prove `source_ref` truth or authorize reading it.

## 5. Why This Exists

A future generator must not turn a symbolic `source_ref` into an ambient file
read. A separate bounded-read contract makes local path scope, content limits,
provenance, and blocked-read semantics explicit before any implementation can
prepare evidence for packet generation.

## 6. Bounded Read Is Not Authority

A successful bounded read proves only that a permitted local artifact was read
within declared limits. It does not prove the artifact is correct, current,
complete, trusted, or authoritative. Read success must never promote evidence
to authority or set Guardian authority locks.

## 7. Bounded Read Is Not Execution

Reading content is not executing content. A future bounded evidence reader must
never invoke scripts, commands, binaries, notebooks, workflows, providers, or
any other `source_ref` target.

## 8. Bounded Read Is Not Evidence Ingestion

Read artifacts are transient bounded evidence-preparation results. They are not
Codexify ingestion, durable truth, receipts, or Execution Ledger records.

## 9. Bounded Read Is Not Packet Generation

Bounded reading prepares a read result only. It does not create or validate a
`GuardianEvidencePacket`, infer claims, select authority, or replace the future
packet generator contract.

## 10. Allowed Read Sources

A future bounded evidence reader may read only explicitly allowed local source
references named by a validated input bundle and permitted by a future
bounded-read allowlist:

- `docs/architecture` files explicitly referenced by validated input bundles.
- `docs/architecture/fixtures` files explicitly referenced by validated input
  bundles.
- `docs/architecture/templates` files explicitly referenced by validated input
  bundles.
- Test result summary files explicitly produced by local validation tasks, if a
  later implementation explicitly names them.
- Static proof index files explicitly named by a later implementation.

The allowlist must be explicit, repository-scoped, and auditable. A reference
being present in a bundle is not by itself permission to read it.

## 11. Disallowed Read Sources

A future bounded evidence reader must reject:

- Absolute paths outside the repository.
- Network URLs and network-backed references.
- Secrets files and environment files such as `.env`.
- Private key files and Git credentials.
- Database files and Docker volumes.
- Runtime logs unless a separate contract explicitly permits them.
- User home directories outside the repository.
- `/Volumes/Dev_SSD/Codex-Runner` unless a separate read contract explicitly
  allows it.
- Any file not explicitly referenced by a validated input bundle or future
  bounded evidence-read allowlist.

## 12. Source Reference Resolution Rules

Resolution must accept only the reference forms named by the future allowlist.
The resolver must normalize a candidate path, reject traversal and symlink
escapes, verify that the result remains inside the repository boundary, and
record both the original `source_ref` and the resolved repository-relative
path. Resolution must not fetch, execute, mutate, or silently reinterpret a
reference.

## 13. Local Path Boundary

The repository root is the maximum local boundary. A future implementation
must reject `..` escapes, absolute paths outside the repository, symlinks that
resolve outside the repository, mounted external repositories, and implicit
home-directory expansion. Local does not mean unrestricted.

## 14. Network Boundary

Network access is forbidden. A future bounded evidence reader must not follow
`http`, `https`, `ssh`, `git`, cloud-storage, database, or other network URLs.
`source_ref_network_url_blocked` is a required blocked-read diagnostic.

## 15. Secret and Sensitive Content Boundary

The reader must not read secrets or sensitive credentials, including `.env`
files, key material, tokens, Git credentials, credential stores, or database
credentials. A path or content type with secret risk must be blocked before
content is returned. Use `source_ref_secret_risk_blocked` for that outcome.

## 16. Size and Truncation Rules

Every future implementation must declare byte and excerpt limits before a read.
It must stop at the configured limit, set `excerpt_truncated` when content is
cut, preserve `omitted_content_reason`, and emit `content_truncated`. A file
that exceeds an implementation's permitted pre-read size may return
`too_large` without returning content. Limits are safety bounds, not a reason
to imply completeness.

## 17. Content Hash and Provenance Rules

If a bounded implementation can compute a content hash within its limits, it
may report it as continuity evidence. A hash match proves file continuity, not
correctness or truth. If unavailable, the result must preserve
`content_hash_unavailable`. Provenance must identify the contract version,
source reference, resolved path, read time, reader identity, and limits used.

## 18. Read Artifact Shape

A future implementation must return a JSON-like
`GuardianEvidenceBoundedReadResult` with at least:

```text
GuardianEvidenceBoundedReadResult:
  schema_version
  read_contract_version
  input_bundle_ref
  source_ref
  resolved_repo_relative_path
  read_status
  content_hash
  content_excerpt
  excerpt_truncated
  omitted_content_reason
  warnings
  errors
  provenance
  limits
```

The artifact is a bounded diagnostic handoff, not a packet and not durable
truth.

## 19. Read Result Semantics

Required `read_status` values are:

- `read`
- `skipped`
- `blocked`
- `missing`
- `too_large`
- `unsupported`

`read` means only that bounded content was returned. `blocked`, `missing`,
`too_large`, and `unsupported` preserve why content was not returned.
`skipped` records an intentional bounded decision without implying that the
source was inspected.

## 20. Error and Warning Semantics

The future result vocabulary must preserve these warning/error concepts:

- `source_ref_outside_repo`
- `source_ref_network_url_blocked`
- `source_ref_secret_risk_blocked`
- `source_ref_missing`
- `source_ref_too_large`
- `source_ref_unsupported_type`
- `source_ref_not_allowlisted`
- `content_truncated`
- `content_hash_unavailable`

Warnings and errors are diagnostics for human review. They must not authorize
repair, retries into execution, source mutation, or claim promotion.

## 21. Relationship to ReducerInputBundle

`ReducerInputBundle` remains a bounded declaration of input metadata. Static
input-bundle validation checks shape and guardrails only; it is not read
approval. A future reader may consume a validated bundle only through a
separate implementation that applies this contract's allowlist and limits.

## 22. Relationship to Dry-Run Loader

The dry-run input-bundle loader remains diagnostics-only and must not read
`source_ref` targets. Loader success is not bounded reading, packet generation,
evidence ingestion, source truth approval, or authority promotion.

## 23. Relationship to Packet Generator

The [Guardian Evidence Packet Generator Contract](./guardian-evidence-packet-generator-contract.md)
is a separate docs-only future seam. A future packet generator must depend on
bounded read results before turning source references into packet evidence.
Bounded-read success is not authority, source truth approval, evidence
ingestion, execution, WorkOrder mutation, or an Execution Ledger write.

## 24. Relationship to Static Packet Validation

Static packet validation checks packet shape and guardrail presence only. It
does not authorize source reads, validate the truth of read content, or convert
a bounded read result into a packet.

## 25. Relationship to Execution Ledger and WorkOrder

Bounded reading must not mutate WorkOrders or write Execution Ledger entries.
Future adoption of either surface requires a separate explicit contract,
provenance rules, and an independently authorized write path.

## 26. Relationship to UI and CI

This contract does not add an API route, UI, dev-build test button, CI
integration, default release gate, or release support expansion. Future UI or
CI use requires separate contracts and explicit opt-in boundaries.

## 27. Forbidden Interpretations

This contract must not be interpreted as:

- A bounded reader implementation.
- Permission to read arbitrary `source_ref` targets.
- Source truth approval or evidence authority.
- Packet generation or runtime reducer behavior.
- Evidence ingestion, receipt trust, Execution Ledger truth, or WorkOrder
  mutation.
- Execution, source mutation, Pi Loop invocation, provider execution, or plan
  execution.

The future reader must not execute source references, mutate source references,
follow network URLs, read secrets, call command bus, call Codex Runner, invoke
live validation or orchestration, write receipts, mutate WorkOrders, or write
Execution Ledger entries.

## 28. Future Allowed Slices

The following are future tasks only and are not implemented here:

- Bounded evidence-read implementation.
- Bounded evidence-read focused tests.
- Bounded evidence-read Make target.
- Generated read-result fixture.
- Packet generator implementation.
- Packet generator focused tests.
- Packet static validation integration.
- Read-only operator surface contract.
- Execution Ledger adoption contract.
- WorkOrder mapping contract.
- CI opt-in validation contract.

### Generated packet fixture

A static generated GuardianEvidencePacket fixture now exists at
`docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`.
It was produced by the local stdout-only generator
(`scripts/guardian/generate_evidence_packet.py`) using this bounded-read fixture as
input. The fixture is a static packet object derived from bounded-read output. It is
not packet generation by itself, not runtime reducer output, not evidence ingestion,
not WorkOrder mutation, not an Execution Ledger write, and not release support
expansion. The fixture preserves evidence refs with content hashes, the skipped
entry as uncertainty, all forbidden interpretations, and all authority locks false.

## 29. Bottom Line

This contract makes a future local bounded evidence-read seam explicit without
implementing it. A future reader may read only explicitly allowlisted local
references, return bounded artifacts with provenance and uncertainty, and stop
at the read boundary. Bounded reading is not execution, evidence authority,
source truth approval, receipt trust, WorkOrder mutation, Execution Ledger
write, packet generation, or release approval.

### Required future conceptual flow

```text
Validated ReducerInputBundle
  -> future bounded evidence reader
  -> GuardianEvidenceBoundedReadResult
  -> future packet generator
  -> GuardianEvidencePacket
  -> static packet validator
  -> human/operator review
  -> future UI, Execution Ledger, WorkOrder, CI, or runtime use only through separate contracts
```

The flow states that bounded reading is not execution, not evidence authority,
not source truth approval, not receipt trust, not WorkOrder mutation, not
Execution Ledger write, and not release approval.
