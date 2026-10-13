# Native chat candidate adoption qualification — blocked pre-adoption

## Scope and authority

2026-10-07; Architecture-Impact / runtime qualification / PROOF_REQUIRED.
Human ownership assignment authorizes candidate-only qualification of
`codexify_candidate_28c95_20261005`, using the frozen reviewed handoff exactly.
It does not authorize reconstructing missing destructive commands, taking over
recovery source/process custody, or changing runtime semantics. Only this proof
artifact is writable in the repository. No ADR impact.

This is a prerequisite-blocked result, not a failed native chat experiment.
No candidate was adopted or qualified. Current-main supported-Compose
qualification remains separate; release remains **HOLD**.

## Exact blocking prerequisite

Frozen plan: `/private/tmp/codexify-chat-native-adoption-preflight-685cea098-20261007/handoff-plan.md`.
SHA-256: `5aaf194608fb9881fdae7dcac39b78075d5e2137e99166a1cc43ef15861c8911`.

The file exists, but is a seven-step narrative headed “pending ownership
assignment.” It contains no command-level Compose invocation, resolved config,
bounded-drain commands, quiescence checks, backup commands, pinned recreation
commands, or supported restart/qualification commands. Step 2 explicitly calls
for a separate bounded adoption Task Spec and privately rendered Compose.
Those executable inputs are absent from the designated recipe.

The plan also declares that backend and client share frozen revision
`685cea098a4a6c14e1bf3f679c94e0633dfe590a`. The required later client build proof
explicitly supersedes that client with
`c511f154bf70175672a6a9e78e854827482a4b73`, containing the final-read custody
repairs. That proof requires updated source/artifact pins before adoption.
The objective requires adoption of this refreshed client; following the older
client declaration would not qualify it. Backend tree equivalence permits the
older prepared backend image as a prerequisite, not the obsolete client pin.

The task's stop condition applies: material disagreement with the frozen plan
must yield BLOCKED rather than reconstruction of destructive commands. Runtime
custody was assigned, but an executable, current-pin reviewed recipe is still
required. No substitute plan or candidate was selected.

## Orientation and governing sources

Physical assigned checkout: `/Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main`; logical supplied path:
`/Users/chriscastillo/.codex/worktrees/7d94/Codexify-main`.
Branch: `codex/chat-postgres-terminal-deadline-20261003`.
Pre-task HEAD: `07157efff91d22f57f77b9c5d4f399bc383c8314`.

Axis Node README, invocation protocol, character directive, node contract and
knowledge source map were inspected. The source manifest is an unhydrated LFS
pointer, so its schema/content could not be verified. The connector recall
returned no selected workspace; no connector workspace was chosen. Filesystem
scope remained the supplied checkout. The default shell sandbox failed before
execution because its writable root contains a symlink; reviewed shell access
used the physical path without changing configuration or checkouts.

Current-state, ADR index, architecture README, agent protocol operations,
operator Goal, issue template contract, docs-to-issue compiler protocol,
constitutional heuristic and chat runtime/state/request contracts were inspected.
Governing boundaries include ADR-003/005 identity separation, ADR-038 durable
receipt versus transport/UI projection, and ADR-101 admitted Chroma custody.
This report changes none of those contracts. Postgres remains canonical;
observations and prior build/test artifacts are evidence only. The requested
capability is scoped adoption/proof under the explicit human assignment; the
only new durable repository state is this proof. Completion evidence for native
qualification is absent.

The four required prior proofs are absent from the assigned checkout. Read-only
worktree inventory located them in the separate candidate-source/recovery
checkout at HEAD `3c5d5538f8758f96dbc7d07f056af11a41da7ff6` on
`codex/chat-stop-diagnostic-mainline-20261005`:

- `/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main/docs/architecture/proofs/runtime/2026-10-07-final-transcript-read-promise-custody.md`
- `/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main/docs/architecture/proofs/runtime/2026-10-07-current-client-native-build-refresh.md`
- `/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main/docs/architecture/proofs/runtime/2026-10-07-current-client-controlled-browser-admission.md`
- `/Volumes/Dev_SSD/offload/codex/worktrees/chat-postgres-deadline/Codexify-main/docs/architecture/proofs/runtime/2026-10-07-goal-completion-gap-audit.md`

That checkout was only read, not selected, reset, staged, committed or changed.
Its four dirty files are the recovery-owned files listed below. This proof is
committed in the supplied checkout, not silently transplanted into that Goal.
Prior tests/build/synthetic-browser results remain bounded prior evidence.

## Pre-adoption Git inventory

Exact supplied-checkout status before the proof:

