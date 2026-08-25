# Disposable image tag-retention experiment R2 proof

Date: 2026-08-25
Execution lane: Architecture-Impact
Task kind: proof
Evidence posture: live-runtime proven
Result: `TAG_REPLACEMENT_PRESERVES_UNTAGGED_IMMUTABLE_IMAGE`
Confidence: HIGH

## Decision

R2 repeated the disposable image lifecycle inside one uninterrupted foreground
host-shell invocation. The same event-client PID was started before image A,
captured A import, B import, and the single replacement tag, remained alive at
the accepted T+5, T+30, and T+120 checkpoints, and was stopped only after the
result freeze.

Image A began with exactly one mutable tag. After that tag moved to image B, A
became untagged but remained directly inspectable by immutable ID at T0, T+5,
T+30, T+120, and result freeze. No explicit task removal or prune occurred
before result freeze, and the captured image-event log contains no delete or
prune event.

Supported conclusion:

```text
Moving an image's only mutable tag does not by itself remove the old immutable
image object during the controlled 120-second observation window.
```

This removes tag replacement alone as the active causal candidate for the
historical `ee3f...` loss. It does not identify the historical deletion
mechanism or establish long-term dangling-image retention.

## Lineage and authority boundary

| Field | Result |
| --- | --- |
| Branch | `proof/disposable-image-tag-retention-experiment-r2` |
| Task base HEAD | `803c7aae30298cfc50be808e2ee085e40f9b2945` |
| Observed `origin/main` | `803c7aae30298cfc50be808e2ee085e40f9b2945` |
| `git fetch origin main` | PASS; attempted exactly once |
| Commits above observed main at branch creation | none |
| R1 experiment predecessor | `6df26b4bda91aba3148c6cd86aa7bfba925ee505`; evidence only |
| Retention-classification predecessor | `bc88a3a863ab38f9f95359eab94ed72c42af2fd4`; evidence only |
| R4 predecessor | `61fbb2805bafa8060e99a5fe390fd3f81f2de1bb`; evidence only |
| ADR impact | No ADR impact |
| Governing contracts | ADR-020, ADR-066, ADR-068, Config and Ops, Agent Protocol Operations |

This proof changes no runtime semantics, Guardian/Pi/provider/credential
authority, Docker topology, canonical image ownership, persistence, or release
posture. No Codexify runtime image participated.

## Docker authority and namespace preflight

| Field | Result |
| --- | --- |
| Docker context | `desktop-linux` |
| Docker endpoint | `unix:///Users/chriscastillo/.docker/run/docker.sock` |
| Docker server version | `29.7.2` |
| Docker server OS / architecture | `linux/arm64` |
| Reserved namespace | `codexify-retention-probe-r2` |
| Namespace preflight | PASS; no existing references |
| Containers created | 0 |

## Scratch inputs and harness

Scratch root: `/Volumes/Dev_SSD/codexify-image-retention-probe-r2.cqOJ54`
Scratch cleanup: PASS; the exact root was removed after result freeze and
task-only Docker cleanup.

| Input | Size | SHA-256 |
| --- | ---: | --- |
| `probe-a.tar` | 6656 bytes | `d0cf651beea02c2b63697023db2aabf221b149a1fcb25029450f86a1780810c1` |
| `probe-b.tar` | 6656 bytes | `8b787548020d354c0f83652c4e961b4767367ccfd140cca38af815afd218ab7d` |

The archives contained only these deterministic marker files:

```text
rootfs-a/probe-marker.txt: codexify-retention-probe-r2-a
rootfs-b/probe-marker.txt: codexify-retention-probe-r2-b
```

The single experiment harness was:

```text
/Volumes/Dev_SSD/codexify-image-retention-probe-r2.cqOJ54/scripts/run-retention-experiment.sh
```

It was invoked exactly once in the foreground as:

```sh
/bin/bash "$SCRATCH_ROOT/run-retention-experiment.sh"
```

The lifecycle from event-capture startup through the final checkpoint and
event-client stop remained inside that one process. The harness exited with
status 1 after event stop while evaluating bookkeeping variables that had not
been initialized. The result-freeze metadata, event log, and all Docker
observations had already been written; no Docker mutation occurred after the
freeze. The counters and classification were reconciled from those frozen
artifacts before cleanup.

## Image identities and pre-replacement posture

