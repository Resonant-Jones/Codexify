## Purpose

This file is the canonical short-form source of truth for Codexify’s current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-09-06

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a gated private-preview lane. Recent mainline work improved bounded profile, sharing, and worker-diagnosis seams, but established no new release-ready runtime path or wider Beta support boundary.

## What changed recently

- Persona Profile authority, account-scoped persistence, export coverage, acceptance-time snapshots, and five-field runtime application landed with focused tests; broad Studio controls remain outside runtime enforcement.
- ShareSheet async handling now rejects stale search/send completions and surfaces relationship-load failure with retry coverage.
- A proof-only Tester worker lineage bridge confirmed that the historical bind/import race still applies to `main`; the fail-closed readiness predicate and fresh Tester runtime proof remain absent.
- Pi’s Anthropic coding default was reconciled to `claude-sonnet-4-6` with contract/proof coverage; this remains internal coding-worker qualification.
- Private-preview migration/recovery evidence and one-slot local chat-worker admission remain bounded prerequisites, not provider or persistence closure.
- The 2026-09-06 mainline log records no additional implementation or runtime qualification today.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary covers local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this doctrine is not current-tip qualification.
- Mainline has focused coverage for project lifecycle, conversation origin, document artifacts, Guardian Chat, account import, mobile shell, Persona Profile, and ShareSheet paths; authenticated supported-path browser proof remains separate.
- Persona Studio persistence is account-scoped and runtime-active only through the current five-field projection; broad voice, tools, permissions, retrieval, and connector fields remain inert or local.
- Valid account-import multipart batches are accepted and durably staged on the server path; the Safari/WebKit envelope failure remains unrepaired.
- Private-preview migration preservation/readback, scheduled reconciliation, Guardian secret rotation, Cloudflare ingress, and private-profile People/Share behavior have bounded evidence without guest admission or Beta widening.

## Not yet true / do not assume

- Do not assume current-tip Compose health, model inventory, terminal chat, durable assistant readback, retrieval, queue/worker execution, locks, terminal events, or recovery closure.
- Do not treat the Tester lineage bridge as a startup repair or fresh runtime qualification; no current bind-readiness predicate has landed.
- Do not treat private-preview admission serialization, migration/recovery, or health/read results as live provider, persistence, observability, isolation, or canary proof.
- Do not treat Persona Profile persistence, acceptance snapshots, ADR-082, or focused UI tests as broad configuration enforcement or browser proof.
- Do not treat CE-L1/Pi qualification, Chroma state, hosted-sandbox partial conformance, or Watchdog contracts as release-supported runtime behavior.
- Do not infer shipped reality from another checkout, local-only artifacts, mutable `latest`, planning language, or docs alone; attachments, federation, and cross-node messaging remain deferred.

## Active blockers

- Fresh supported-Compose closure is missing at the current `main` tip, including health, chat, persistence/readback, retrieval, queue/worker, locks, and terminal events.
- The Tester worker bind-readiness repair and fresh isolated runtime proof remain open; the historical diagnosis is applicable but static.
- Private-preview provider execution, persistence, observability, tester isolation, approved non-admin canary, and DeepSeek requalification remain open.
- Fresh-state Chroma startup/retrieval qualification remains unresolved; it is derived state, not canonical data.
- CE-L1 still lacks live provider/model execution, terminal durable result, and source-thread readback.
- Project-ownership convergence, Safari upload repair, authenticated browser gates, Watchdog policy/model, immutable image retention, and hosted-sandbox qualification remain unclosed.

## This week’s priorities

1. Land the bounded fail-closed Tester bind-readiness predicate, then run fresh isolated Tester proof.
2. Run current-main supported-Compose closure for health, chat, persistence/readback, retrieval, queue/worker, locks, and events; requalify Chroma.
3. Requalify private-preview provider/persistence/canary and CE-L1 live execution/readback with current credentials and source-thread evidence.
4. Close Project ownership, Safari upload, authenticated browser, Watchdog, retention, and hosted-sandbox gates.

## Release classes

The five release classes below are accepted architecture per ADR-069. They are
human-facing release interpretations over the existing Product Architecture
Assertion dimensions and the `00-current-state.md` short-form authority, not
new schema enums. Evidence maturity and support posture remain orthogonal
under ADR-069. Support doctrine does not prove every current-tip gate is
green; the "Not yet true / do not assume" and "Active blockers" sections above
remain authoritative for the present live-state truth.

### Beta Supported

The current Beta Supported envelope is the local-first supported install
path and its core surfaces, already enumerated in the "Current supported
reality" section above and accepted by ADR-069:

- Local Docker Compose runtime with the local-only default provider posture
  (`CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`,
  `LLM_PROVIDER=local`).
- Local inference and the supported local profile.
- Ordinary chat, durable threads / messages / tasks, and project / thread /
  workspace navigation.
- Documents and media ingestion on currently implemented supported formats.
- Embedding and workspace-scoped retrieval.
- Codexify-native identity / authentication boundaries and account-scoped
  ownership behavior.
- Operator-visible health and configuration truth required to run the
  self-hosted node.

This is support doctrine, not current-tip qualification. The "Not yet true
/ do not assume" and "Active blockers" sections above continue to bound what
is provably green on the current `main` tip. Implementation presence in a
code path does not promote a capability to Beta Supported; only the
architecture-accepted support envelope under ADR-069 does.