```text
## codex/chat-postgres-terminal-deadline-20261003
 M docs/architecture/00-current-state.md
 M docs/architecture/adr/retired/053-threadspace-whispermesh-managed-service-boundary.md
 M docs/architecture/proofs/supported-compose/2026-10-05-chat-failed-stop-durable-recovery.md
 M docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json
 M docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json
 M frontend/src/features/workspace/__tests__/WorkspaceScratchpadPanel.test.tsx
 M frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx
 M guardian/routes/memory_vault.py
 M tests/ops/test_pi_assistant_response_telemetry.py
 M tests/routes/test_memory_vault.py
```

Exact separate recovery-checkout status:

```text
## codex/chat-stop-diagnostic-mainline-20261005...origin/main [ahead 83]
 M guardian/tests/migration/test_chatgpt_ingest.py
 M guardian/workers/chat_embedding_worker.py
 M tests/workers/test_chat_embedding_canonical_handoff.py
 M tests/workers/test_chat_embedding_worker_import_replay.py
```

Both indexes were empty. All ten unrelated modified files in the supplied
checkout were fingerprinted and preserved. Recovery HEAD, status, worktree diff,
index diff and four content hashes were separately captured.

## Candidate runtime inventory and pins

Observed at `2026-10-07T15:27:34.478031+00:00`. Compose project labels confirm
`codexify_candidate_28c95_20261005`. These are running-container identity
observations, not readiness or successful execution proof.

| Service | Container ID prefix | Configured image |
| --- | --- | --- |
| worker-chat | `42f5f9a660d5` | `codexify-backend-runtime:goal-integrated-a165a3447` |
| worker-document-embed | `9e468f5c35c7` | `codexify-backend-runtime:goal-integrated-a165a3447` |
| frontend | `8b25fa82b031` | `sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293` |
| backend | `60d99ff5416b` | `codexify-backend-runtime:goal-integrated-a165a3447` |
| db | `8d7e69dee694` | `postgres:15` |
| redis | `93c3a036abad` | `redis:7-alpine` |
| neo4j | `897d8610221e` | `neo4j:5` |

Backend/chat/document image ID is
`sha256:910b5acd39be578be8da6fd5c773314bccc4a3bdc516226210fb53ecc746e341`;
its revision label is `a165a34475a20c3a1aad95c41b3d69c041d9b14e`.
Prepared backend image/tag still exists:
`codexify-backend-runtime:goal-current-685cea098`, ID and RepoDigest suffix
`sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6`,
revision label `685cea098a4a6c14e1bf3f679c94e0633dfe590a`.
The image was inspected, not adopted or independently requalified internally.

Frontend base image is
`sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293`.
Its running source bind remains the prior receipt-candidate-adoption frontend;
this image ID alone does not attest to the served client source/bundle revision.
Frontend port is 5173; full candidate port/mount/container/start-time details are
in scratch `baseline.json`. Labels identify Compose files:

```text
/private/tmp/codexify-mainline-proof-28c95/source/docker-compose.yml
/private/tmp/codexify-mainline-proof-28c95/source/docker-compose.whooshd-smoke.yml
/private/tmp/codexify-mainline-proof-28c95/candidate.override.yml
/private/tmp/codexify-mainline-proof-28c95/receipt-candidate-adoption/integrated.override.json
```

Actual active profile/environment fidelity was not established by rendering
config. No inferred profile or environment equivalence is asserted.

Attached named/anonymous volumes:

- `0382900c2a77f08fd477da25b89fa9e2d7c9efb4cf19e39d18e24a716b20da65`
- `25830adbcea5a2a5636e75b9bd4db4d8f74f0979ae86c36ca5d17e093c5f4b1f`
- `5fc24591f254f73d3c44a0a1e0c7b00c577c6bd3113466e4bb1247747c470fb7`
- `codexify_candidate_28c95_20261005_codexify_cli_home`
- `codexify_candidate_28c95_20261005_corepack_cache`
- `codexify_candidate_28c95_20261005_frontend_pnpm_store`
- `codexify_candidate_28c95_20261005_hf_cache`
- `codexify_candidate_28c95_20261005_neo4j_data`
- `codexify_candidate_28c95_20261005_pg_data`
- `codexify_default_local_chroma`
- `f91157e84c1d3e5d54402fd70f845fe20a675c57b4e99ded61ae1c3d58cea2a5`

`codexify_default_local_chroma` retains admission ID
`ef0c3312bdb640e4a35e2783ecfcd687`, contract ADR-101 and candidate project label.
All-container inspection found only candidate backend, worker-chat and
worker-document-embed mounting it, each read-write at `/app/.chroma`.
No additional Docker-container mounter was found. This does not prove idle
writers or exclude every possible non-container writer. No quiescence claim.

## Prepared refreshed client artifacts