| Field | Image A | Image B |
| --- | --- | --- |
| Full immutable ID | `sha256:515b83a79ee2688d6c21efe50fe55d71d4f57e13015ed8c6b3fd9160820c76d6` | `sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70` |
| Import reference | `codexify-retention-probe-r2:latest` | `codexify-retention-probe-r2:replacement` |
| RepoTags before replacement | `["codexify-retention-probe-r2:latest"]` | `["codexify-retention-probe-r2:replacement"]` |
| RepoDigests before replacement | `codexify-retention-probe-r2@sha256:515b83a79ee2688d6c21efe50fe55d71d4f57e13015ed8c6b3fd9160820c76d6` | `codexify-retention-probe-r2@sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70` |
| Size | 1179 bytes | 1179 bytes |
| Direct inspect | PASS | PASS |

The exact pre-freeze Docker mutations were:

```text
TASK_OWNED_IMAGE_IMPORTS: 2
PRIMARY_TAG_REPLACEMENTS: 1
TASK_EXPLICIT_IMAGE_REMOVALS: 0
TASK_PRUNE_OPERATIONS: 0
CODEXIFY_IMAGE_BUILDS: 0
CODEXIFY_IMAGE_PULLS: 0
CODEXIFY_IMAGE_TAG_CHANGES: 0
CODEXIFY_IMAGE_REMOVALS: 0
NON_TASK_IMAGE_TAG_CHANGES: 0
NON_TASK_IMAGE_REMOVALS: 0
```

## Continuous event capture

| Field | Result |
| --- | --- |
| Event-client PID | `96200` |
| Capture start wall-clock | `2026-08-25T20:47:08.716450000Z` |
| Capture start monotonic value | `37495613122875` |
| Event client alive before A import | PASS |
| Event client alive after A import | PASS |
| Event client alive after B import | PASS |
| Event client alive before replacement | PASS |
| Event client alive after replacement | PASS |
| Event client alive at T+5/T+30/T+120 | PASS at all checkpoints |
| Event client alive at result freeze | PASS |
| Capture end wall-clock | `2026-08-25T20:49:10.233865000Z` |
| Capture end monotonic value | `37617129186916` |
| Event-client stop | PASS |
| Continuous capture from before A import to result freeze | PASS |

The captured event timeline contained exactly these task-owned image events,
in event-time order:

```text
1. image tag
   actor=sha256:515b83a79ee2688d6c21efe50fe55d71d4f57e13015ed8c6b3fd9160820c76d6
   name=codexify-retention-probe-r2:latest
   timeNano=1787690829859523762

2. image import
   actor=sha256:515b83a79ee2688d6c21efe50fe55d71d4f57e13015ed8c6b3fd9160820c76d6
   name=sha256:515b83a79ee2688d6c21efe50fe55d71d4f57e13015ed8c6b3fd9160820c76d6
   timeNano=1787690829898008554

3. image tag
   actor=sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70
   name=codexify-retention-probe-r2:replacement
   timeNano=1787690829999639637

4. image import
   actor=sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70
   name=sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70
   timeNano=1787690830006140637

5. image tag
   actor=sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70
   name=codexify-retention-probe-r2:latest
   timeNano=1787690830108645887
```

Event counts before result freeze:

```text
IMPORT_EVENT_COUNT: 2
TAG_EVENT_COUNT: 3
UNTAG_EVENT_COUNT: 0
DELETE_EVENT_COUNT_BEFORE_RESULT_FREEZE: 0
PRUNE_EVENT_COUNT_BEFORE_RESULT_FREEZE: 0
IMAGE_A_DELETE_EVENT_BEFORE_RESULT_FREEZE: NO
```

The initial tag events are the references created inherently by the two
imports. The third tag event is the single primary replacement that moved
`latest` from A to B. The event log contains no A deletion or prune event.

## Tag replacement and monotonic checkpoints

The intervention was exactly:

```sh
docker tag \
  sha256:9dc6e1bf04126f2c28d11474456757fc301e8381283e30e8ed0bc00916b8cb70 \
  codexify-retention-probe-r2:latest
```

| Field | Result |
| --- | --- |
| Tag replacement wall-clock | `2026-08-25T20:47:10.078110000Z` |
| Tag replacement monotonic value | `37496972944125` |
| Tag replacement result | PASS |
| T0 elapsed | 0.039 seconds |
| T0 image A inspect | PASS |
| T0 image A RepoTags | `[]` |
| T0 latest resolution | B ID; PASS |

The image-A checkpoints used the same monotonic clock and met the packet's
acceptance windows:

| Checkpoint | Wall-clock | Elapsed | Timing window | A inspect | A RepoTags | Size |
| --- | --- | ---: | --- | --- | --- | ---: |
| T+5 | `2026-08-25T20:47:15.177704000Z` | 5.053 s | PASS (`5.0 <= t < 8.0`) | PASS | `[]` | 1179 |
| T+30 | `2026-08-25T20:47:40.210889000Z` | 30.087 s | PASS (`30.0 <= t < 33.0`) | PASS | `[]` | 1179 |
| T+120 | `2026-08-25T20:49:10.171808000Z` | 120.057 s | PASS (`120.0 <= t < 124.0`) | PASS | `[]` | 1179 |

At result freeze, A remained inspectable with RepoTags `[]` and the event
client was still alive.

## Primary classification and causal posture

```text
PRIMARY_CLASSIFICATION: TAG_REPLACEMENT_PRESERVES_UNTAGGED_IMMUTABLE_IMAGE
CONFIDENCE: HIGH
HISTORICAL_EE3F_LOSS_CAUSED_BY_TAG_REPLACEMENT_ALONE:
DISPROVEN_WITHIN_CONTROLLED_120_SECOND_WINDOW
```

Exact causal statement: In this controlled disposable experiment, moving A's
only mutable tag to B did not remove A's immutable image object during the
120-second no-action observation window. The historical `ee3f...` disappearance
therefore required an additional retention-loss event or mechanism, which this
experiment does not identify.

This does not prove long-term dangling-image retention, survival across prune
or daemon reset, Docker Desktop behavior, BuildKit behavior, repository cleanup
execution, or the historical deletion actor.

## Cleanup and invariant counts

Cleanup occurred only after result freeze and event-client stop:

```text
TASK_OWNED_REFERENCES_CLEANED: 2
TASK_OWNED_IMAGE_OBJECTS_CLEANED: 2
TASK_NAMESPACE_EMPTY_AFTER_CLEANUP: YES
IMAGE_A_INSPECT_AFTER_CLEANUP: FAIL_EXPECTED
IMAGE_B_INSPECT_AFTER_CLEANUP: FAIL_EXPECTED
HOST_SCRATCH_CLEANUP: PASS
```

Removing B's final reference deleted B before the subsequent explicit B-ID
cleanup command; that second removal returned `No such image`. The cleanup
target remained task-owned and exact. A was removed by its immutable ID.

```text
CONTAINER_CREATIONS: 0
CONTAINER_STARTS: 0
CONTAINER_STOPS: 0
CONTAINER_REMOVALS: 0
DOCKER_SYSTEM_PRUNE_OPERATIONS: 0
DOCKER_IMAGE_PRUNE_OPERATIONS: 0
DOCKER_BUILDER_PRUNE_OPERATIONS: 0
DOCKER_BUILDX_PRUNE_OPERATIONS: 0
DOCKER_CONTEXT_CHANGES: 0
DOCKER_CONFIGURATION_CHANGES: 0
DOCKER_DESKTOP_RESTARTS: 0
DOCKER_DAEMON_RESTARTS: 0
CANONICAL_NETWORK_MUTATIONS: 0
CANONICAL_VOLUME_MUTATIONS: 0
HOST_PACKAGE_INSTALLATIONS: 0
OPENSSL_SOURCE_ACQUISITIONS: 0
OPENSSL_CONFIGURES: 0
OPENSSL_BUILDS: 0
OPENSSL_INSTALLS: 0
NODE_SOURCE_ACQUISITIONS: 0
NODE_BUILDS: 0
PI_EXECUTION_ATTEMPTS: 0
OAUTH_LOGIN_ATTEMPTS: 0
OPENAI_HTTP_REQUESTS: 0
AUTH_OPENAI_TLS_HANDSHAKES: 0
PROVIDER_INFERENCE_REQUESTS: 0
MODEL_PROMPTS: 0
PI_CREDENTIAL_ACCESSES: 0
CREDENTIAL_ACCESS_COUNT: 0
CREDENTIAL_EXPOSURE: NONE
```

These zeroes are task-command and captured-experiment counts, not claims about
unrelated Docker activity outside the bounded observation.

## Exact next prerequisite

Qualify a checksum-verified task-owned Docker image archive on
`/Volumes/Dev_SSD` as the durable proof-substrate retention anchor, proving
that one disposable image can be saved, locally removed, restored, and
recovered with the expected immutable content/runtime identity without
changing canonical runtime image ownership.

Do not perform archive qualification in this task's proof artifact.

## Validation and documentation follow-through

Only this focused proof artifact is tracked. No application source changed, so
no automated application tests apply. `git diff --check` and
`make docs PYTHON=python3` are required. The known duplicate
`canonical-audit-live-proof-receipt` Makefile-target warnings may be reported
separately from a passing docs validation.
