# Backend static boundary reconciliation — 2026-09-22

## Result

**Bounded result: PASS. The F7 backend-static portion is CLOSED.**

The governing backend release-boundary suite now tests each invariant against
the authority that owns it. ADR-069 remains the durable source for the
five-class Beta doctrine and named product classifications;
`00-current-state.md` remains the concise operational truth layer; and the
supported-profile startup fixture now constructs the canonical local-only
profile without ambient cloud credentials or a historical physical-model
selection.

The frontend lifecycle-test OOM/hang behavior remains open. Overall F7 is
therefore `PARTIALLY CLOSED`, and the supported-Compose result remains `HOLD`.

## Environment

| Field | Evidence |
| --- | --- |
| Date | 2026-09-22 |
| Repository | `/Volumes/Dev_SSD/Codexify-main` |
| Branch / base commit | `main`; `9c6b14fca047203c14daf3fe4032baf630d5b4dc` |
| Upstream / divergence | `origin/main`; ahead 7, behind 0 |
| Initial worktree | One unrelated staged deletion: `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; no unstaged or untracked paths |
| Workflow | Architecture-impact static release-governance reconciliation |

The staged Dev Log deletion was not restored, unstaged, modified, or included
in this task.

## Historical baseline

The 2026-09-21 supported-Compose rerun recorded the recovered governing backend
suite at:

```text
151 passed / 5 failed / 8 warnings
```

The five historical failures were:

1. `test_current_state_contains_the_five_release_classes`
2. `test_current_state_places_tts_voice_outside_beta`
3. `test_current_state_places_federation_outside_beta`
4. `test_current_state_names_coding_loop_and_hosted_rooms_qualification_pending`
5. `test_supported_profile_health_loads_during_startup`, at
   `release_hold is False`

Historical observations were not treated as current truth. Both affected test
files were rerun unchanged at the base commit before mutation.

## Current-tip reproduction

The architecture test collected 31 tests and reproduced all four historical
current-state failures: `27 passed / 4 failed`.

The startup test collected five tests and reproduced the release-hold failure:
`4 passed / 1 failed / 8 warnings`.

The startup state was inspected without printing credential values:

```text
profile valid: true
profile mismatches: []
cloud-capable configuration present: true
release hold: true
ambient cloud credential present: DeepSeek only
fixture local model: mlx-community/gemma-4-e2b-it-4bit
```

The health implementation was behaving correctly: explicit cloud credential
presence must keep the local-only profile on release hold. The test fixture,
not runtime health, was stale.

## Failure classification and authority map

| Invariant | Historical test source | Canonical authority now | Classification |
| --- | --- | --- | --- |
| Five release classes | `00-current-state.md` headings | ADR-069 `Release Classes` doctrine | `STALE TEST AUTHORITY` |
| TTS / voice Out of Beta | `00-current-state.md` proximity match | ADR-069 `Out of Beta`; supported-profile voice quarantine corroborates exposure | `STALE TEST AUTHORITY` |
| Federation Out of Beta | `00-current-state.md` proximity match | ADR-069 `Out of Beta`; supported-profile federation quarantine corroborates exposure | `STALE TEST AUTHORITY` |
| Coding Loop / Hosted Rooms Qualification Pending | `00-current-state.md` section layout | ADR-069 `Qualification-Pending Doctrine`, including a named open gate for each | `STALE TEST AUTHORITY` |
| Supported-profile release hold | startup fixture | supported-profile manifest plus runtime health/posture contract | `STALE FIXTURE` |

No `REAL CONTRACT FAILURE` or `CANONICAL SOURCE CONTRADICTION` was found.
ADR-069, the posture corpus, the Product Architecture ontology, the supported
profile, and current operational truth remain compatible within their stated
authority scopes.

## Repair

### Release-boundary assertions

`tests/architecture/test_beta_release_boundary.py` now:

- reads the five release classes from ADR-069's bounded `Release Classes`
  section rather than requiring the short-form current-state document to
  repeat the taxonomy;
- proves TTS/voice and federation remain explicit bullets in ADR-069's
  `Out of Beta` section;
- proves Coding Loop and Hosted Rooms remain in ADR-069's
  `Qualification-Pending Doctrine`, each with its own named open gate; and
- keeps meaningful `00-current-state.md` coverage by checking its own
  operational responsibilities: local-first Beta hardening, current `HOLD`,
  the named local Docker Compose profile, and a distinguishable active blocker
  section.

The assertions remain semantic and section-bounded. They do not compare an
entire Markdown document or require incidental short-form layout.

### Supported-profile startup fixture

`tests/core/test_supported_profile_startup.py` now:

- snapshots, clears, and restores `DEEPSEEK_API_KEY` with the other cloud
  credentials used by the isolated fixture;
- explicitly clears the cached settings field so repository `.env` loading
  cannot contaminate the supported local-only case; and
- uses the canonical logical model route `local-chat` rather than the old
  physical Whoosh'd model string.

The test still asserts `release_hold is False`. It was not weakened to accept a
hold. The neighboring provider-drift test remains intact and proves an invalid
provider fails closed with a startup error.

No architecture authority, runtime source, supported-profile YAML, Compose
file, environment file, health logic, provider behavior, or release claim was
changed.

## Validation

### Directly affected files

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -v tests/architecture/test_beta_release_boundary.py` | PASS: 32 passed |
| `.venv/bin/python -m pytest -v tests/core/test_supported_profile_startup.py` | PASS: 5 passed, 8 warnings |
| `.venv/bin/ruff check tests/architecture/test_beta_release_boundary.py tests/core/test_supported_profile_startup.py --output-format concise` | PASS |

