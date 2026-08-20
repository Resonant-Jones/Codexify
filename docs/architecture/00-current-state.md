## Purpose

This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-19

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise
- the current human-facing Beta support interpretation

It is **not** a substitute for accepted ADRs or canonical Product Architecture Assertions. The Canonical Authority Hierarchy in [ADR-069](./adr/069-codexify-beta-runtime-support-boundary.md) governs how this file, accepted ADRs, canonical posture assertions, the supported runtime profile, and proof / test / code sources must be reconciled when they appear to disagree.

## Audited repository revision

`0f494b398b79f73c077322ef82456027e51d38f1` (pre-change audited HEAD for the Anthropic conversation-import Beta-boundary reconciliation; includes the successful 2026-08-19 Anthropic account-import supported-runtime proof R2).

## Current phase

`main` is in local-first beta hardening at `0f494b398`. ADR-069 was accepted 2026-08-14 by Resonant Jones. ADR-069 canonizes the coherent local-first product surface that is intentionally shipped and supportable, without changing runtime behavior, the default supported profile, or the local-only provider posture. It does not by itself promote Coding Loop, Hosted Rooms, DeepSeek, or Browser Host to Beta. TTS / voice and federation remain Out of Beta. Anthropic / Claude account-export conversation import was canonized as Beta Bounded / Conditional on 2026-08-19 following its successful supported-runtime proof R2.

## What changed recently

- Accepted **ADR-069: Codexify Beta Runtime Support Boundary** on 2026-08-14 (Resonant Jones). The canonical Beta support boundary, the five human-facing release classes, the evidence-vs-support separation doctrine, the canonical authority hierarchy, and the first bounded canonical posture assertion corpus for present Beta support are now canonically defined. No runtime code change accompanies this acceptance.
- Accepted **ADR-072: Bounded Settings and Connections Route Promotion** on 2026-08-18 (Resonant Jones). The default local profile now admits authenticated identity/prompt settings routes and the read-only Connections catalog under separate route capabilities; generic connector mutation/sync routes remain quarantined. Fresh authenticated live proof is still required for runtime readiness claims.
- Activated the first canonical Product Architecture Beta posture assertion corpus at `docs/knowledge-graph/assertions/codexify-beta-support-posture.v1.json`, recorded against the audited repository revision `f4fece599e9e081154a7a7a96e1923f7f5c205b5`. ADR-057's historical acceptance record is preserved; ADR-069 activates a bounded posture corpus on top of the vocabulary ADR-057 already accepted.
- Added the bounded read-only `op::health_health_get` chat capability and advertised-subset authority gate; general tool use remains outside the release promise.
- Added DeepSeek native transport translation / continuation coverage and a cross-provider semantic convergence proof; both remain non-live provider evidence.
- Added Whoosh'd capability projection, structured transport, qualification / attestation seams, and exact-target identity reconciliation; the receipt covers one target / schema identity only.
- Canonicalized ADR-060 through ADR-063 and reverified DLG / knowledge-graph freshness after history corrections; these are control-plane / documentation changes.
- Added a Doctrine of Legible Responsibility and related tool-loop contract updates; they clarify boundaries without proving runtime readiness.
- Repaired the historical `d6f7a8b9c0d1` ThreadSpace migration lineage and the `b2c3d4e5f6a7` account-observability migration-content drift: `b2c3d4e5f6a7` was restored to its original applied body and a forward normalization migration (`9d4c2a7e1b6f`) converges clean, already-canonical, and backup-derived tester schemas onto one canonical ADR-049 shape at a single Alembic head. The preserved tester source remains unmodified and still requires a separate live upgrade / startup task; the canonical migrator psycopg driver compatibility is now landed and proven (see the 2026-08-13 driver-normalization proof); Hosted Room runtime proof remains pending; no release promise was widened.
- Landed canonical Alembic psycopg v3 driver normalization (`guardian/db/migrations/env.py`): driver-neutral `postgresql://` Alembic URLs now resolve to the installed psycopg v3 dialect before SQLAlchemy engine construction, for both the `DATABASE_URL` environment and the `alembic.ini` `sqlalchemy.url` source, while the process-wide `DATABASE_URL` contract is preserved for `seed_defaults.py` and runtime consumers; proven on a disposable Compose project with the canonical migrator and no ephemeral URL override (`docs/architecture/proofs/2026-08-13-alembic-psycopg3-driver-normalization-proof.md`). Migration graph unchanged at a single head `9d4c2a7e1b6f`; no release promise was widened.
- Canonized Anthropic / Claude account-export conversation import as **Beta Bounded / Conditional** under the existing ADR-069 doctrine (2026-08-19), following the successful supported-runtime proof R2: rendered Web UI → durable account-import job (`source_system="anthropic"`) → Redis → `worker-account-import` → Anthropic adapter → canonical Claude writer → PostgreSQL, with terminal job state `completed` and durable counters (63 threads / 784 messages) matching PostgreSQL readback exactly. The canonical continuity posture assertion advanced to `beta-continuity-v2` (v1 closed as a historical record). Anthropic Projects, `memories.json`, `users.json` persona/profile, binary media reconstruction, arbitrary export formats, and Anthropic inference remain excluded; the local-only provider contract is unchanged.

