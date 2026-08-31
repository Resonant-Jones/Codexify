# Hosted E2B Provider Read-Only Input Qualification

## Exact qualification conclusion

`E2B_PROVIDER_READ_ONLY_INPUT_UNSUPPORTED`

This conclusion is scoped to the hosted E2B Cloud API and the pinned E2B
Python SDK `2.46.0` inspected and exercised on 2026-08-31. The qualification
does not claim that E2B can never add this capability. It records that the
tested hosted surface exposes no supported provider-enforced read-only input
mechanism that can satisfy ADR-077.

The smallest blocker is the absence of a provider-controlled read-only access
mode. The hosted sandbox volume-mount request contains only a volume identity
and guest path. The current account's live attempt to create the persistent
volume candidate returned `403: use of volumes is not enabled`, and the
official hosted volume contract describes mounted files as writable. A fresh
live ordinary-files sandbox then demonstrated the consequence directly: the
execution principal could mutate the materialized workspace. Guest-denied
`chown` and remount commands do not establish read-only enforcement.

No production `SandboxProvider` adapter, Guardian integration, Pi integration,
worker privilege change, or ADR change is included.

## Scope and evidence posture

This proof is follow-through for the read-only blocker in
[ADR-077](../../adr/077-sandbox-execution-authority-and-provider-boundary.md)
and references the prior
[hosted E2B read/exec conformance proof](./2026-08-31-e2b-read-exec-provider-conformance-proof.md).
The prior result remains:
`E2B_READ_EXEC_PARTIALLY_CONFORMANT`.

| Evidence label | Meaning |
| --- | --- |
| `LIVE-RUNTIME` | Observation returned by a real E2B Cloud control-plane call or sandbox allocation during this proof. |
| `SDK-SURFACE` | Inspection of the installed pinned SDK and generated request models. It is not, by itself, provider behavior proof. |
| `DOC` | Current official E2B hosted documentation or official SDK source. It is capability evidence only. |
| `INFERENCE` | A bounded interpretation of the evidence; it is not an observed provider guarantee. |
| `UNPROVEN` | Not established by this qualification. |

The probe used synthetic fixture content only. The credential was sourced from
the ignored local `.env.tester` into `E2B_API_KEY`; its value was never printed,
stored in the artifact, passed to sandbox environment variables, or included in
telemetry. The probe itself is
[`scripts/e2b_read_only_input_qualification_probe.py`](../../../../scripts/e2b_read_only_input_qualification_probe.py).

## Revision, dependency, and hosted-service truth

| Property | Value |
| --- | --- |
| Branch | `main` |
| Upstream | `origin/main` |
| Pre-task HEAD | `930a8ad32582422fd079a509f3a88a362a71e876` |
| Pre-task worktree | Clean; `origin/main...HEAD` was `0 4` |
| E2B Python SDK | `2.46.0` |
| Dependency pin | [`requirements/e2b-conformance.txt`](../../../../requirements/e2b-conformance.txt) |
| Hosted service | E2B Cloud, default control plane |
| Account constraint | Persistent volume use returned `403: use of volumes is not enabled` |
| Service tier | Not exposed by the inspected API |
| Region | Not exposed by the inspected allocation |
| Live sandbox allocations | One fresh ordinary-files sandbox |
| Volume allocations | Zero; volume creation was rejected before allocation |
| Approximate provider usage | One sandbox requested for 90 seconds; it was explicitly destroyed after approximately 5.4 seconds. Billing totals were not exposed. |

The probe used a process-local E2B SDK `pyqwest`
`SyncHTTPTransport(use_system_dns=True)` for control-plane and sandbox
transport only. This was required because the host's default resolver added a
local Tailscale search suffix to `api.e2b.app`. It did not change sandbox
network policy and is not production code.

## Current hosted E2B capability inspection

The following official materials were inspected for the tested generation:

- [E2B volume overview](https://docs.e2b.dev/volumes) (`DOC`): persistent volumes are mounted storage and the hosted contract describes files as readable and writable.
- [E2B volume mounting](https://docs.e2b.dev/volumes/mount) (`DOC`): `volume_mounts` maps a guest path to a volume or volume name; no access-mode option is documented.
- [E2B volume read/write API](https://docs.e2b.dev/volumes/read-write) (`DOC`): the volume surface includes write, directory creation, and removal operations.
- [E2B sandbox create API](https://docs.e2b.dev/api-reference/sandboxes/create-sandbox) (`DOC`): `volumeMounts` items contain `name` and `path`; no `readOnly` field is shown.
- [E2B persistence](https://docs.e2b.dev/sandbox/persistence) and [snapshots](https://docs.e2b.dev/sandbox/snapshots) (`DOC`): these preserve sandbox state, not a provider-enforced immutable input layer.
- [E2B cloud buckets](https://docs.e2b.dev/storage/cloud-buckets) (`DOC`): bucket mounts use guest FUSE commands and credentials, so they are not a provider-enforced read-only input primitive for this posture.
- [E2B Python SDK package metadata](https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/pyproject.toml) (`DOC`): source for the maintained Python package version inspected.

The installed `2.46.0` SDK inspection produced this contract evidence:

| Surface | Observed shape | Evidence |
| --- | --- | --- |
| `Sandbox.create` | Has `volume_mounts`; no `read_only` or `readonly` parameter | `SDK-SURFACE` |
| Generated `SandboxVolumeMount` model | `name`, `path`, and generic `additional_properties` only | `SDK-SURFACE` |
| Generated `NewSandbox` request | `volume_mounts` serializes each mount as `name` and `path`; no read-only field | `SDK-SURFACE` |
| Volume content API | Read/write/list/remove operations; no mount access-mode control | `SDK-SURFACE` + `DOC` |

No undocumented `readOnly`, `readonly`, mount flag, immutable layer, or
provider-side input projection was invented or sent.

### Candidate mechanism table

| Candidate mechanism | Hosted service | Maintained SDK | Classification | Qualification finding |
| --- | --- | --- | --- | --- |
| Ordinary sandbox filesystem materialization | Available | Available | Not applicable | An ordinary guest path is writable by the execution principal; live negative-control test below. |
| Persistent volume mount | Available in the public surface; current account rejected creation with `403` | Available | Not applicable to read-only posture | Mount identity and path are exposed without access mode; official docs describe mounted content as writable. |
| Template or base image | Available | Available | Not applicable | Establishes starting image state, not an attached immutable task-input path. |
| Snapshot or pause/resume | Available | Available | Not applicable | Preserves mutable filesystem state; no immutable mount/access mode was exposed. |
| Cloud bucket guest FUSE mount | Documented | Not an input-mount primitive | Not applicable | Requires guest commands/FUSE and credentials; enforcement is not below guest authority. |
| Custom/self-hosted storage enforcement | Not hosted E2B Cloud | Not qualified | Self-hosted only | Out of this hosted qualification scope; no self-hosted capability is promoted into hosted proof. |

No legitimate hosted provider-native read-only candidate was exposed by the
tested API generation. The persistent-volume creation call was still made as
a bounded live check because it was the closest named hosted storage
candidate; its account rejection is recorded rather than silently treated as
proof of a read-only behavior.

## Live qualification run

### Allocation and provenance

The fresh live allocation was:

| Property | Observation |
| --- | --- |
| Sandbox ID | `itwbaujr58mxkw2ggzomv` |
| Template ID | `rki5dems9wqfm4r03t7g` (`base`) |
| Started | `2026-08-31T15:53:06.660166Z` |
| Provider state at inspection | `running` |
| Runtime | `envd_version=0.6.10`, Linux runtime, `x86_64` from the provider's base template family |
| Resource class | `cpu_count=2`, `memory_mb=512` |
| Network request | `allow_internet_access=false` |
| Volume mounts | `[]` |
| Execution identity | Synthetic one-principal/task metadata; command ran as the sandbox's default `user` principal |
| Control-plane observation | `get_info()` succeeded after guest probes while the sandbox remained live |

The current account's persistent-volume attempt occurred at
`2026-08-31T15:53:06.198524Z` and returned `VolumeException` with bounded
message `403: use of volumes is not enabled`. No volume was created and no
volume credential or token was recorded.

### Synthetic input and read proof

The ordinary-files negative-control workspace was materialized through the
E2B Files API at `/tmp/adr077-input-1bbff17aba`. The protected-workspace label
is intentional: this was the path tested as if it were protected, but it was
not a provider-enforced read-only path.

The required input files were readable, enumerated, and hash-matched:

| Relative path | SHA-256 | Read result |
| --- | --- | --- |
| `root.txt` | `24fd8bb6993f118b255584c49f878a906e5ebf494650ba128e8b10de50b676c6` | PASS |
| `nested/marker.txt` | `ab8ef65335b16b510de6ee226872d9068976d1abde2579325037353fc0482598` | PASS |
| `nested/checksum.bin` | `7cbc58761a2449acfd0d921adca99984d34625492ad678165efc1d85bf54d082` | PASS |

Directory enumeration and command-side `sha256sum` both returned exit code
`0`. The host repository path `/Volumes/Dev_SSD/Codexify-main` was absent
inside the sandbox. The source fixture was synthetic and its in-memory
SHA-256 map was identical before and after the allocation:
`integrity_preserved=true`.

### Protected-workspace mutation matrix

Because no provider-native read-only candidate was exposed, the live ordinary
filesystem run is a negative control. For this surface, a successful mutation
is the failure evidence: it proves the execution principal has write authority
over the supposedly protected path. `chown` and remount were denied by guest
authority, not by a provider read-only mount, and therefore cannot turn the
surface into a PASS.

| Required attack | Live ordinary-materialization result | Enforcement classification |
| --- | --- | --- |
| Overwrite existing protected file | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Append to existing protected file | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Create new file | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Create new directory | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Delete protected file | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Rename protected file | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Rename protected directory | FAIL: exit `0`; mutation succeeded | Guest-writable filesystem |
| Change file permissions | FAIL: exit `0`; mutation succeeded | Guest discretionary permission control |
| Change directory permissions | FAIL: exit `0`; mutation succeeded | Guest discretionary permission control |
| Change ownership where available | Attempt denied: exit `1`, `Operation not permitted` | Guest/kernel authorization; not provider RO |
| Restore write permission after permission removal | FAIL: exit `0`; `chmod` reversal and modification succeeded | Guest-reversible permission state |
| Replace via temporary file plus rename | FAIL: exit `0`; replacement succeeded | Guest-writable filesystem |
| Create symlink | FAIL: exit `0`; link creation succeeded | Guest-writable filesystem |
| Create hardlink and modify through link | FAIL: exit `0`; link and mutation succeeded | Guest-writable filesystem |
| Remount/remap writable attempt | Attempt denied: exit `32`, `must be superuser to use mount` | Guest authority; not provider RO |

This matrix directly rejects `chmod` as an enforcement layer. The execution
principal could restore write permission and modify the input. It also rejects
discarded writes, prompt/tool restrictions, and a disposable writable copy as
equivalents of ADR-077 read-only input.

### Authorized scratch

The same allocation used a separate scratch path
`/tmp/adr077-scratch-3990154724`. Creation, modification, deletion, and
directory removal completed with exit code `0`. This proves the negative
control was not a globally unusable filesystem and preserves the required
distinction between protected workspace and authorized scratch.

### Environment and credential posture

The probe inspected environment key names only; it did not inspect or emit
values. The observed names were:

```text
E2B_CONFORMANCE_SAFE E2B_EVENTS_ADDRESS E2B_SANDBOX E2B_SANDBOX_ID
E2B_TEMPLATE_ID HOME LOGNAME PATH PS1 PWD SHELL SHLVL USER _
```

`E2B_API_KEY`, Codexify database credentials, model/provider credentials, and
known service credential names were absent. Only the test-safe variable
`E2B_CONFORMANCE_SAFE` was intentionally supplied. Result: credential
non-disclosure `PASS` for the inspected names and minimal environment
`PASS`, with no claim about values that were deliberately not inspected.

### Control-plane separation and teardown

The sandbox was created with `allow_internet_access=false`. While the guest
probes were complete, the E2B control plane successfully returned `get_info()`
for the still-running sandbox. This is a `PASS` for control-plane observation
separation in this probe: the operator credential and SDK transport remained
outside sandbox command visibility. It is not a read-only workspace result.

Explicit teardown then called `sandbox.kill()`, which returned `true`, and
`sandbox.is_running(request_timeout=5)` returned `false`. Result:
`PASS`, teardown confirmed. The persistent-volume path had no teardown because
the volume allocation was rejected before creation.

No lifecycle reconnect test was run: no volume, snapshot, or reconnectable
read-only candidate existed in the tested account/API surface. This is
`UNPROVEN` for a hypothetical future provider feature, not evidence that such
a feature exists.

## ADR-077 conformance matrix

| ADR-077 requirement | Result | Evidence | Mandatory gate |
| --- | --- | --- | --- |
| provider-native read-only input mechanism | FAIL | `SDK-SURFACE`: no access-mode field; `DOC`: mounted volume content is writable; `LIVE-RUNTIME`: volume candidate rejected by account and ordinary path was writable | yes |
| protected workspace readable | PASS for negative-control path | `LIVE-RUNTIME`: required files read and hashes matched | yes |
| actual read-only workspace | FAIL / unsupported | No supported hosted access mode; mutation matrix shows guest authority | yes |
| writable scratch separated | PASS | `LIVE-RUNTIME`: scratch create/modify/delete succeeded | immediate support |
| provider enforcement below guest authority | FAIL | `LIVE-RUNTIME`: ordinary path mutations succeeded; guest permission state was reversible | yes |
| source fixture integrity | PASS | `LIVE-RUNTIME`: synthetic source hash map unchanged before/after | defense-in-depth |
| provider control transport remains observable | PASS | `LIVE-RUNTIME`: `get_info()` succeeded after guest probes | yes |
| volume candidate live qualification | UNPROVEN as runtime behavior | `LIVE-RUNTIME`: current account returned `403: use of volumes is not enabled`; no volume was allocated | supporting |
| lifecycle persistence of read-only protection | UNPROVEN | No read-only candidate existed to reconnect | supporting |
| provider/version provenance | PASS | `LIVE-RUNTIME` sandbox ID/template/envd/resource metadata plus `SDK-SURFACE` version `2.46.0` | yes |
| overall provider read-only input qualification | `E2B_PROVIDER_READ_ONLY_INPUT_UNSUPPORTED` | No hosted provider-enforced posture was exposed or proven | yes |

## Effect on the prior provider result

The prior
`E2B_READ_EXEC_PARTIALLY_CONFORMANT` result remains unchanged. This proof
does not promote E2B to `E2B_READ_EXEC_CONFORMANT` and does not close the prior
provider qualification gaps for storage ceiling semantics or tenant/workspace
separation.

The read-only blocker is now more precisely scoped:

`E2B Cloud API/SDK 2.46.0 exposes persistent-volume identity/path mounting but no provider-enforced read-only access mode; current account volume entitlement is also unavailable.`

The account-level `403` is a warning/constraint, not a claim that persistent
volumes cannot exist in every E2B team. The unsupported qualification follows
from the absence of a read-only access mode in the tested hosted API/SDK and
the official read/write semantics, with the fresh live ordinary sandbox
providing direct negative-control evidence.

## Warnings, failures, and limitations

Warnings:

- Persistent volumes are private-beta/account-gated for this credential; a
  volume runtime could not be allocated.
- E2B did not expose service tier, region, or a tenant identifier in the
  inspected response.
- The live ordinary-files attack matrix is a negative control, not proof of a
  provider-native candidate.
- No hypothetical future E2B access mode was tested because none was exposed
  by the pinned public surface.

Failures:

- `READ_ONLY_WORKSPACE_UNSUPPORTED` remains a mandatory failure for the
  immediate ADR-077 posture.
- Ordinary materialization allowed principal mutations, including permission
  reversal and file replacement.

Unproven assumptions:

- E2B may add a future hosted read-only input feature; this proof says nothing
  about an unexposed or unreleased API.
- Cross-tenant and service-tier separation remain outside this focused proof.
- Resource ceilings and descendant lifecycle semantics remain governed by the
  prior conformance proof and are not requalified here.

## Recommended next Task Spec boundary

Do not build an E2B adapter that represents an ordinary writable copy as
read-only. The next prerequisite should evaluate another hosted Sandbox
Provider whose public, account-available contract exposes a provider- or
kernel-level read-only input attachment with a separate writable scratch path.
If no such provider is available, open a separate architecture decision about
whether Codexify should own that enforcement boundary; do not make that
decision implicitly by discarding sandbox writes at teardown.

The smallest valid follow-up is therefore a provider-comparison/evaluation
proof, not Guardian or Pi integration.

## Validation and repository scope

Commands run for this proof:

- `git status --short --branch --untracked-files=all` — PASS before editing;
  `main...origin/main [ahead 4]`, clean.
- Safe environment check for `.env` and `.env.tester` — PASS; both contained a
  non-empty `E2B_API_KEY` without printing its value.
- Pinned SDK inspection — PASS; installed `e2b` version `2.46.0`.
- Live focused probe with `.env.tester` — PASS as an executed probe; exact
  qualification `E2B_PROVIDER_READ_ONLY_INPUT_UNSUPPORTED`.
- `python3 -m py_compile scripts/e2b_read_only_input_qualification_probe.py` —
  PASS.
- `python3 scripts/validate_docs.py` — run after this artifact is added.
- `git diff --check` — run after this artifact is added.
- Secret-value scan — run on changed and staged files before commit; no key
  value may appear.

Only the focused probe and this dated proof artifact are authorized changes.
No production execution surface or accepted ADR was modified.

## Axis KB addition

Record this qualification as a provider-boundary fact: hosted E2B Cloud Python
SDK `2.46.0` exposes volume mount identity/path but no provider-enforced
read-only access mode; the current team returned `403` for volume creation;
ordinary materialization is guest-writable and permission-reversible; the
correct next boundary is another provider comparison or an explicit future
Codexify-owned enforcement decision. Do not treat this proof as whole-provider
conformance or as authorization to implement an adapter.