The eight startup warnings are the existing FastAPI/Pydantic/deprecation
warning surface; they were not introduced as release-boundary failures.

### Recovered governing backend F7 suite

The exact ten-file command recovered from the 2026-09-21 proof ledger was:

```text
.venv/bin/python -m pytest -p no:cacheprovider -v tests/architecture/test_beta_release_boundary.py tests/core/test_supported_profile.py tests/core/test_supported_profile_auth_coherence.py tests/core/test_supported_profile_provider.py tests/core/test_supported_profile_quarantine.py tests/core/test_supported_profile_startup.py tests/audit/test_collect_canonical_live_proof_receipt.py tests/ops/test_source_compose_supported_profile_contract.py tests/proofs/test_supported_profile_live_proof_contract.py tests/proofs/test_workspace_obsidian_e2e_contract.py
```

Result:

```text
157 passed / 0 failed / 8 warnings
```

The total is one test higher than the historical 156-test collection because
the repaired architecture file adds explicit semantic coverage for the
short-form current-state authority.

## Invariants

- Static proof remains distinct from live runtime proof.
- ADR-069 still defines the five release classes and accepted classifications.
- The posture corpus remains the structured temporal posture authority and was
  not modified.
- `00-current-state.md` remains the short-horizon operational/release truth
  layer and was not expanded into an exhaustive taxonomy.
- TTS/voice and federation remain Out of Beta and quarantined by the supported
  profile.
- Coding Loop and Hosted Rooms remain Qualification Pending with named gates.
- DeepSeek remains outside the default public Beta profile; ambient DeepSeek
  configuration now causes no false positive in the isolated local-only
  fixture.
- The canonical supported-profile test still requires `release_hold=false`,
  while actual provider drift remains fail-closed.
- No runtime/configuration behavior or release claim changed.

## F7 disposition

| Surface | Disposition | Evidence |
| --- | --- | --- |
| Backend release-boundary static assertions | **CLOSED** | All five historical failures were classified and repaired; recovered governing suite is 157/157. |
| Frontend Guardian lifecycle-test reliability | **PERSISTS — unchanged** | `GuardianChat.lifecycle-timing` OOM and `GuardianChat.turn-lock-lifecycle` hang were not run or modified in this task. |
| Overall F7 | **PARTIALLY CLOSED** | Backend half is green; frontend lifecycle reliability remains open. |

F4 remains `CLOSED — unchanged`. F5 remains `CLOSED — unchanged`. Overall
supported-Compose remains `HOLD`.

## ADR impact and documentation follow-through

**ADR impact: aligned with existing ADR-069. No ADR change.**

This artifact records static proof only. `docs/architecture/00-current-state.md`
was deliberately not modified. Its later release-truth reconciliation remains a
separate authorized task; this repair does not silently rewrite current release
claims.

The next single prerequisite is to reconcile the two Guardian frontend
lifecycle test files so they execute deterministically without OOM/hang while
preserving their lifecycle assertions. This task does not begin that work.