Existing build scratch:
`/private/tmp/codexify-chat-client-build-c511f154b-20261007/`.
Its attestation declares revision
`c511f154bf70175672a6a9e78e854827482a4b73`, 716 input files and 16 output files.
All 16 output bytes and SHA-256 values were freshly checked against
`artifacts.json`; all match, totaling 11,088,871 bytes. This verifies retained
artifacts only; no client rebuild, serving adoption or browser action occurred.

| Prepared artifact | SHA-256 | Bytes |
| --- | --- | --- |
| `index.html` | `90a16438003948bb9f7928f077e941fe51120a840ee267d966539827d4747683` | 544 |
| `workbox-43e0ad88.js` | `b267a25675a59ca7faa27582fad84702467fd4af962058e0638108a0a02a68db` | 138184 |
| `vite.svg` | `fff702862e14c3ce019b81d86e07a0734764cac22ca5dbbe8542d4a682e482b2` | 1498 |
| `registerSW.js` | `9742073ef7fc795e7673d98f272992843298426a0ffd8cb3507784df5143608b` | 134 |
| `manifest.webmanifest` | `6d1d68893648a15e64ad7a023a9ea5fc017f51fdb6494dda1a57d45aeac11d1c` | 358 |
| `sw.js` | `751b0216ca56ae37ddeac8dea5eb8ac229f124b727010d9417636a937d210e3e` | 3638 |
| `peekaboo-demo/field-notes-map.png` | `02894e62ce44e88e7ad475690c7dd8fbac16a9e2605be18369485a6591ebe33f` | 3536825 |
| `peekaboo-demo/abstract-signal-study.png` | `5a5ccebba9c97ec39b0e6e5986a22dc638f3f0c8629b8a162598d7f10fb8e725` | 2154785 |
| `peekaboo-demo/interface-moodboard.png` | `691cf5f9d3b36b82d8a59aa88f95a4a61845caa4199670effc8df16c7b5d4375` | 2668203 |
| `assets/index-Bj801Zkd.js` | `98d720fcc72db54383e1fd48ba98108254539eb46db9d8cd8cdeb81f44e33943` | 1863691 |
| `assets/Rusty-Butthole-QBBVr4o3.png` | `b29b84041da90ff6ac5e15bc270b507e5c779e7222b629caf64866f1bc844bb8` | 422016 |
| `assets/index-DuhC_-pX.css` | `997ee0fd66fe7d2076af80d9b81876a4a5938cef635afd05985a035a211ab8e5` | 160721 |
| `assets/ui-tune-DHN1in1h.css` | `20aafb3313a8d90be78b8ce5992e02c34fd9a9e3f0aa440704f70cd21533b9b0` | 1595 |
| `assets/UITunePad-iMTWbvZu.js` | `bda625b961972912a7fbc2432644f1197b4252f780ef424d2cb3e45be8d31418` | 5530 |
| `assets/github-D8EXDMGG.svg` | `af0ac154b70b9dfe6881dcda75ab648ffcd259160258c8a9af8008e822872952` | 128658 |
| `assets/core-D9ZGnyhG.js` | `33fd62a0aff0467268e8e5139068de60e66b5f14ef972ab376b98a4932a38421` | 2491 |

`verification.json` SHA-256:
`40ca1d543573d1b5927129142986a8befffdefb335e2bb38547a0a50661cd403`.
Its recorded backend tree equality is inherited attestation, not a fresh
in-container source-fidelity proof in this task.

## Quiescence, backups and commands actually executed

No consumers were drained/stopped; no runtime or data service was recreated.
No PostgreSQL/Chroma backup was taken: the required command-level backup recipe
was absent and writers remained live. No historical Chroma bytes were imported,
no backups/volumes deleted, and no model substitution occurred. Existing backup
contents were neither inventoried nor asserted to be qualified.

Read-only inventory commands actually executed from the assigned repo root:

```sh
git status --short --branch --untracked-files=all
git rev-parse HEAD
cat /private/tmp/codexify-chat-native-adoption-preflight-685cea098-20261007/handoff-plan.md
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
docker volume inspect codexify_default_local_chroma
git worktree list --porcelain
git log -8 --format='%h %s'
```

Additional reads: mandatory contracts, the four prior proof files, build artifact
and verification JSON, `docker inspect` for all discovered containers,
`docker image inspect` for the two backend tags/prepared digest and Node image,
read-only separate-worktree status/diff/HEAD, SHA-256 snapshots, and a bounded
host process inventory. Private filtered scratch retains outputs without
container environment/credentials or message bodies.

**Adoption/recreation/restart commands executed: none.**
No `compose up/down`, migrator, prune, worker signal, task submission, recovery
replay or queue/lock/data mutation was executed. Database migration revision,
canonical thread/message/attempt counts and Redis queue/TTL state were not
refreshed in this task; the preflight observations do not replace those gates.