## Definition of Beta (ADR-069)

Codexify Beta is the **intentionally shipped and supportable local-first product envelope**, not a synonym for production-grade proof maturity. Bugs and incomplete polish are compatible with Beta. Unknown, unrestricted, or authority-ambiguous execution surfaces are not compatible with Beta. A Beta capability may carry `proven-test` or `proven-code-path` evidence where the architecture decision intentionally accepts that maturity for Beta, while authority-sensitive, destructive, remote-trust, or multi-user surfaces may remain qualification-pending regardless of how mature their implementation appears.

Evidence maturity, support posture, runtime participation, integration state, and strategic posture are orthogonal. A capability that is `proven-live-runtime` is not automatically `supported`, and a capability that is `supported` is not automatically `proven-live-runtime`. The five release classes below are human-facing release interpretations over those orthogonal Product Architecture Assertion dimensions plus explicit scope — they are **not** a replacement token domain.

## The five release classes (ADR-069)

The canonical human-facing release classification uses five classes. The corresponding canonical posture assertions live at `docs/knowledge-graph/assertions/codexify-beta-support-posture.v1.json`.

1. **Beta Supported** — intentionally shipped as part of the normal Codexify Beta experience and support promise.
2. **Beta Bounded / Conditional** — intentionally part of Beta, but only inside an explicit authority, topology, provider, mode, or capability boundary.
3. **Internal** — real operational substrate or operator / developer mechanism that may support Beta behavior but is not itself a public / user-facing release promise.
4. **Qualification Pending** — intended or plausible Beta surface with implementation present, but a specifically named proof / authority / operational gate remains open.
5. **Out of Beta** — explicitly excluded from the present Beta promise.

## Canonical Beta envelope (ADR-069)

### Beta Supported

**Local runtime and lifecycle**

- Local Docker Compose runtime.
- Local-only default provider posture (`CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`).
- Whoosh'd / local inference on the supported local profile.
- Core startup / migration lifecycle.
- Queue-backed chat completion lifecycle.
- Durable thread / message / task persistence.
- Supported health and runtime diagnostics.

**Digital Cognitive Workspace core**

- Ordinary chat.
- Threads and durable conversation history.
- Projects.
- Project / thread / workspace navigation.
- Documents and media ingestion on currently implemented supported formats.
- Embedding and private retrieval / RAG.
- Workspace-scoped retrieval.
- Obsidian / local workspace ingestion and retrieval.
- Bounded verified personal-facts / personalization behavior already used by ordinary chat.
- Core settings that configure currently supported runtime behavior.
- The read-only Connections catalog/control-plane is available through the
  existing core Settings Connectors bay on the supported local profile. This
  exposes catalog and safe state projection only; it does not expose generic
  connector execution or mutation.

**Identity and ownership**

- Codexify-native identity / authentication boundaries.
- Account-scoped ownership behavior already required by supported workspace surfaces.
- Migration / upgrade behavior already part of the supported local lifecycle.
- Operator-visible health / configuration truth required to run the self-hosted node.

**Operator experience**

- Dashboard / admin / health surfaces that truthfully expose supported runtime state.
- Model inventory / readiness surfaces.
- Queue / worker / runtime diagnostic visibility where the UI reflects real Guardian state.
- Unrestricted control-plane mutation is not promoted merely because diagnostic UI exists.

### Beta Bounded / Conditional

