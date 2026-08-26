# Whoosh'd Qwen registry restoration proof

## Result

`BLOCKED: CODEXIFY_PREREQUISITE_ANCESTRY_MISSING`

The required Codexify source-preflight commits exist as objects, but neither
is an ancestor of the active task checkout. The packet requires their exact
ancestry before the registry restoration, a Whoosh'd restart, or Guardian
runtime qualification. The current branch instead has rewritten commits with
the same subjects. That is not evidence of the required commit ancestry.

No Whoosh'd commit or service restart was performed. This receipt records a
blocked preflight only; it does not prove a canonical Qwen runtime inventory,
Guardian recovery, inference, or Watchdog readiness.

## Codexify preflight

| Check | Result |
| --- | --- |
| Task checkout | `codex/diagnose-tester-fresh-chroma-failure` |
| Task HEAD | `8e3af0191295704b59cba2c746fa8dc7bc098af8` |
| `git cat-file -e 802f9baba0f22e38e13f37307b2769a10240119b^{commit}` | pass |
| `git merge-base --is-ancestor 802f9baba0f22e38e13f37307b2769a10240119b HEAD` | fail |
| `git cat-file -e 536c06c9e9297254c86b5974b1db4c0d327bc8ae^{commit}` | pass |
| `git merge-base --is-ancestor 536c06c9e9297254c86b5974b1db4c0d327bc8ae HEAD` | fail |

The current HEAD log contains `8e3af0191 Prove Whooshd Qwen identity repair`
and `504c72f68 Reconcile tester model authority`, but the mandatory checks
above use the exact task-specified commits. No semantic-equivalence exception
is defined by the packet.

The Codexify worktree also had a pre-existing unrelated unstaged change in
`guardian/workers/watchdog_review_worker.py`. It was preserved and is outside
this proof's edit boundary.

## Authoritative registry discovery

The active Whoosh'd checkout was independently identified as:

| Field | Value |
| --- | --- |
| Root | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| Remote | `https://github.com/Resonant-Jones/whooshd.git` |
| Branch | `main` |
| HEAD | `da216d76a0a3ea5c8930f1a0cf722151af526e31` |
| Dirty state at closeout | clean; branch is 22 commits behind `origin/main` |

The active plist is syntactically valid and still names:

```text
/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml
```

It also identifies the selected local artifact as:

```text
/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit
```

Before this task, the expected registry was absent. Git-native history found
the exact canonical source at
`81fe385b44f124ce528902964e049d815da34979:configs/models.friends-family-guest.yaml`:

| Source evidence | Value |
| --- | --- |
| Source commit | `81fe385b44f124ce528902964e049d815da34979` |
| Source blob | `dc70602d29c174560e012943f32b67b14b69d12a` |
| SHA-256 | `93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817` |
| Exact mapping | `qwen3.8-27b-4bit` -> `mlx_vlm` -> `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit` |

The candidate is in the active repository's own history, although its commit
is not an ancestor of the active Whoosh'd HEAD. This is an allowed source
class in the packet. The current registry parser successfully loaded the
historical blob: it has one exact canonical ID, engine `mlx_vlm`, format
`mlx`, and an existing resolved artifact directory. No other current registry
defines that canonical ID.

## Containment and stop decision

An exact temporary worktree copy was byte-compared with the historical blob
and parser-validated while completing source discovery. It had the source
blob SHA and SHA-256 above. Once the explicit Codexify ancestry failure was
confirmed, that uncommitted copy was removed before any Whoosh'd commit or
service action. At closeout the active target is absent again and the
Whoosh'd worktree is clean.

`WHOOSHD_REGISTRY_RESTORE_RESTARTS=0`.

No launchd plist, Whoosh'd source, model artifact, Tester configuration,
Guardian matching policy, provider routing, DeepSeek configuration, Watchdog
configuration, Postgres, Redis, or Chroma state was changed. No backend,
`worker-chat`, Redis, or MLX sidecar restart was attempted.

The pre-repair Whoosh'd inventory remains the only observed inventory for this
task:

1. `mlx-community/Llama-3.2-3B-Instruct-4bit`
2. `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`

It does not establish the exact configured Qwen ID. Guardian health/catalog
surfaces were not refreshed after a registry change because no registry change
was allowed to remain active. No backend inventory-refresh decision applies.

`MODEL_INVOCATIONS_DURING_REGISTRY_RESTORE=0`.
`DEEPSEEK_REQUESTS_DURING_REGISTRY_RESTORE=0`.
`WATCHDOG_ATTEMPTS_DISPATCHES_RESULTS_DURING_REGISTRY_RESTORE=0`.

No chat task, GitHub I/O, Command Bus, Build Loop, manual Postgres mutation,
manual Redis mutation, or Chroma mutation occurred.

## ADR impact and next proof

**Aligned with ADR-074; no ADR change.**

The exact active checkout must first be moved onto a lineage containing the
two packet-specified prerequisite commits, or the task packet must explicitly
authorize replacement commit identities. Only then may a new bounded task
restore the proven blob, perform the single permitted Whoosh'd reload, and
qualify exact inventory and Guardian health. No authenticated Qwen completion
or Watchdog work may begin from this receipt.