### Beta Bounded / Conditional

Surfaces intentionally inside the Beta envelope but only under an explicit
authority, topology, provider, mode, or capability boundary. The
classification below is the current accepted one; no new bounded surface
is added by this section.

- Persona Studio: account-scoped profile creation / editing, persistence,
  selection, and application of the currently implemented five-field
  runtime projection to ordinary chat. TTS / voice execution, unsupported
  permission authoring, unsupported retrieval-policy execution, and
  "preview UI equals enforcement" claims are excluded from this
  promotion.
- Import / continuity entry surfaces: OpenAI / ChatGPT export import,
  Task Prompt Archive, owner-scoped retry / recovery behavior already
  implemented, and account export / restore to the exact extent supported
  by the existing contract and implementation. Not every historical
  corpus, provider export format, or migration shape is claimed.
- Repository intelligence on the supported local single-user path:
  repository candidate discovery, explicit repository import,
  account / Project `RepositoryBinding`, direct Project-bound repository
  search, and ordinary-chat repository search exposure only when
  Guardian resolves exactly one valid active binding and existing
  authority checks pass. Remote / multi-user / Hosted-Room repository
  authority remains outside this bounded Beta claim.
- Bounded Guardian tool execution: read-only health capability, and
  bounded Project repository search where current eligibility /
  authority checks pass. Advertised-subset authority, Guardian-owned
  execution authority, exact capability eligibility, bounded command
  count, and provider capability checks are preserved. Arbitrary tools,
  arbitrary write operations, and generic shell / filesystem execution
  are not promoted.
- MCP / extensibility: the public MCP extension posture may be described as
  part of Beta only as a bounded extension interface. A general plugin
  marketplace, plugin SDK internals as public Beta API, and arbitrary
  plugin execution bypassing Guardian policy are not claimed.
- Desktop / Tauri client (if current `main` still contains the functioning
  local desktop / Tauri presentation layer): Beta Bounded / Conditional
  when used as a client of the same supported local Guardian node. Not a
  packaged production desktop distribution, not auto-update support, not
  an independent desktop persistence / runtime authority, not a separate
  release topology not currently proven.

### Internal

The following remain explicitly internal, not user-facing release promises:

- direct Command Bus HTTP / control-plane API
- plugin SDK internals
- generic tools / API tools surfaces currently marked internal or
  quarantined
- developer-only diagnostics
- unsafe operator mutation surfaces
- implementation / control-plane mechanisms that support Beta behavior
  without being user-facing promises
- Pi 0.82.1 wrapper/API, source-vendor, identity, framing, and telemetry
  surfaces (per the "Current supported reality" / "Not yet true" sections
  above; non-inference / OAuth-readiness qualification; not a
  user-facing release promise at the current `main` tip).
- CE-L1 wiring (lives in code paths and is required to close active
  blockers, but remains internal / qualification pending — see below).
- Campaign / coding-worker substrate (operational substrate that supports
  Beta behavior; not a user-facing release promise).

Implementation presence of Pi, CE-L1, or coding-worker wiring does not
promote those surfaces to Beta Supported merely because their code paths
exist.

### Qualification Pending

Intended or plausible Beta surface with implementation present, but a
specifically named proof / authority / operational gate remains open.
Each entry below names its explicit `remaining gate` rather than only
saying "not supported," per the ADR-069 Qualification-Pending Doctrine.

- **Coding Loop** — `remaining gate` requires: live provider/model
  execution, terminal durable result, and source-thread readback on the
  claimed supported profile. CE-L1 wiring remains internal / qualification
  pending; no `LIVE_EXECUTOR_PROVEN_CANONICAL` is emitted.
- **Hosted Rooms** — `remaining gate` requires: clean supported / tester
  startup and owner / guest live semantic proof after migration repair.
- **DeepSeek / private-preview provider lane** — `remaining gate` requires:
  required credentials, authenticated provider-specific persisted runtime
  proof, and explicit supported-profile promotion.

### Out of Beta

Explicitly excluded from the present Beta promise under ADR-069 and not
classified as Qualification Pending:

- TTS / voice — Out of Beta
- federation — Out of Beta
- unrestricted autonomous / recursive agent execution
- arbitrary write-capability tool use
- generic shell / filesystem execution through ordinary Beta chat
- public Command Bus exposure
- generic cron / unattended automation
- generic connectors without separate qualification
- graph-write / Neo4j-derived-write behavior where the supported path remains
  flagged off or quarantined
- remote / multi-user repository execution not covered by a separately
  accepted authority contract and live proof

## Release definition right now

- [x] Supported local Compose path and Beta boundary are defined on `main`.
- [x] Support doctrine, bounded/internal surfaces, qualification-pending work, and unproven evidence remain distinct.
- [x] Private-preview migration preservation/readback and ingress proofs are bounded without guest admission or release widening.
- [ ] Current-tip Compose proves healthy startup, model inventory, terminal chat, persistence/readback, and event delivery.
- [ ] Queue, worker bind readiness, locks, migrations, configuration, recovery, browser, and account-import claimed-path gates are green.
- [ ] Every claimed preview/provider lane has current-main proof for execution, durable readback, isolation, and recovery where applicable.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
