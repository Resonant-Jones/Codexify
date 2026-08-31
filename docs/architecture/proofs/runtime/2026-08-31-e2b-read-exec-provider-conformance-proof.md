# Hosted E2B Read/Exec Provider Conformance Proof

## Qualification conclusion

`E2B_READ_EXEC_PARTIALLY_CONFORMANT`

This is a live hosted-provider result for the ADR-077 immediate read/exec
posture. E2B successfully provided isolated allocations, synthetic workspace
materialization, foreground execution, provider-configured command egress
denial, minimal command environment, bounded timeout/output observations, and
confirmed teardown. It did not provide an actually read-only workspace path
through the tested SDK/API surface. Storage was observable but not enforceable
as a selected ceiling, and tenant separation could not be proven with the one
operator credential/team available.

The smallest direct blocker is `READ_ONLY_WORKSPACE_UNSUPPORTED`: the
materialized workspace was writable by the provider/filesystem API and became
mutation-resistant only after guest `chmod`. The probe then successfully
re-enabled writes, proving that this was guest permission state rather than a
provider read-only boundary. No E2B adapter or Pi/Guardian integration is
authorized by this result.

## Scope and evidence posture

This proof belongs to the Sandbox Provider conformance boundary established by
[ADR-077](../../adr/077-sandbox-execution-authority-and-provider-boundary.md).
It does not change ADR-077, Guardian, Pi tool activation, Pi `spawnHook`, the
Coding Worker, Compose authority, provider routing, or ordinary-turn
execution.

The evidence labels used below are:

| Label | Meaning |
| --- | --- |
| `LIVE-RUNTIME` | Observation returned by a real hosted E2B allocation during this proof. |
| `SDK-SURFACE` | Inspection of the pinned installed SDK/API surface; not a provider behavior claim by itself. |
| `DOC` | Official E2B documentation or source; capability evidence only, not live proof. |
| `UNPROVEN` | The proof did not establish the assertion and does not infer it. |

No repository or production user data was uploaded. The fixture was synthetic.
The E2B API key was loaded only as `E2B_API_KEY` from the ignored local
`.env.tester`; no key value, environment value, or credential-bearing output
was recorded here.

## Revision, dependency, and runtime identity

| Property | Value |
| --- | --- |
| Branch | `main` |
| Upstream | `origin/main` |
| Pre-task HEAD | `93d7802771c8caa9006b50077351c3e8ec51d80f` (`Define sandbox execution authority boundary`) |
| Pre-task worktree | Clean before the focused probe and pin were added |
| Proof window | `2026-08-31T15:28:49.761498Z` to `2026-08-31T15:29:26.057499Z` |
| E2B Python SDK | `2.46.0` |
| Pin | [`requirements/e2b-conformance.txt`](../../../../requirements/e2b-conformance.txt) |
| Tested API generation | Generated E2B Cloud REST/envd API surface shipped by Python SDK `2.46.0`; no separate service API version was exposed by the inspected runtime |
| Provider | E2B Cloud hosted service, default control plane |
| Service tier | Not exposed by the inspected hosted API |
| Operator credential scope | One E2B credential/team; cross-tenant qualification was not possible |
| Allocations | Three: primary, lifecycle-timeout, and peer-isolation |
| Approximate usage | Three sandbox allocations; requested lifetimes were 180 seconds, 7 seconds, and 180 seconds. Billing/usage totals were not exposed. |

The pinned SDK version was verified at runtime before allocation. The probe
used a process-local `pyqwest` `SyncHTTPTransport(use_system_dns=True)` because
the host's default Rust resolver appended its Tailscale search suffix to
`api.e2b.app`; host `curl`/`dig` resolved the endpoint, and the resolver-enabled
SDK path allocated successfully. This is a control-plane connectivity
workaround inside the proof process only; it is not a provider network-policy
workaround and is not production code.

The maintained E2B materials consulted for the tested generation were:

