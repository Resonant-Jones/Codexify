# Anthropic Export Profiler

> Classification: architecture tooling (read-only evidence)
> Status: normative for the profiler surface; does not widen release support
> Governing contract: `docs/architecture/account-export-restore-contract.md`
> ADR impact: none

## Purpose and evidence boundary

`scripts/anthropic_import/profile_anthropic_export.py` is a standalone,
read-only CLI that inspects a real Anthropic account export and emits a
deterministic **structural evidence report**. It is fixture archaeology: it
answers, from observed evidence, what Anthropic actually placed in the export.

The profiler describes schema **shape only**. It never imports data, never
mutates the source package, never extracts ZIP members to disk, and never
writes to any Codexify runtime store (Postgres, Redis, Chroma, Neo4j, media
storage, Guardian state, or any service). It imports only the Python standard
library and does not invoke the existing Claude or OpenAI importer paths.

Profiler output is **observed evidence, not an Anthropic schema contract**. It
does not import data and does not widen Codexify's supported release promise.
Durable Anthropic account import remains explicitly deferred.

## Why the profiler exists before the importer

Codexify does not possess a normative Anthropic personal-export schema, and
Anthropic full-account ZIP import is not a supported runtime path. Building an
importer blind would force guesses about undocumented structure. The profiler
lets an operator (or a future importer task) ground normalization decisions in
observed structural evidence first: container key names, message shape, branch
relationships, project/memory/account surfaces, and attachment/artifact hints.

This mirrors the existing OpenAI account-export posture, where a diagnostic
inventory and provenance contract already precede durable migration, and where
imported third-party records become canonical Codexify state while retaining
source provenance.

## Supported input types

- a ZIP archive (inspected in-place; members are never extracted)
- an extracted directory (recursive; symlinks rejected; confined to the root)
- an individual JSON file (treated as a one-file package)

## CLI

```
python scripts/anthropic_import/profile_anthropic_export.py <input> --output <report.json>
```

Example:

```
python scripts/anthropic_import/profile_anthropic_export.py /path/to/claude-export.zip --output /tmp/anthropic-export-profile.json
```

A short human-readable summary is printed to stdout: input package kind,
package fingerprint (truncated sha256), file count, JSON file count, warning
count, and the output report path. No source message content or identity
values are printed.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Profiling completed, including completion with bounded warnings. |
| `2` | Invalid arguments, missing input, unsupported input type, or unwritable output. |
| `3` | Unsafe archive structure, corrupt ZIP container, duplicate member path, path traversal, symlink, or other structural-integrity rejection. |

## Safety rules

- ZIP members are streamed via `zipfile` and inspected without extraction.
- Member paths are normalized to canonical POSIX relative form.
- Rejected before any content is analyzed: absolute paths, `..` traversal,
  symbolic links (mode-bit detection), duplicate normalized paths, and corrupt
  ZIP containers.
- ZIP members are processed in deterministic normalized-path order.
- Directory input rejects symbolic links and ensures every inspected path
  remains beneath the supplied root.
- Reads are bounded by named constants (file count, per-member bytes, total
  bytes, JSON depth, retained keys, warnings). Overflow is reported as
  `analysis_limit_reached` warnings and flagged via `package.analysis_truncated`
  rather than silently dropped.

## Privacy and redaction rules

The report must never carry message text, conversation or project titles,
usernames, account names, email addresses, UUID or other identifier values,
URLs, prompts, file contents, attachment contents, or memory text. A central
allowlist is the only place scalar **values** may be aggregated:

- role/sender labels (short, structural; bounded distinct count)
- structured content-block `type` labels
- coarse timestamp format categories (derived, e.g. `iso8601`, `epoch_seconds`)
- safe boolean presence flags
- file extensions and detected broad types

Everything else is recorded as key **names** and counts. The report never
copies arbitrary scalar values.

Relative package paths are retained because they are required for structural
inventory, but the operator's absolute source path is never emitted, and
UUID-shaped path stems (for example a sharded `projects/<uuid>.json` layout)
are scrubbed to `<uuid>` while preserving directory shape, extension, and
deterministic uniqueness.

Determinism: repeated profiling of identical input produces byte-identical
UTF-8 JSON (sorted keys, stable list ordering, two-space indentation, one
trailing newline, no generated timestamp).

