# Prerequisite lineage reconciliation proof

## Result

`REWRITTEN_PREREQUISITE_LINEAGE_ACCEPTED`

Both task-specified historical prerequisites have independently verified,
patch-equivalent rewrites in current HEAD ancestry. Their matching subjects
were used only to discover candidates. File sets, stable patch IDs, raw patch
hashes, and the added proof-file blobs all match exactly.

This receipt canonizes a narrow evidence bridge; it neither changes Tester
authority nor proves a Whoosh'd repair, runtime inventory, inference, or
Watchdog activity.

## Current lineage and mandatory preflight

| Field | Value |
| --- | --- |
| Branch | `codex/diagnose-tester-fresh-chroma-failure` |
| HEAD at reconciliation | `94d268435fc9c3d9e4e657457785c5bfa760ddad` |
| Pre-existing unrelated worktree change | modified `guardian/workers/watchdog_review_worker.py`; preserved and unstaged |
| Common merge base of each old/new pair | `0ff80e332fa19edea85abc977275bd37fc8d409a` |

Both historical commits exist. Neither is an ancestor of the reconciliation
HEAD (`git merge-base --is-ancestor` exit status `1` for each), so neither is
silently retained as the prerequisite identity.

## Independent mapping 1: Tester authority reconciliation

| Evidence | Historical prerequisite | Current-lineage candidate |
| --- | --- | --- |
| SHA | `536c06c9e9297254c86b5974b1db4c0d327bc8ae` | `504c72f681350f37f98a7a41533a2c78b681c989` |
| Subject | `Reconcile tester model authority` | `Reconcile tester model authority` |
| Parent | `d64ad1db99476052c210d50afd166a017262d14a` | `3e732ced5de95940d2e858a63b293d23d62e4aec` |
| Candidate ancestor of HEAD | n/a | yes |
| Changed-file set | `A docs/architecture/proofs/runtime/2026-08-25-active-tester-model-authority-reconciliation-proof.md` | same |
| Stable patch ID | `5e063b7db20abf80145beda13e29a6a9772de5b9` | `5e063b7db20abf80145beda13e29a6a9772de5b9` |
| SHA-256 of raw binary patch | `d679d85e53e96f1d579cc4e7f3f0601b9bd09d23dc39b8ed5303bc91cb6b4877` | same |
| Added proof-file blob | `742ecf60a60edff05c69c496157a8f155a3b25e4` | same |

`git diff` of the proof file between the historical and candidate commits is
empty. There are no implementation or configuration files, semantic proof
differences, changed validation claims, or changed ADR interpretation to
classify.

**Classification:** `PATCH_EQUIVALENT_REWRITE`.

## Independent mapping 2: Whoosh'd Qwen identity investigation

| Evidence | Historical prerequisite | Current-lineage candidate |
| --- | --- | --- |
| SHA | `802f9baba0f22e38e13f37307b2769a10240119b` | `8e3af0191295704b59cba2c746fa8dc7bc098af8` |
| Subject | `Prove Whooshd Qwen identity repair` | `Prove Whooshd Qwen identity repair` |
| Parent | `536c06c9e9297254c86b5974b1db4c0d327bc8ae` | `504c72f681350f37f98a7a41533a2c78b681c989` |
| Candidate ancestor of HEAD | n/a | yes |
| Changed-file set | `A docs/architecture/proofs/runtime/2026-08-25-whooshd-qwen-runtime-identity-repair-proof.md` | same |
| Stable patch ID | `380145099486030b9c6366ca6f11bc890c1f8b9c` | `380145099486030b9c6366ca6f11bc890c1f8b9c` |
| SHA-256 of raw binary patch | `790d544767dac14c2aa1b1ca436d378ac791949ed79743cf328970acaf36f434` | same |
| Added proof-file blob | `17b353deee0757946637c50fb8e7627c0c35a11a` | same |

`git diff` of the proof file between the historical and candidate commits is
empty. The candidate therefore preserves the identical root-cause result,
model/authority observations, service and queue claims, validation posture,
ADR interpretation, and no-runtime-mutation boundary recorded by the
historical receipt.

**Classification:** `PATCH_EQUIVALENT_REWRITE`.

## Series and rewrite relationship

The explicit range comparison:

```text
git range-diff d64ad1db99476052c210d50afd166a017262d14a..802f9baba0f22e38e13f37307b2769a10240119b \
  3e732ced5de95940d2e858a63b293d23d62e4aec..8e3af0191295704b59cba2c746fa8dc7bc098af8
```

reported the one-to-one sequence:

```text
1: 536c06c9e = 1: 504c72f68 Reconcile tester model authority
2: 802f9baba = 2: 8e3af0191 Prove Whooshd Qwen identity repair
```

The commit SHAs differ because the candidate commits have different parent
objects and later committer timestamps, while author timestamps, raw patches,
and resulting proof blobs are identical. Git evidence proves the equivalent
reconstruction onto a different parent series; it does not identify whether
the operator used rebase, cherry-pick, or another history-rewrite mechanism.

## Canonical accepted prerequisite mapping

```text
802f9baba0f22e38e13f37307b2769a10240119b -> 8e3af0191295704b59cba2c746fa8dc7bc098af8
536c06c9e9297254c86b5974b1db4c0d327bc8ae -> 504c72f681350f37f98a7a41533a2c78b681c989
```

Later task specifications in this campaign may use the accepted
current-lineage SHAs above as equivalent prerequisites. Historical receipts
remain unmodified and continue to name the identities that existed when they
were produced.

## Boundaries and follow-through

No rebase, reset, cherry-pick, merge, branch switch, force push, or previous
proof edit occurred. This new proof artifact is the only tracked change in
this task.

No Whoosh'd registry or launchd mutation, Tester/backend/worker activity,
model inference, DeepSeek activity, Watchdog activity, GitHub runtime action,
or Postgres, Redis, or Chroma mutation occurred.

**No ADR impact — Git evidence lineage reconciled only.**

`docs/architecture/00-current-state.md` remains untouched. The next permitted
slice is the separately bounded canonical Whoosh'd Qwen registry restoration
using the two accepted current-lineage prerequisite SHAs; it must retain its
one-restart and zero-inference limits.