- [E2B Python SDK package metadata](https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/pyproject.toml) (`DOC`; source currently identifies `2.46.0`).
- [Sandbox lifecycle and timeout documentation](https://docs.e2b.dev/sandbox) (`DOC`).
- [Network internet-access documentation](https://docs.e2b.dev/network/internet-access) (`DOC`).
- [Filesystem read/write documentation](https://docs.e2b.dev/filesystem/read-write) (`DOC`).
- [Sandbox metrics documentation](https://docs.e2b.dev/sandbox/metrics) (`DOC`).
- [Sandbox environment-variable documentation](https://docs.e2b.dev/sandbox/environment-variables) (`DOC`).

The official material was used to identify the current API surface and
configuration vocabulary. The qualification outcome below is based on the
live run, not on those documents.

## Probe boundary

The focused probe is [`scripts/e2b_conformance_probe.py`](../../../../scripts/e2b_conformance_probe.py).
It calls the E2B SDK directly and is deliberately not a `SandboxProvider`
adapter. It creates synthetic metadata for one execution principal, task,
workspace, and grant; uses the `base` template; sets `secure=True`; requests
`allow_internet_access=False` plus `deny_out=0.0.0.0/0`; supplies only one
test-safe environment variable; bounds captured stdout/stderr at 4096 bytes;
and explicitly kills allocations before exit.

The bounded JSON receipt from the completed run was ephemeral and was not
committed separately. Its SHA-256 was
`1ee765b1f3f5cf140c65d0c80a7f203e82fd233a5262efdb86216b01afa2185b`.

## Live allocation and provenance

| Role | Sandbox ID | Template | Started | Provider-reported state at inspection | Requested lifetime |
| --- | --- | --- | --- | --- | ---: |
| primary read/exec | `izzt32tib3g4fu00tsk8z` | `base` / `rki5dems9wqfm4r03t7g` | `2026-08-31T15:28:50.185447Z` | `running` | 180 s |
| lifecycle timeout | `iavsdv0x9xd100xvlx5s7` | `base` / `rki5dems9wqfm4r03t7g` | `2026-08-31T15:29:16.918413Z` | `running` before expiry | 7 s |
| peer isolation | `i09rrwrcdp3dyi75zoez6` | `base` / `rki5dems9wqfm4r03t7g` | `2026-08-31T15:29:24.350747Z` | `running` at inspection | 180 s |

The primary runtime reported Linux `6.1.158+`, `x86_64`, UID `1000`, user
`user`, and working directory `/home/user`. It reported `envd_version=0.6.10`,
`cpu_count=2`, `memory_mb=512`, no volume mounts, and no exposed region or
sandbox domain. The primary network metadata returned
`allow_internet_access=false`, `deny_out=["0.0.0.0/0"]`, and
`allow_public_traffic=true`; the live application probes below are the
effective behavior evidence rather than an inference from one field.

The control plane returned stable sandbox IDs and metadata for all three
allocations. E2B did not expose a separate tenant ID, region, service tier, or
Codexify task authority binding in the inspected response.

## Basic isolated execution and workspace materialization

The primary foreground command completed with exit code `0` and bounded
observable output:

```text
cwd=/home/user
kernel=Linux 6.1.158+ x86_64
uid=1000
user=user
```

The probe also checked that `/Volumes/Dev_SSD/Codexify-main` was absent inside
the sandbox. The check exited `0`. This establishes that the sandbox did not
inherit the repository path merely because the allocation existed; it does not
claim isolation from every possible host-side metadata channel.

The synthetic fixture was materialized through the E2B filesystem API at one
fresh workspace path, with a separate scratch path. E2B filesystem readback
and a command-side `cat` matched the source fixture:

| Relative path | Bytes | SHA-256 | Readback |
| --- | ---: | --- | --- |
| `readme.txt` | 39 | `fe45e42701109445a9d75aa94904a0424bd719ca9bc63e77eeb4d28ced01e36e` | PASS |
| `nested/marker.txt` | 25 | `166accecced05abcefe9a3552425a04fe968d1d1e5f1ef1449253aeaad5499ca` | PASS |
| `nested/checksum.bin` | 32 | `630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd` | PASS |

The peer allocation wrote a different synthetic sentinel at the same absolute
path used for the primary's peer-visibility check. The primary could not see
that path, and the two allocations had different sandbox IDs. This proves
allocation filesystem separation within one credential/team, not tenant
separation.

## Actual read-only workspace test

The installed `Sandbox.create` surface exposed `volume_mounts` but no
`read_only` or `readonly` parameter. Inspection of the installed generated
volume-mount model also found no read-only field. This is `SDK-SURFACE` evidence
that the tested API generation has no provider-native read-only mount control.

The probe intentionally kept the distinction between the protected workspace
candidate and authorized scratch explicit:

| Test | Live result |
| --- | --- |
| Read protected workspace | PASS; filesystem readback and command `cat` matched |
| Guest `chmod 0555`/`0444` preparation | Exit `0`; guest permission mutation only |
| Create file after guest chmod | Exit `1`, permission denied |
| Modify existing file after guest chmod | Exit `1`, permission denied |
| Delete protected file after guest chmod | Exit `1`, permission denied |
| Rename protected file after guest chmod | Exit `1`, permission denied |
| Re-enable guest write permission and modify | Exit `0`; bypass succeeded |
| Authorized scratch write | Exit `0`; `scratch-ok` was written |
| Provider-enforced read-only workspace | `READ_ONLY_WORKSPACE_UNSUPPORTED` |

The four failed mutation commands are not read-only provider proof: they were
caused by guest mode bits and were followed by a successful mode bypass. The
workspace itself was initially writable through the E2B filesystem API. A
future adapter must fail closed unless E2B exposes a provider-enforced
read-only input/mount mechanism or a different conforming provider is
selected.

## Command egress and control-plane separation

The primary was allocated with both `allow_internet_access=False` and
`deny_out=["0.0.0.0/0"]`. No guest firewall command was used. The provider
returned the same deny-all configuration in sandbox metadata.

Live application-level observations were:

| Probe | Result |
| --- | --- |
| DNS `getent hosts example.com` | Timed out under deny-all egress; no DNS answer was returned |
| Hostname request `curl -fsS --max-time 3 https://example.com/` | Exit `28`; DNS resolution timed out |
| Direct-IP request `curl -fsSk --max-time 3 https://1.1.1.1/` | Exit `35`; TLS connection failed |
| `get_info()` after command probes | PASS |
| `get_metrics()` after command probes | PASS |

The command tests therefore establish provider-configured, live application
denial for DNS/hostname and direct-IP paths, while control-plane observation
remained functional. The classification is `provider-enforced configuration
plus live application-level observation`; no guest firewall was trusted as the
boundary. The control-plane calls were made through E2B's API with the
credential outside the sandbox and are not evidence that sandbox commands had
network access.

## Environment and credential isolation

The probe inspected environment key names only. It never emitted values. The
sandbox exposed 14 names:

```text
E2B_CONFORMANCE_SAFE
E2B_EVENTS_ADDRESS
E2B_SANDBOX
E2B_SANDBOX_ID
E2B_TEMPLATE_ID
HOME LOGNAME PATH PS1 PWD SHELL SHLVL USER _
```

`E2B_CONFORMANCE_SAFE` was the only intentionally supplied variable. The
E2B API key name was absent; no known Codexify database, model/provider, or
service credential name was present; and no parent-host key beyond the safe
baseline was copied. The E2B runtime-injected `E2B_*` names are identifiers or
addresses observed by name only, not credential values.

Result: minimal environment `PASS`; credential non-disclosure `PASS`, with the
scope limited to key-name inspection and the operator credential/team used for
this proof.

## Background descendants and timeout

The primary ran a shell that started `sleep 30` with output redirected away,
wrote the child PID to scratch, and exited. The parent returned exit `0`; the
probe observed the child PID with `kill -0` immediately after parent exit. This
proves that a foreground command completion alone does not prevent a
background descendant in the live allocation.

The probe then immediately destroyed the entire primary allocation. E2B
`kill()` returned successfully and `is_running()` returned `false`. The
descendant was not given a second live allocation or a reusable path. This is
`PASS` only under the ADR-077 immediate whole-allocation teardown rule; E2B
does not provide a foreground-only guarantee merely because the parent exited.

The separate 7-second allocation ran `sleep 30`. The command ended with the
SDK's `TimeoutException` after approximately 6.95 seconds, distinct from a
normal nonzero exit. The allocation reported `is_running=false` on the first
post-expiry check, so timeout cleanup and descendant unreachability were
confirmed. A subsequent explicit kill was an idempotent no-op (`kill()` false)
with `is_running=false`, not an ambiguous live state.

## CPU, memory, and storage posture

The base template's live metadata and metrics reported:

| Dimension | Classification | Live observation | Selection/enforcement finding |
| --- | --- | --- | --- |
| CPU | `PREDECLARED_RESOURCE_CLASS` | 2 vCPU in sandbox info and metrics | No per-allocation CPU selector in `Sandbox.create`; no hard-ceiling stress test was attempted |
| Memory | `PREDECLARED_RESOURCE_CLASS` | 512 MB in sandbox info; latest metrics `mem_total=501293056` bytes | No per-allocation memory selector; no hard-ceiling stress test was attempted |
| Storage | `MEASUREMENT_ONLY` | Latest metrics `disk_total=22757814272`, `disk_used=1652707328`; bounded `df` observation reported 22,224,428 KiB total | No per-allocation storage selector or hard ceiling was exposed/proven |

The provider resource class is recorded as a class, not silently promoted to a
requested hard ceiling. CPU and memory have a live predeclared class; storage
remains an unproven mandatory boundary because the service exposed measurement
only. No resource exhaustion was attempted.

## Bounded output

The primary ran a deterministic 65,536-byte output source. The E2B command
result reported 65,536 bytes; the probe stored only the first 4,096 bytes,
marked the result truncated, and emitted no larger payload. This demonstrates
the required Codexify-side bounded collection policy even though the provider
returned the complete bounded test payload to the SDK.

Result: `PASS` for adapter-side output bounding; provider-native truncation was
not required or inferred.

## Teardown and provenance confirmation

| Allocation | Explicit destroy | Post-destroy `is_running()` | Confirmation |
| --- | --- | --- | --- |
| Primary `izzt32tib3g4fu00tsk8z` | `kill()` true | false | PASS |
| Lifecycle timeout `iavsdv0x9xd100xvlx5s7` | already expired; `kill()` false | false | PASS; lifecycle expiry was already confirmed |
| Peer `i09rrwrcdp3dyi75zoez6` | `kill()` true | false | PASS |

Teardown is therefore confirmed for all three allocations. The live receipt
also retained provider IDs, template ID/name, lifecycle, network policy,
environment runtime version, CPU/memory class, timestamps, and metrics. Region,
sandbox domain, service tier, and provider tenant identity were unavailable,
not guessed.

## ADR-077 conformance matrix

| ADR-077 Requirement | Result | Evidence | Mandatory Gate |
| --- | --- | --- | --- |
| isolated allocation | PASS | Three fresh sandbox IDs; primary command ran as UID 1000 in `/home/user`; host repository path absent | yes |
| workspace materialization | PASS | Synthetic nested fixture materialized and checksum/readback matched | yes |
| workspace read | PASS | Filesystem API and command read both matched fixture | yes |
| actual read-only workspace | FAIL | `READ_ONLY_WORKSPACE_UNSUPPORTED`; no provider read-only field; guest chmod was bypassed | yes |
| writable scratch | PASS | Separate scratch path write returned exit 0 | no/immediate support |
| foreground exec | PASS | Deterministic foreground command returned bounded stdout/stderr and exit 0 | yes |
| command network denied | PASS | Provider deny-all metadata plus DNS timeout, hostname exit 28, direct-IP exit 35 | yes |
| provider control transport preserved | PASS | `get_info()` and `get_metrics()` succeeded after command egress denial | yes |
| minimal environment | PASS | 14 key names; one supplied safe variable; no non-baseline parent keys copied | yes |
| credential non-disclosure | PASS | E2B API key name and known Codexify/provider credential names absent; values never inspected/emitted | yes |
| timeout | PASS | 7-second lifecycle produced SDK `TimeoutException`; allocation `is_running=false` | yes |
| descendant teardown | PASS | Child survived parent exit, then immediate whole-allocation destroy was confirmed | yes |
| CPU posture | PASS | `PREDECLARED_RESOURCE_CLASS`: 2 vCPU observed; no hard-ceiling claim | yes |
| memory posture | PASS | `PREDECLARED_RESOURCE_CLASS`: 512 MB observed; no hard-ceiling claim | yes |
| storage posture | UNPROVEN | `MEASUREMENT_ONLY`: disk metrics/`df` observed, no selected ceiling | yes |
| bounded output | PASS | 65,536-byte provider result collected/stored at 4,096-byte probe bound | yes |
| sandbox teardown confirmed | PASS | All three allocations returned `is_running=false` after lifecycle/kill | yes |
| tenant/task allocation identity | UNPROVEN | Synthetic principal/task/workspace/grant metadata and separate IDs observed; cross-tenant proof unavailable with one credential/team | yes |
| provider/version provenance | PASS | SDK `2.46.0`, endpoint identity, IDs, template, envd version, lifecycle, network, timestamps recorded; unavailable fields marked | yes |

The mandatory failures/unproven gates prevent `E2B_READ_EXEC_CONFORMANT`.
The useful live capabilities and the absence of a demonstrated fundamental
service impossibility support `E2B_READ_EXEC_PARTIALLY_CONFORMANT` rather than
`E2B_READ_EXEC_NONCONFORMANT`.

## Limitations and next Task Spec boundary

The proof does not establish:

- a provider-native read-only workspace/input mount;
- a hard storage ceiling selected by Codexify;
- cross-tenant separation using independently scoped E2B credentials;
- a separately exposed E2B service tier, region, or tenant identity;
- post-destroy descendant state by executing another command after the
  allocation was destroyed (the provider's confirmed non-running state is the
  available lifecycle assertion);
- a production integration, `SandboxProvider` interface, Guardian route, Pi
  hook, or release claim.

The next task should remain at the provider qualification boundary: first ask
E2B whether a provider-enforced read-only input/mount feature and an explicit
storage resource class can be represented by the current hosted API, then
re-run this proof with separately scoped tenant credentials if Codexify needs
tenant qualification. If either boundary remains unavailable, evaluate another
hosted Sandbox Provider or define the smallest Codexify-owned provider
boundary. Do not build an adapter that treats chmod, discarded writes, or
measurement alone as conformance.

## Validation and closeout

The live probe was run with the key sourced only from `.env.tester`:

```text
set -a; source .env.tester; set +a
python scripts/e2b_conformance_probe.py --output <ephemeral-proof-json>
```

The completed probe exited `0`, verified the installed SDK as `2.46.0`, and
used three allocations. `python3 -m py_compile scripts/e2b_conformance_probe.py`
passed. The repository documentation validator, `git diff --check`, staged
path inspection, and final status are recorded in the task closeout after this
artifact is staged. No `.env` or `.env.tester` file is tracked by this proof.

## Governing and related evidence

- [ADR-077](../../adr/077-sandbox-execution-authority-and-provider-boundary.md)
- [ADR-020](../../adr/020-guardian-mediated-coding-agent-execution-contract.md)
- [ADR-068](../../adr/068-campaign-engine-live-role-execution-contract.md)
- [Pi Invocation Boundary Contract](../../pi-invocation-boundary-contract.md)
- [2026-08-31 Guardian Native Execution Seam Audit](2026-08-31-guardian-native-execution-seam-audit.md)
- [2026-08-29 Pi tool activation telemetry repair proof](2026-08-29-pi-0821-tool-activation-telemetry-repair-proof.md)

Axis KB addition recommended: hosted E2B `2.46.0` live proof is
`E2B_READ_EXEC_PARTIALLY_CONFORMANT`; the immediate blocker is provider-native
read-only workspace semantics, with storage hard ceilings and cross-tenant
identity still unproven. E2B command egress denial, control-plane separation,
environment credential non-disclosure, timeout, bounded output, and teardown
were live-proven in one credential/team.