## Report schema (`anthropic_export_profile_report_v1`, profiler version `1`)

Top-level fields:

- `report_schema` — exact value `anthropic_export_profile_report_v1`.
- `profiler_version` — exact value `1`.
- `package` — `kind` (`zip` | `directory` | `json`), `display_name` (basename
  only), `sha256`, `file_count`, `json_file_count`, `binary_file_count`,
  `total_bytes`, `analysis_truncated`.
- `files` — ordered inventory; each record may include `relative_path`,
  `size_bytes`, `compressed_size_bytes` (ZIP only), `sha256`, `extension`,
  `broad_type`, `json_parse_status`, `json_top_level_type`, and
  `json_top_level_keys`. Never parsed user-authored values.
- `candidate_surfaces` — evidence-backed candidate classifications
  (`conversations`, `projects`, `memories`, `users_or_account`,
  `attachments_or_files`, `artifacts`, `unknown_json`), each with the
  structural `evidence_keys` that caused the classification. Classification is
  always `candidate`, never authoritative.
- `conversation_shape` — whether conversation-like objects were observed,
  candidate conversation count, observed conversation/message object keys with
  occurrence counts, message-container keys, message object keys, role-field
  names, bounded role values (for recognized role fields such as `sender`/
  `role`), timestamp-field names and coarse format categories, identifier-,
  model-, project-reference-, parent-relationship-, and attachment-reference
  field names, and observed content-block type names. No IDs, titles, text, or
  timestamps are emitted.
- `capabilities_observed` — boolean observed flags with bounded evidence lists
  (structural keys + relative paths only) for: `flat_conversation_array`,
  `nested_conversation_container`, `message_parent_links`, `project_records`,
  `conversation_project_links`, `account_metadata`, `memory_records`,
  `attachment_references`, `binary_payloads`, `generated_file_evidence`,
  `artifact_evidence`.
- `unknown_structures` — counts (and bounded relative paths / structural
  labels) for unknown top-level JSON shapes, unknown content-block types, and
  unknown message keys. No raw content values.
- `warnings` — bounded records with `code`, optional `relative_path`, and
  `message`. Examples: `json_parse_failed`, `analysis_limit_reached`,
  `unknown_json_shape`, `possible_branch_structure`,
  `binary_without_reference`, `reference_without_binary`.
- `errors` — empty on successful reports; structural rejection terminates with
  exit code `3` instead of producing a misleading success report.

## Capability classifications

Capabilities are reported as `true` only when positive structural evidence was
observed, with a bounded evidence list naming only structural keys and relative
paths. They are evidence of shape, not proof of importability:

- Branch/parent links are noted when parent-relationship field names
  (`parent_message_uuid`, `parent_uuid`, `parent_message_id`, `parent_id`, and
  unknown `parent*` alternatives) appear on message objects.
- Project/memory/account/artifact surfaces are detected from wrapper keys,
  record-list shape, or observed record-family directory names
  (for example sharded `projects/<uuid>.json` files).
- Attachment references, generated-file hints, and artifact hints are reported
  independently and only when explicit structural keys support each
  classification. A text extract is never labeled a binary; an attachment is
  never labeled uploaded or generated without positive evidence.

## Interpretation guidance

- Treat the report as a snapshot of one observed export, not a schema spec.
  Field names may vary across Anthropic export versions.
- `candidate` classifications are starting points for a future importer, not
  acceptance gates. Missing fields remain missing; the profiler does not infer
  undocumented semantics.
- `reference_without_binary` means attachment references were observed without
  bundled binaries; `binary_without_reference` means binaries were present
  without observed reference fields. Both are heuristic and bounded.
- Conversation linearity must not be assumed. `message_parent_links` indicates
  branching that a future importer would have to resolve.

## Explicit non-goals

- This tool does not import data and does not add Anthropic import support.
- No current release-truth document is changed to claim Anthropic import
  support. `docs/architecture/00-current-state.md` remains the release gate.
- The profiler does not create, widen, or satisfy any ADR.

## Fixture confidentiality

Real user exports and generated profile reports must never be added to this
repository. The committed tests in `tests/scripts/test_anthropic_export_profiler.py`
use only temporary synthetic files. Operators should write profile reports to
locations outside the repository and treat any real export as confidential
user data.
