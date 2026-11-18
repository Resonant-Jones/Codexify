# Lens and curated voice: bounded mainline continuation

2026-11-18, existing launch Task Spec, continuation VOICE-FUND-02. This is the
same work packet as the preserved local Lens/voice campaign, not a new campaign.
The full prior local history remains at0180a67087c5349ed202b4d1d6eae239609b4c4d;
that branch includes unmerged Lens/continuous/Inspector/UI work and is not the
candidate for wholesale merge or deployment.

## Exact scope and authority

Chris requested finalizing Deepgram for Private Preview. Execution is authorized
for isolated implementation, disposable/mocked proof and a bounded draft PR after
local validation. Root reviews readiness before any merge/deployment. No live
provider/account call, spend, recording, credential/configuration change, tester
access widening or Beta promotion is authorized during verification.

Base main145e8cbf11c11566e4fbf16944df3d50cb0c06ce, verified2026-11-18. Isolated
worktree `/tmp/codexify-deepgram-preview-finalize-20261118`. Current serving source
reportsbf36fa2426c10c795ed64911bab996b0251b7fd5 plus tracked modifications, with
separate account-profile/UI/image changes. No serving source is edited here.
Do not deploy this branch as a parallel Preview. A later deployment must use a
verified main revision and preserve separately owned profile/import behavior.

This slice ports only the inactive typed voice spending core from the checkpoint,
repairs its migration-test dependency and re-parents its additive migration to
actual main heade723ba9046cd. It does not import the held Lens migrationf834cb0157de,
continuous runtime, client changes, other owner patches or old Preview source.
The continuous candidate is preserved for later coordinated integration; batch
STT/TTS is not a substitute for that requested interaction loop. No client work or
native build is needed for this inactive server slice; Scout-first preference is
preserved for the eventual client stage.

Canonical User/thread/project/message state owns content access. Existing fixed
operator-owned monthly/provider window rows own capacity. Internal quote/payer/
credential descriptors are trusted service inputs, not newly verified grants.
Only content-free reservation/claim/usage records become durable in disposable
tests. Completion is exact parent/diff, real PostgreSQL concurrency/custody and
migration/recovery proof, unchanged production gates, plus PR/CI evidence. Source
proof does not establish provider privacy, billing, actual audio or release readiness.

Governing ADR-003/005/087/091/092/110 and
[inactive budget foundation](../../Plans/2026-11-14-inference-budget-foundation.md)
remain unchanged. [Voice budget contract](../../architecture/voice-budget-admission-contract.md)
describes this inactive internal seam. No production policy issuer, account grant,
credential custody or quarantine exception is selected by this increment.

## Requirements and acceptance

- Exact service and explicit sponsor/account-owned payer descriptors; reject
  cross-account owner or scope mismatch, no silent sponsor/provider fallback.
- Share actual aggregate/provider window locks and counters with chat, including
  in-flight/unknown holds. One committed exact dispatch claim, replay refusal,
  unclaimed-only release and original-quote trusted settlement/overrun accounting.
- Current same-account success, foreign/deleted/changed resource refusal, immutable
  normalized assistant content/settings/quote, expiry and cancellation/failure
  liability. No audio/key/header/prompt content in records; no account-deletion FK.
- Additive migration from actual main head, no budget seeds. Old-budget migration
  proof uses its own empty schema instead of dropping parent tables beneath new
  dependents. Prove full upgrade, new-only downgrade/re-upgrade and backup/restore
  of synthetic held liability without permitting another claim.
- Keep provider adapters, runtime authorization, profile posture, worker/queue and
  clients unchanged. The core is not production admission or verified BYOK.
- Validate with synthetic data, owned Unix-only PostgreSQL and outbound denial.
  Proposed10 minutes/tester/day remains unapproved/unimplemented; no quota seeded.

## Live gates retained

Main currently lacks the continuous/Lens candidate. Actual serving source and
loaded process/image/schema/configuration differ from main and must be reviewed
with their owners; moving source mounts is not a rollout. Future root-reviewed
maintenance must retain exact rollback refs, backups, effective overrides, auth/
allowlist and existing profile behavior, and serialized worker/proxy health proof.

