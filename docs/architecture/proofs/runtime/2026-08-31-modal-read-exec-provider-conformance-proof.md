# Hosted Modal Read/Exec Provider Conformance Proof

## Qualification conclusion

`MODAL_READ_EXEC_PARTIALLY_CONFORMANT`

This is a live hosted-provider result for the ADR-077 immediate read/exec
posture using Modal Python SDK `1.5.5` and the stable Sandbox API. Modal
provided a provider-enforced read-only Volume mount, separate writable
scratch, foreground execution, deny-all command networking with preserved
control-plane access, minimal environment construction, credential
non-disclosure, hard CPU and memory ceilings, timeout, bounded output,
whole-sandbox descendant teardown, and confirmed cleanup.

Full conformance is withheld because the stable `Sandbox.create` surface has
no storage/disk ceiling parameter. The live filesystem reported an effectively
unbounded root view, so storage is `UNPROVEN`, not silently inferred from
measurement or provider billing. ADR-077 requires a bounded storage posture.

No Modal adapter, Pi integration, Guardian integration, worker privilege
change, ordinary-chat route, or release claim is authorized by this result.

## Scope and evidence posture

This proof qualifies one hosted Sandbox Provider candidate against
[ADR-077](../../adr/077-sandbox-execution-authority-and-provider-boundary.md).
It does not amend ADR-077, ADR-020, ADR-068, or the Pi Invocation Boundary.

| Label | Meaning |
| --- | --- |
| `LIVE-RUNTIME` | Observation returned by a real hosted Modal allocation during this proof. |
| `SDK-SURFACE` | Inspection of the pinned installed SDK/API surface; not provider behavior by itself. |
| `DOC` | Current official Modal documentation; capability evidence only. |
| `UNPROVEN` | The proof did not establish the assertion and does not infer it. |

Only synthetic fixture content and synthetic lineage identifiers entered
Modal. Authentication came from the local `jones` Modal profile. Credential
values were not printed, copied into repository files, or injected into any
Sandbox. No Modal `Secret` was supplied.

## Revision, dependency, and runtime identity

| Property | Value |
| --- | --- |
| Branch | `main` |
| Upstream posture before execution | Local/upstream divergence `5/5`; zero overlapping changed paths in the required overlap inspection |
| Pre-task HEAD | `9baa904a2ea4bd431ad582d63eeb64b0bf08279e` |
| Pre-task worktree | Clean |
| Canonical proof window | `2026-08-31T18:03:27.378948Z` to `2026-08-31T18:04:04.464456Z` |
| Modal Python SDK | `1.5.5` |
| Pin | [`requirements/modal-conformance.txt`](../../../../requirements/modal-conformance.txt) |
| Sandbox API generation | Stable Sandbox API; Modal V2/experimental Sandbox was not enabled |
| Provider | Modal hosted service |
| Canonical allocation cloud/region | `CLOUD_PROVIDER_AZURE`, `eastus` |
| Canonical image | `im-GYYHaMJMKETlbgCvh62lOr` |
| Command runtime | Linux `4.19.0-gvisor`, `x86_64`, UID `0`, user `root` |
| Account scope | One local Modal profile/workspace and the `main` environment; cross-account isolation not tested |

The final normalized receipt was kept ephemeral at `/tmp` and was not
committed. Its SHA-256 was
`975325db338ede7f29fad7f013b4228d11a42b978649a66e5551bfa1cbcd7e36`.

The canonical run used four allocations:

| Role | Sandbox ID | Purpose |
| --- | --- | --- |
| primary read/exec | `sb-6LGAydy3NIdqpOr3uC1a5n` | workspace, scratch, process, network, environment, resources, output, descendant |
| metadata reconnect | `sb-EqzXiu5KXYGEK7vS7JryA2` | fresh-mount verification after mutation attacks |
| lifecycle timeout | `sb-OPfBmaVT9TdrZJp06koiCx` | provider wall-clock timeout |
| memory limit | `sb-6Q65FfYmmxN80XaBdbaonM` | bounded normal/over-limit memory behavior |

