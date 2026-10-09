## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-09

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` remains in local-first Beta hardening with a separately gated Private Preview lane. Since the 2026-10-08 audit, only a 2026-10-09 release-accounting log landed; no implementation or supported-path qualification changed. The latest complete supported-Compose qualification remains `HOLD`.

## What changed recently

- Since the prior refresh, `main` added only the 2026-10-09 no-change accounting artifact; no implementation or qualification claim changed.
- Merged opt-in, same-node Private Preview messaging with durable request, consent, idempotency, rate, privacy, and two-account proof; default Beta remains excluded.
- Persisted authenticated account-intake provenance for coding runs and merged chat-only generic task-event SSE admission through durable completion-attempt and canonical-thread authority.
- Closed focused credential-purpose, mixed-principal, Hosted Room invitation, task-event, and agent snapshot authorization cases on `main`.
- Merged bounded workspace scratchpad, Memory Vault request-reference, and Pi telemetry test tightening; these are focused changes, not release qualification.
- Removed stale daily logs, added retired-ADR routing, and recorded explicit no-change checkpoints.

## PR #865 integration boundary

PR #865 retains its historical supported-Compose and native-candidate proof records, including [native candidate qualification](./proofs/runtime/2026-10-07-native-candidate-adoption-qualification.md), [protected checkpoint proof](./proofs/runtime/2026-10-07-live-candidate-protected-checkpoint.md), and [failed Stop recovery](./proofs/supported-compose/2026-10-05-chat-failed-stop-durable-recovery.md). Their evidence applies to the revisions and runtime paths recorded there. Conflict reconciliation preserves the deadline and worker-shutdown implementations alongside current-main account isolation and lazy embedding startup; it does not establish fresh integrated-tip Compose qualification or authorize candidate adoption. Non-local non-streaming provider calls now consume their full HTTP response inside the same accepted deadline, active-task receipt lookup advances through bounded history pages, and idle document intake uses an owned two-second blocking transport bound. These are focused code/test changes; no cloud-provider, live candidate, or release qualification is inferred. The release gate remains `HOLD`.

## Current supported reality

- The named supported install path is local Docker Compose using `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported contract covers local inference, ordinary chat, durable threads/messages/tasks, document upload/embed/readback, workspace retrieval, identity/ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, migrations, health, browser cold/warm chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, and deadline behavior at evaluated tips.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Account import remains bounded: isolated evidence covers browser staging, materialization, ownership/readback, and later vector observations, not complete recall.
- Same-node human messaging is enabled only in the opt-in Private Preview profile; it does not grant project, thread, Guardian, federation, attachment, or realtime authority.

## Not yet true / do not assume

- Do not call the supported path release-ready; the latest complete qualification is `HOLD`.
- Do not infer current-tip restart/shutdown recovery, browser transcript coherence before reload, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the current complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat focused tests, disposable PostgreSQL, isolated Preview proof, docs, or route presence as deployed/public-ingress qualification.
- Do not treat the two changed architecture knowledge-graph JSON nodes as valid metadata; committed conflict markers currently make both fail JSON parsing.
- Do not infer exact unavailable-model rejection: the current complete Compose proof recorded accepted work with model substitution and no assistant fallback flag.
- Do not treat focused auth tests, disposable PostgreSQL, isolated Preview proof, docs, or route presence as deployed/public-ingress qualification.
- Do not treat the focused workspace, Memory Vault, or Pi telemetry changes as evidence of complete supported-path qualification.
- The two architecture knowledge-graph records now parse and match their source hashes on this repair branch; their freshness remains stale until the declared anchors are reviewed.
- Do not treat direct messaging, activation, browser/import, connectors, Watchdog, retention, hosted sandbox, Atlas, Pi, or branch-local work as default Beta support without current-main qualification.
- Do not infer cross-node messaging, federation, or autonomous coding-worker support from merged contracts or implementation slices.
- Do not treat uncommitted worktree changes or local-only audit commits as synchronized public-main state.

## Active blockers

- Run the complete supported-Compose qualification on current `main`, including exact-model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Resolve the explicit-model worker/test contradiction and retain fail-closed behavior with no silent substitution.
- Reproduce and repair the new-thread authored-message projection gap, then rerun the real browser and durable-readback path.

- Complete a fresh natural import-to-recall run through provider context, answer persistence, and negative scope control.
- Requalify Private Preview activation, Chroma/application, provider/persistence/isolation, approved canary, and public-ingress claims on intended live paths.
- Repair and validate the conflict-marked architecture knowledge-graph metadata before relying on those nodes.
- Reconcile the local-only `main` commits before treating local artifacts as published state.
- Review the reconciled architecture knowledge-graph records and their freshness-invalidating anchors before relying on them as current metadata.
- Publish or explicitly reconcile the local-only `main` commits before treating local artifacts as published state.


## This week's priorities

1. Freeze current `main` and run the full supported-Compose proof bundle.
2. Review architecture knowledge-graph metadata freshness on the integrated tip.
3. Close the explicit-model rejection contradiction before provider execution.
4. Repair and reprove browser new-thread transcript projection.
5. Prove uninterrupted account import, then reconcile the local-main publication gap.

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
- **Browser side-panel / Browser Host release surface** — `remaining gate`
  requires: live Electron host qualification, production Guardian
  authentication, and supported release proof. The private unpacked Chrome
  side panel remains internal-only, and Browser Host remains a
  development/internal unsigned proof; neither is generally Beta-supported.

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

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, and authorization evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration, browser, account-import recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Each claimed Preview or public-ingress path has current live evidence, with no claim inferred from focused tests alone.
- [ ] Changed release metadata parses cleanly and its freshness points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