- **Persona Studio core** — profile creation / editing, persistence, selection, and application of supported persona / profile configuration to ordinary chat. TTS / voice execution, unsupported permission authoring, unsupported retrieval-policy execution, the claim that preview UI equals enforcement, and any future Studio feature without a current implementation seam are not in this promotion. Persona Studio being Beta does not implicitly make every control visible in Studio Beta-supported.
- **Import / continuity entry surfaces** — OpenAI / ChatGPT export import; Anthropic / Claude account-export conversation import (bounded to the proven conversation-import path); Task Prompt Archive; owner-scoped retry / recovery behavior; and account export / restore only to the exact extent supported by the existing contract and implementation.
- **Repository intelligence** — repository candidate discovery, explicit repository import, account / Project `RepositoryBinding`, direct Project-bound repository search, and ordinary-chat repository search exposure only when Guardian resolves exactly one valid active binding and existing authority checks pass (governed by ADR-065). The model must not gain authority from supplying Project ID, repository root, binding ID, account ID, cwd, mount path, credentials, or equivalent authority-bearing data.
- **Bounded Guardian tool execution** — allowlisted, Guardian-authorized bounded tool execution for explicitly supported capabilities (at minimum: read-only health capability; bounded Project repository search where current eligibility / authority checks pass). Preserves the advertised-subset authority gate, Guardian-owned execution authority, exact capability eligibility, bounded command count, continuation / persistence semantics, and provider capability checks. Does not promote arbitrary tools, arbitrary write operations, generic shell / filesystem execution, recursive multi-command agents, public Command Bus HTTP, or generic `/tools` or `/api/tools` exposure.
- **MCP / extensibility** — public MCP extension posture as a bounded extension interface. Does not claim that every MCP server is trusted, that every plugin is supported, that plugin SDK internals are public Beta API, that arbitrary plugin execution bypasses Guardian policy, or that a general plugin marketplace is released.
- **Desktop / Tauri client** — if current `main` still contains the functioning local desktop / Tauri presentation layer, classified as Beta Bounded / Conditional when used as a client of the same supported local Guardian node. Packaged production desktop distribution, auto-update support, an independent desktop persistence / runtime authority, and any separate release topology not currently proven are not claimed.
- **Identity, prompt, system-document, and Connections settings surfaces** — authenticated, local single-user settings routes and the read-only `/api/connections` catalog are Beta Bounded / Conditional. Connections catalog visibility does not imply provider implementation, setup, authorization, credential possession, or live health; generic `/api/connectors` mutation/sync behavior remains quarantined.

### Internal

- Direct Command Bus HTTP / control-plane API.
- Plugin SDK internals.
- Generic tools / API tools surfaces currently marked internal / quarantined.
- Developer-only diagnostics.
- Unsafe operator mutation surfaces.
- Implementation / control-plane mechanisms that support Beta behavior without being user-facing promises.

### Qualification Pending (with named remaining gates)

- **Coding Loop** — remaining gate: adapter execution plus terminal durable result plus source-thread readback on the claimed profile.
- **Hosted Rooms** — remaining gate: clean supported / tester startup plus owner / guest live semantic proof after migration repair.
- **DeepSeek / private-preview provider lane** — remaining gate: required credentials, authenticated provider-specific persisted runtime proof, and explicit supported-profile promotion.
- **Browser side-panel / Browser Host release surface** — remaining gate: whichever current host / auth / release proof remains open after reading current `main`.
- Any desktop packaging behavior not covered by the bounded local-client claim.

### Out of Beta

- TTS / voice execution.
- Federation.
- Unrestricted autonomous / recursive agent execution.
- Arbitrary write-capability tool use.
- Generic shell / filesystem execution through ordinary Beta chat.
- Public Command Bus exposure.
- Generic cron / unattended automation.
- Generic connector mutation/sync behavior without separate qualification. The read-only Connections catalog is separately bounded under ADR-071/ADR-072.
- Graph-write / Neo4j-derived-write behavior where the supported path remains flagged off or quarantined.
- Remote / multi-user repository execution not covered by a separately accepted authority contract and live proof.

TTS / voice and federation are intentionally **Out of Beta**, not qualification-pending.

## Current supported reality