Probe development required three earlier calibration executions and one
single-allocation provenance check. Total hosted allocations for the task were
15: 14 across four bounded probe runs plus one provenance allocation. The
final exact script used four. Approximate aggregate sandbox lifetime was a few
allocation-minutes; Modal billing totals were not exposed. All task-tagged
Sandboxes were absent from `Sandbox.list` after completion.

The final run landed on Azure `eastus`; the separate provenance check landed
on OCI `eu-frankfurt-1` because no region was pinned. This proves provider
scheduling variability, not a residency guarantee. A production adapter must
make region/residency policy explicit rather than infer it from one run.

## Stable API surface

The probe used these stable Modal 1.5.5 surfaces:

- `Sandbox.create` with `block_network=True`, hard CPU/memory tuples, a
  wall-clock timeout, an explicit environment allowlist, no Secrets, and a
  Volume mount;
- `Volume.with_mount_options(read_only=True)` at `/workspace`;
- `Sandbox.exec` for bounded foreground commands;
- `Sandbox.list` and `poll` for control-plane observation;
- `Sandbox.terminate(wait=True)` for whole-allocation teardown; and
- an ephemeral proof-only Volume populated from the trusted control plane.

Official Modal documentation describes read-only Volume mounts as preventing
container writes, `block_network=True` as blocking outbound connections, and
CPU/memory `(request, limit)` tuples as hard limits:

- [Modal Volumes and read-only mounts](https://modal.com/docs/guide/volumes)
- [Modal Sandbox networking](https://modal.com/docs/guide/sandbox-networking)
- [Modal Sandbox SDK reference](https://modal.com/docs/sdk/py/latest/Sandbox)
- [Modal Sandbox lifecycle](https://modal.com/docs/guide/sandboxes)

Those documents selected the candidate APIs. The result below comes from live
execution.

## Synthetic workspace and read proof

The trusted probe populated one proof-only Volume with a root file, nested
directory/file, binary checksum fixture, and distinct attack targets. The
Volume was mounted at `/workspace` using exactly:

```text
Volume.with_mount_options(read_only=True)
```

The Sandbox enumerated and read the protected input. Command-side SHA-256
results matched the trusted source hashes:

| Relative path | SHA-256 | Result |
| --- | --- | --- |
| `root.txt` | `a8f55fa9e8f07f0bb86bc70fcec9d8ded16cf681903e8e481c653c78ef100c44` | PASS |
| `nested/marker.txt` | `3d2ded22aa82be2496f5aed19f39e7502bb378ea678b87261b358783ea92d86c` | PASS |
| `nested/checksum.bin` | `630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd` | PASS |

The host path `/Volumes/Dev_SSD/Codexify-main` was absent inside the
allocation. This is bounded isolation evidence, not a universal escape proof.

## Protected-workspace mutation matrix

| Attack | Live result | Observed enforcement/effect |
| --- | --- | --- |
| overwrite existing file | PASS: denied, exit `1` | `Read-only file system` |
| append existing file | PASS: denied, exit `1` | `Read-only file system` |
| create file | PASS: denied, exit `1` | `Read-only file system` |
| create directory | PASS: denied, exit `1` | `Read-only file system` |
| delete file | PASS: denied, exit `1` | `Read-only file system` |
| rename file | PASS: denied, exit `1` | `Read-only file system` |
| rename directory | PASS: denied, exit `1` | `Read-only file system` |
| `chmod` file | PASS by observed effect | command returned `0`; mode remained `0644` before/after/fresh mount |
| `chmod` directory | PASS by observed effect | command returned `0`; mode remained `0755` before/after/fresh mount |
| `chown 1234:1234` | PASS by observed effect | command returned `0`; UID/GID remained `0:0` before/after/fresh mount |
| remove and restore write permissions, then modify | PASS: content write denied, exit `1` | guest could not convert the mount to writable |
| temporary file plus rename replacement | PASS: denied, exit `1` | temporary file creation denied |
| create symlink inside workspace | PASS: denied, exit `1` | `Read-only file system` |
| write through scratch symlink into workspace | PASS: denied, exit `1` | target remained read-only |
| hardlink then modify | PASS: denied, exit `1` | link creation denied |
| remount writable | PASS: denied, exit `32` | mount permission denied |

The zero-return `chmod`/`chown` results were not treated as mutations because
the probe compared the actual metadata before and after each attack family,
then created a fresh Sandbox mount. Mode, UID, and GID were identical in all
three observations. Content and namespace hashes also remained unchanged.

Classification: provider/container Volume enforcement below prompt/tool
policy. The guest could not reverse the posture. This is stronger than guest
`chmod`, discarded writes, or a writable disposable copy.

## Writable scratch and foreground process execution

The same primary Sandbox created, modified, renamed, and deleted a file under
`/tmp/codexify-scratch`; exit was `0`. A separate foreground shell command
returned the expected marker with exit `0`. The protected Volume was
specifically read-only rather than the whole container being unusable.

## Command network and control-plane separation

The Sandbox was created with `block_network=True`. No guest firewall command
was used.

| Probe | Live result |
| --- | --- |
| DNS resolution of `example.com` | PASS: `gaierror` |
| hostname HTTPS request to `example.com` | PASS: `URLError` |
| direct TCP connection to `1.1.1.1:443` | PASS: `OSError` |
| `Sandbox.poll()` during those restrictions | PASS: `None` / still running |
| filtered `Sandbox.list(tags=...)` | PASS: returned the primary sandbox ID |
| explicit termination after restricted commands | PASS |

Command data-plane egress was denied while Modal control-plane traffic
remained usable from the trusted caller. This preserves ADR-077's separation
between provider control transport and untrusted command networking.

## Environment and credential isolation

The probe supplied exactly one synthetic value and no Modal `Secret`. It
inspected Sandbox environment key names only, apart from three explicitly
allowlisted non-secret provenance values (`MODAL_CLOUD_PROVIDER`,
`MODAL_REGION`, and `MODAL_IMAGE_ID`).

Observed names were runtime/image configuration keys such as `HOME`, `PATH`,
Python/image configuration, thread-count controls, Modal allocation IDs, the
cloud/region/image provenance keys, and `CODEXIFY_MODAL_PROBE_SAFE`.

Absent names included:

- `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`;
- E2B credentials;
- OpenAI, Anthropic, and Minimax credentials;
- database, Postgres, Redis, GitHub, AWS, and Google credential names.

Result: minimal explicit environment `PASS`; credential non-disclosure
`PASS`. Values of parent credentials and unrelated environment variables were
not inspected or forwarded.

## CPU, memory, and storage posture

| Dimension | Requested posture | Live observation | Classification |
| --- | --- | --- | --- |
| CPU | request `0.125`, hard limit `0.25` physical cores | cgroup v1 quota/period `250000/1000000` = `0.25` | `HARD_CEILING_PROVEN` |
| Memory (primary) | request `256 MiB`, hard limit `384 MiB` | cgroup v1 `memory.limit_in_bytes=402653184` | `HARD_CEILING_PROVEN` |
| Memory (termination control) | request `128 MiB`, hard limit `192 MiB` | 16 MiB allocation passed; 384 MiB allocation destroyed Sandbox; terminal `137` | `HARD_CEILING_PROVEN` |
| Storage | no selectable stable parameter | root `df` reported `9223372036854771712` bytes; measurement only | `UNPROVEN` |

The CPU and memory classifications use live cgroup state and bounded memory
behavior, not documentation alone. The memory limit termination was
distinguishable from the normal control and the destroyed allocation was
confirmed non-running. Stable Modal 1.5.5 `Sandbox.create` exposed no
`storage`, `disk`, or `disk_size` parameter. This mandatory storage gap is the
sole reason the overall result is partial.

## Timeout, descendants, output, and teardown

### Timeout

A Sandbox with a 10-second maximum lifetime ran `sleep 30`. Modal raised
`SandboxTimeoutError` after approximately 11.5 seconds, and `poll()` returned
`124`. The allocation was already terminal and remained confirmed terminal.

### Descendant lifecycle

The primary command started a background `sleep 120` child and exited. The
child remained alive immediately after parent exit, proving that foreground
completion alone is insufficient. `terminate(wait=True)` then returned `137`,
`poll()` returned `137`, and reconnecting to execute `kill -0` returned
`NotFoundError`. Whole-sandbox destruction therefore contained the descendant.

### Bounded output

The synthetic output command produced 81,920 bytes. The probe retained exactly
4,096 bytes, marked truncation, and discarded the remainder. Provider-native
truncation was not inferred or required.

### Teardown and cleanup

All four canonical Sandboxes reached a terminal state. A final filtered
`Sandbox.list` returned no task-tagged running Sandbox. The proof-only Volume
context ended, the exact Volume ID was explicitly deleted, and a subsequent
lookup returned `NotFoundError`. The three earlier proof-only calibration
Volumes were also explicitly deleted by exact ID and verified non-resolvable.

The explicit ephemeral Volume deletion uses Modal 1.5.5's installed
volume-ID deletion method because context exit stops heartbeats but does not
make deletion immediately observable. This is proof cleanup, not production
adapter design.

## Allocation and tenant posture

The probe bound each allocation in Codexify-owned tags/receipt metadata to a
synthetic execution principal, task ID, workspace ID, attempt ID, and grant
reference. Provider allocation IDs remained separately inspectable.

Cross-account/cross-tenant isolation is `UNPROVEN`: only one Modal
profile/workspace was available. Distinct Sandbox IDs and the fresh-mount
verification prove allocation separation inside that account, not hostile
tenant separation or provider-operator access policy.

## ADR-077 conformance matrix

| ADR-077 requirement | Result | Enforcement/evidence | Mandatory |
| --- | --- | --- | --- |
| isolated allocation | PASS | Fresh Sandbox IDs; gVisor Linux runtime; host repository path absent | yes |
| workspace materialization | PASS | Trusted control-plane upload to proof-only Volume | yes |
| workspace read | PASS | Enumeration, reads, and three hashes matched | yes |
| provider-enforced read-only workspace | PASS | Stable read-only Volume mount; all attempted mutations had no effect | yes |
| guest cannot reverse protection | PASS | permission restoration, links, and remount failed; fresh mount unchanged | yes |
| writable scratch | PASS | create/modify/rename/delete under `/tmp/codexify-scratch` | yes |
| foreground execution | PASS | deterministic foreground command exited `0` | yes |
| command network denied | PASS | provider `block_network=True`; DNS, hostname HTTPS, and direct IP failed | yes |
| control-plane transport preserved | PASS | `poll`, filtered `list`, and termination worked during/after egress denial | yes |
| minimal environment | PASS | explicit one-value allowlist plus provider/image baseline; no wholesale parent environment | yes |
| credential non-disclosure | PASS | known credential key names absent; no Secrets supplied | yes |
| timeout | PASS | 10-second lifetime produced `SandboxTimeoutError` and terminal `124` | yes |
| descendant teardown | PASS | child survived parent, then whole Sandbox became unreachable/terminal `137` | yes |
| CPU hard ceiling | PASS | requested tuple matched live cgroup quota `0.25` | yes |
| memory hard ceiling | PASS | live cgroup limit plus normal/over-limit control and terminal `137` | yes |
| storage ceiling/posture | UNPROVEN | no stable creation parameter; `df` is measurement only | yes |
| bounded output | PASS | 81,920 observed bytes reduced to 4,096 with truncation marker | yes |
| teardown confirmed | PASS | every allocation terminal; filtered running list empty | yes |
| task/workspace lineage | PASS | synthetic principal/task/workspace/attempt/grant metadata retained with provider IDs | yes |
| cross-tenant isolation | UNPROVEN | one Modal account/profile only | qualification note |
| provider/version provenance | PASS | SDK, stable API, cloud, region, image, runtime, app, Volume, Sandbox IDs recorded | yes |

Because one mandatory gate is `UNPROVEN`, this proof cannot emit
`MODAL_READ_EXEC_CONFORMANT`. Modal satisfies useful and security-critical
parts of the contract, and the missing stable storage ceiling is a bounded
provider-surface gap rather than evidence that the read-only boundary itself
is impossible. The exact conclusion is therefore:

`MODAL_READ_EXEC_PARTIALLY_CONFORMANT`

## Warnings, failures, and limitations

Warnings:

- Stable Modal 1.5.5 exposes no attempt-level disk/storage ceiling.
- Unpinned provider placement varied between Azure `eastus` and OCI
  `eu-frankfurt-1`; residency policy was not exercised.
- `chmod` and `chown` returned zero on the read-only mount even though direct
  stat and a fresh mount proved no effect. Callers must judge effects, not
  command exit alone.
- The proof used one Modal profile/workspace and cannot establish cross-account
  isolation, provider-operator access, quotas, or commercial service terms.
- Calibration consumed additional short-lived allocations before the final
  exact script run; all were terminated and all proof Volumes were deleted.

Failure:

- `STORAGE_CEILING_UNPROVEN` is the single mandatory ADR-077 failure.

Unproven assumptions:

- whether a separately contracted Modal resource/product can impose a hard
  per-Sandbox ephemeral disk ceiling outside the stable 1.5.5 API;
- cross-account tenant isolation and data-residency enforcement;
- provider billing/usage totals, which were not exposed by the tested API;
- long-duration behavior beyond the bounded proof window.

## Validation and repository scope

The focused probe is
[`scripts/modal_conformance_probe.py`](../../../../scripts/modal_conformance_probe.py).
It is not a production `SandboxProvider` adapter.

Validation performed for the proof surface:

- required `5/5` local/upstream overlap inspection — PASS; zero overlapping paths;
- local profile structural check and authenticated `modal environment list` — PASS;
- Modal SDK version check — PASS, `1.5.5`;
- final exact live probe — PASS as an executed probe; conclusion
  `MODAL_READ_EXEC_PARTIALLY_CONFORMANT`;
- post-run Sandbox and Volume cleanup checks — PASS;
- Python compilation, docs validation, diff checks, secret-value scans, staged
  scope inspection, and commit evidence are recorded in the task closeout.

Only the Modal proof dependency pin, focused probe, and this proof artifact
belong to the change. Production execution behavior remains untouched.

## Recommended next Task Spec boundary

Do not implement the Modal Sandbox Provider Adapter yet as fully conformant
for ADR-077. First run a narrow Modal storage-ceiling qualification:

`Qualify a provider-enforced Modal Sandbox storage ceiling for ADR-077`

That task should determine whether a stable account-available Modal primitive
can impose a hard per-attempt ephemeral storage limit. If it cannot, resume
provider comparison or decide explicitly whether ADR-077 should support a
separately named resource-class posture. Do not weaken or silently reinterpret
ADR-077 in the qualification task.

## Axis KB addition

Record that hosted Modal with Python SDK `1.5.5` and the stable Sandbox API
live-proved the strict read-only Volume boundary, writable scratch, deny-all
command networking with control-plane separation, credential isolation, hard
CPU/memory ceilings, timeout, bounded output, whole-sandbox descendant
teardown, source integrity, and cleanup. Full ADR-077 conformance remains
blocked solely by the absence of a proven stable storage ceiling. Exact result:
`MODAL_READ_EXEC_PARTIALLY_CONFORMANT`.