## Native qualification gate dispositions

| Gate | Disposition and evidence boundary |
| --- | --- |
| Candidate fidelity/adoption | BLOCKED before adoption: recipe has no exact executable commands and stale client revision; running older candidate inventoried only. |
| Ordinary chat success | NOT RUN. No new thread, authored turn, attempt/request, task, assistant row or terminal correlation ID created. |
| Real browser/transcript/final-read coherence | NOT RUN. Prior synthetic rejected-admission browser proof does not qualify native success or final-read custody. |
| Canonical durable readback | NOT RUN. No new assistant/browser row comparison; Postgres remains canonical without a new durability claim. |
| Bounded failure/recovery | NOT RUN. No injected fault, cancellation, retry, ghost-response or composer-release proof on the adopted candidate. |
| Derived chat embedding | BLOCKED / NOT RUN. Candidate service inventory has no worker-chat-embed. Plan requires a separate exact canonical-service addition with DB/queue/vector/startup/drain proof, but supplies no executable step. Recovery WIP was not used. No derived-state correctness claim. |
| Supported restart/recreation continuity | NOT RUN. No reviewed restart procedure supplied; no services stopped or recreated and no row/queue/lock continuity test. |
| Ordinary chat after restart | NOT RUN. No restart and no post-restart authored/assistant turn or durable readback. |

No native product defect is established. FAIL — REPAIR REQUIRED would overstate
this evidence; there is no source repair authorized or begun. The strongest
remaining prerequisite is a reviewed executable adoption/qualification recipe
that pins the refreshed client and defines exact preservation, consumer addition
and restart commands for this candidate. This report does not generate or
approve that next task.

## Preservation and final invariant check

Recovery-owned file SHA-256 baseline (each rechecked unchanged before document
creation):

| Recovery-owned file | SHA-256 |
| --- | --- |
| `guardian/tests/migration/test_chatgpt_ingest.py` | `d904f467edb65211c40cb19e5d350af59938c10db8fbdd465b72383c3bf0eb1f` |
| `guardian/workers/chat_embedding_worker.py` | `c159df0aa8a7eef57d6f74104930e65c549f51feb454752b8f11bd77a319004b` |
| `tests/workers/test_chat_embedding_canonical_handoff.py` | `f7782be3da76b813e0713132c97af3ce83761985ea8ee2ccdac23e55b1ef4b13` |
| `tests/workers/test_chat_embedding_worker_import_replay.py` | `d1579a86d93dc97209609235fd4b1ef31c358bb2f7d1b51cc3d1233307e8c627` |

The bounded host scan found no matching pytest/vitest process mentioning the
recovery test file families. No known recovery PID was supplied; survival of a
specific pre-existing process is therefore not proven. This task did not launch,
signal, terminate or restart any recovery test process or message its chat.
No runtime process was signalled. Separate recovery HEAD, worktree diff, index
and four file bytes were rechecked unchanged. Supplied-checkout unrelated dirty
file bytes and index were also rechecked unchanged. Candidate container IDs,
images, start times, restart counts and mounts matched the baseline at the
pre-document recheck. Full preservation receipts are in owned scratch.

Postgres authority, identity distinctions, immutable deadline/retry semantics,
model selection, original volumes and historical stores were left untouched.
No stale-read or assistant-completion guarantee is claimed without native proof.
No source/application/test file was modified by this task; only this proof was
created. No merge, push, deployment, broad release-doc update or release claim
expansion. Current-state and other unrelated dirty files remain outside scope.

## Repository validation and documentation follow-through

Required proof diff check and scoped Git status are performed before commit:

```sh
git diff --check -- docs/architecture/proofs/runtime/2026-10-07-native-candidate-adoption-qualification.md
git status --short --branch --untracked-files=all
git add docs/architecture/proofs/runtime/2026-10-07-native-candidate-adoption-qualification.md
git commit -m "docs: record native chat candidate qualification"
```

Staged proof whitespace is also checked, because a new untracked file is not
included by an unstaged diff check. The commit must include only this file;
exact commit hash and final preservation-check results are reported in closeout.
No automated runtime tests apply to this prerequisite-blocked docs-only result.
Required native runtime commands were unavailable and **not run**, not passed.
Earlier missing-file reads failed in this checkout; read-only location in the
separate checkout resolved evidence access without transplanting source.

Documentation follow-through is this artifact only. Current-main support/release
truth, source repairs and runtime qualification remain explicitly deferred.
Scratch evidence: `/private/tmp/codexify-native-qualification-blocked-20261007-01a116f7/`.

## Final verdict

**BLOCKED** — designated frozen handoff lacks executable reviewed adoption,
preservation and qualification commands and pins the superseded client.
Candidate remains unadopted by this task; native gates remain unproven.
Release remains **HOLD**.