- Local Docker Compose is the supported install path.
- The default supported Beta posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `LLM_PROVIDER=local`.
- `whooshd-mlx` is the supported Apple Silicon local runtime preset; other local presets require explicit configuration.
- Chat completion, upload → embed → readback, and workspace-local retrieval remain canonical supported Beta paths; the Beta envelope is not limited to these three.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` are the primary operator checks.
- OpenAI export import, Task Prompt Archive, and owner-scoped retry of failed zero-write import jobs are present and Beta Bounded / Conditional.
- Anthropic / Claude account-export conversation import is present and Beta Bounded / Conditional with a successful real supported-runtime proof: rendered Web UI → durable account-import job (`source_system="anthropic"`) → Redis → `worker-account-import` → Anthropic adapter → canonical Claude writer → PostgreSQL, with truthful terminal job accounting (`completed`; durable counters `imported_thread_count=63`, `imported_message_count=784` matched two independent PostgreSQL readbacks exactly; worker RestartCount=0; source export hashes unchanged). The proof also demonstrated the expected source-discovery / commit distinction — 65 source conversations discovered, 63 canonical threads committed — which is receipt evidence, not a product limit.
- Linked email aliases are resolved as a fallback to the existing user identity; the username path remains first.
- Bounded chat tool decisions pass through one advertised-subset authority gate. When `task.tools` is unset, ordinary chat may automatically expose exactly the read-only, zero-argument `op::health_health_get` (`GET /health`) capability to DeepSeek or to the exact Whoosh'd target when its current capability projection is eligible; explicit tool selections remain untouched, command visibility does not bypass execution authority, and this deterministic implementation does not widen release support.
- A committed live strict-structured qualification receipt exists for the exact `gemma-4-12b-it-qat-4bit` Whoosh'd target, but this is not general model or release support.
- Persona Studio core (profile create / edit / select / apply) is Beta Bounded / Conditional; TTS / voice remains Out of Beta.
- Repository intelligence (discovery, import, binding, search, ordinary-chat exposure) is Beta Bounded / Conditional under ADR-065; multi-user / Hosted-Room authority is not in this Beta.
- The Desktop / Tauri client, where present on `main`, is Beta Bounded / Conditional as a client of the supported local Guardian node; it is not packaged production distribution.
- The default local profile mounts authenticated Imprint, system-prompt, and system-document routes plus the read-only `/api/connections` catalog. `/health` publishes the effective mounted route inventory used by frontend capability gates; this is code/test evidence, not fresh live Compose proof.
- Coding Loop route registration, focused tests, worker readiness / guard evidence, and profile enablement are present; they do not prove a successful adapter turn or durable terminal result.
- Connections control plane surfaces MiniMax OAuth setup as `partial` (authentication/setup only); the MiniMax OAuth provider-specific mutation routes are mounted as `internal_only` under the supported local profile. OAuth-to-inference credential binding is deliberately deferred. The MiniMax API-key lane remains separate and unchanged.
- Architecture-contract, schema, DLG, and proof-validation tooling is present on `main`; it is not live-service proof.

## Not yet true / do not assume

- Do not assume TTS / voice execution is Beta-supported or qualification-pending. It is intentionally **Out of Beta**.
- Do not assume federation is Beta-supported or qualification-pending. It is intentionally **Out of Beta**.
- Do not assume cloud-provider Beta support, a packaged production desktop distribution, or a current local model without live endpoint and inventory proof.
- Do not assume the tester dual-provider lane is release-supported; it still needs authenticated, provider-specific persisted turns.
- Do not assume DeepSeek tool-turn tests or the Whoosh'd Gemma qualification establish supported-provider execution, general tool capability, or release support.
- Do not assume ADR / DLG canonicalization, freshness re-verification, or architecture contracts establish runtime support or release readiness.
- Do not assume a green health check, route acceptance, unit test, proof receipt, or docs contract proves end-to-end runtime readiness.
- Do not assume the linked-email migration alone proves upgrade success or authenticated end-to-end behavior on every existing database.
- Do not assume DLG / PAO documents or fixed ARPs provide corpus migration, arbitrary retrieval / RAG, database projection, assertion resolution, or agent authority.
- Do not assume Campaign Engine schemas provide scheduling, delegation, overnight execution, auto-merge, or auto-push.
- Do not assume the tool-unification plan provides implementation approval, terminal execution, or Coding Loop completion.
- Do not assume Browser Host, Chrome extension, Hosted Room, email, federation, graph writes, Continuity / Project Pulse, or P2P video are shipped Beta behavior.
- Do not assume Anthropic / Claude conversation-import support implies Anthropic Projects import, `memories.json` import, `users.json` profile/persona import, binary media reconstruction from metadata-only file references, support for every future or historical Anthropic export shape, or Anthropic API / Claude cloud inference / provider routing. "Anthropic" names the account-export source format, not a provider execution lane; local-only provider posture is unchanged.
- Do not assume tool-boundary tests or the Coding Loop proof packet establish provider execution, terminal persistence, or durable source-thread readback.
- Do not count local branches, unmerged work, draft plans, origin-only commits, or proof from another checkout as shipped reality.
- Do not assume that any present implementation seam, code path, or focused test by itself constitutes a Beta support claim. ADR-069's authority hierarchy requires canonical posture assertions plus supported-profile alignment plus `00-current-state.md` reconciliation for any release claim.
- Do not assume Connections catalog visibility means an adapter, configured credential, authorization, or healthy runtime; those remain distinct signals owned by their existing subsystems.

## Active blockers

- Fresh live Compose proof is still needed at `f4fece599`, including health, model inventory, terminal completion, persisted output, and retrieval.
- Queue-coupled chat still needs current-tip evidence for Redis, worker, turn-lock, and terminal-event behavior.
- Canonical and legacy configuration paths coexist, creating startup and operator-state drift risk.
- The bounded Coding Loop lane lacks current-tip proof of backend route acceptance, provider adapter execution, terminal result persistence, and durable source-thread readback; the prior proof stopped at backend exit code 3.
- Provider / tool-turn integration lacks current supported-profile proof for capability exposure, adapter execution, continuation, and durable completion; the exact Whoosh'd receipt does not close that gate.
- The private-preview lane lacks its required DeepSeek credential and authenticated session-token prerequisite.
- Hosted Rooms lack a clean supported / tester startup plus owner / guest live semantic proof after migration repair.

## This week's priorities

1. Capture fresh supported-Compose proof at `f4fece599`: health, model inventory, chat, persistence, and retrieval.
2. Verify queue completion, turn locking, migration behavior, and import recovery under the supported profile.
3. Reconcile or clearly fence canonical-versus-legacy configuration paths.
4. Re-prove provider / tool-turn and the enabled Coding Loop lanes end to end, or quarantine them until their required proof exists.
5. Keep DLG / PAO, Campaign Engine, Browser Host, Hosted Room, and provider-preview work outside release claims until their required proof exists.
6. Honor ADR-069's promotion / demotion discipline: every release-class move requires canonical posture assertion, supported-profile alignment, and `00-current-state.md` reconciliation.

## Release definition right now

- [x] The supported profile and local-only flags define the default Beta posture.
- [x] The canonical Beta envelope, the five release classes, and the evidence-vs-support doctrine are defined by ADR-069.
- [x] The first canonical Beta posture assertion corpus is recorded against the audited revision.
- [x] Whoosh'd local runtime and core chat / upload / retrieval paths are represented on `main`; the Beta envelope is not limited to these three.
- [x] TTS / voice and federation are explicitly Out of Beta.
- [x] Direct Command Bus remains internal-only.
- [x] Generic tools / API tools remain quarantined on the default supported profile.
- [x] Relevant architecture and schema validation is defined on `main`.
- [ ] Fresh live Compose evidence confirms terminal completion and persisted output at the audited tip.
- [ ] Queue, configuration, migration, and recovery behavior are green for the supported install path.
- [ ] Enabled Coding Loop routes have backend, authenticated adapter, terminal, and durable readback proof, or are quarantined.
- [ ] Any tool-enabled path has exact-target capability, authority, provider, continuation, terminal, and persistence proof on the supported profile.
- [ ] Any claimed preview or alternate surface has provider- or surface-specific runtime proof.
- [ ] Every release claim is merged to `main` and backed by evidence at the claimed proof level.
- [ ] A separate task promotes each qualification-pending surface with its named remaining gate.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence and invariants.
- `config-and-ops.md` explains operator / runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
- [ADR-069](./adr/069-codexify-beta-runtime-support-boundary.md) is the canonical Beta doctrine and the human-readable entry point for the five release classes.
- [`docs/knowledge-graph/assertions/codexify-beta-support-posture.v1.json`](../../knowledge-graph/assertions/codexify-beta-support-posture.v1.json) is the machine-readable canonical posture corpus; load it with `jsonschema` and `tests/architecture/test_beta_release_boundary.py` for the binding proof surface.