Fresh read-only live schema isf3a9c7d2b8e1, from the separate profile chain
ab71d5ce9604 -> d2e7a9b4c1f6 -> f3a9c7d2b8e1. None of those profile additions is
included by this main-based slice. Main's source graph remains142/e723ba9046cd;
this candidate is143/1b6c8d9e2f40. Do not run this migration graph directly against
the live database or downgrade its profile revision. Root and the profile owner
must reconcile that chain on main before a matched rollout.

The wholesale preserved-checkpoint/main merge rehearsal has14 conflicts, including
newer import recovery/API/token/test surfaces and current-state documentation.
It was not applied. Existing owner import work is retained on main and excluded
from this slice. Earlier source-composition proofs do not qualify the new union.

Before any paid permit: accept exact payer/credential ownership, policy issuer/
revoker, account/operation scope, fixed confirmed funding and buffer, receipt/
retention authority, downstream model costs and daily reset rules. Real BYOK
lookup/purpose custody is not supplied by the coding-only execution vault.

Verify applicable account/project/model opt-out support and price inclusion or
surcharge, billing minima/rounding/start-stop/close liability, and no-unpaid-overage
protection. Historical project-list200/detail403 is not entitlement proof. Deepgram
[Terms5.5](https://deepgram.com/terms) retain overage liability despite insufficient
credits and delayed balances. No key/credit/card assumption or app timer alone
meets Chris's strict requirement. Keep mandatory opt-out, transient microphone
processing, no stored caller recording/training, six selected voice families where
supported, no Think-Fast/substitution and generated-audio cache OFF.

Verification has zero provider-request/spend allowance. Earlier$1/two30-second
session/one short Speak canary is planning only, not approved funding or a proven
hard cap. No provider call or exposure change is made to resolve these unknowns.

## Validation and closeout

From the isolated root, exact network-denied native PostgreSQL runner and proof
logs are in `/tmp/codexify-deepgram-preview-finalize-evidence-20261118/`.

```sh
sh /tmp/codexify-deepgram-preview-finalize-evidence-20261118/run_validation.sh
python scripts/validate_docs.py
git diff --check
```

Stage only the inactive core/models/tokens, additive migration, focused metering
tests and these task/contract docs. Commit locally, then push only this bounded
branch and create a draft PR if validation and scope review permit. No merge,
deployment, runtime change or paid canary without root readiness review. Report
exact head/base/files/commands/results/CI, remaining gates and whether this inactive
slice is useful; no working-live-voice claim.

Local receipt:390 passed with one existing SQLAlchemy relationship warning;
zero unexpected socket/DNS attempts under OS denial. New voice-budget cases ran
against owned PostgreSQL. Full143-revision upgrade, new-only downgrade/re-upgrade
and synthetic pg_dump/restore all passed; restored liabilities kept both holds
and refused replay/release. Temporary PostgreSQL stopped. Scoped Ruff/Black,
documentation and diff checks pass. No frontend/native test applies because no
client changed. CI results must be read from the eventual exact draft head.

## Root-reviewed runtime/rollback plan

This PR can be useful as inactive shared accounting only. It neither installs
continuous voice nor implements an account funding resolver. Do not merge/deploy
it as a complete Deepgram launch. Root must first resolve held dependencies,
main/live schema divergence and independently owned profile/import preservation.

Before maintenance, capture exact source/image/effective config and a verified
data-safe backup/restore checkpoint, reserve quiet work and drain accepted jobs.
Deploy only a reviewed main revision, serially, with voice flags OFF and Deepgram
key still unloaded. Read back matching migrator/source/loaded worker versions,
unchanged account access, profile/import/text behavior and no unintended egress.
Health and internal diagnostics must use their existing auth, never a new public
probe or tester-access exemption. Native nginx syntax, exact WebSocket/callback
route/header/timeout behavior and cancellation need their own proof.

If disabled smoke fails, restore the exact prior runtime source/image/config with
operator-approved scope. Do not automatically downgrade the live schema or drop
held liabilities/profile data. A schema recovery is a separate reviewed restore
operation. Later key/flag/funding activation and a bounded synthetic protocol/
browser/audible canary require root confirmation of privacy, no-overage and all
paid entry-point admission. No live success, no-overage or Beta promotion follows
from the local synthetic receipt.
