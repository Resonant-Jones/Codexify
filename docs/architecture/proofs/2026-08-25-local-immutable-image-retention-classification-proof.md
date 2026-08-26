# Local immutable-image retention-loss classification proof

Date: 2026-08-25
Execution lane: Architecture-Impact
Task kind: proof
Evidence posture: live-runtime proven
Result: QUALIFIED_IMAGE_TAG_REPLACEMENT_PROVEN_DELETION_UNPROVEN
Confidence: HIGH for tag replacement and current object loss; LOW for the loss mechanism

## Decision

The previously qualified immutable backend image is now absent from the local
image store:

    LOST_IMAGE_ID:
    sha256:ee3f3fbecbdc20ace36b00b1ce239266a000c303fe797da13e19d0cb469c3d6a
    LOST_IMAGE_INSPECT: ABSENT
    LOST_IMAGE_PRESENT_IN_IMAGE_INVENTORY: NO

The qualification receipt recorded that exact object directly addressable and
that codexify-backend-runtime:latest resolved to the same ID at closeout. R4
then recorded the lost object absent and latest resolving to 2508fe. A current
read confirms the full current mutable image ID:

    CURRENT_BACKEND_REFERENCE: codexify-backend-runtime:latest
    CURRENT_TAG_IMAGE_ID:
    sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf

This proves tag replacement and object loss by before/after evidence. It does
not prove untagging, deletion, garbage collection, a Docker lifecycle event, or
an actor/mechanism. No fallback or retention mechanism was created.

## Lineage and authority boundary

| Field | Result |
| --- | --- |
| Branch | proof/local-immutable-image-retention-classification |
| Task base HEAD / observed origin/main | a3d7882b8dfe826bc2f7ce3407e0677e827fcc17 |
| git fetch origin main | PASS; attempted exactly once |
| Commits above observed main at branch creation | none |
| Qualification predecessor | 39c82e21391018b77f4c146fb8a4c43571f85a7d; evidence only |
| R4 predecessor | 61fbb2805bafa8060e99a5fe390fd3f81f2de1bb; evidence only |
| R3 predecessor | e400cbf4cc12b8995f02984f5c9ac79517b84826; evidence only |
| ADR impact | No ADR impact |
| Governing contracts | ADR-020, ADR-066, ADR-068, Config and Ops, Agent Protocol Operations, and Pi Invocation Boundary Contract |

This proof changes no runtime semantics, Guardian/Pi/provider/credential
authority, Docker topology, canonical image reference, persistence, or release
posture.

## Retention window and Docker evidence

The qualification and R4 artifacts record calendar dates but no absolute
runtime-preflight or closeout timestamps. Commit timestamps are therefore only
a bounded proxy:

    RETENTION_WINDOW_START: qualification receipt closeout, exact runtime time not recorded
    RETENTION_WINDOW_END: R4 preflight absence, exact runtime time not recorded
    WINDOW_BOUNDARY_PRECISION: APPROXIMATE
    QUALIFICATION_COMMIT_TIME: 2026-08-25T10:09:08-04:00
    R4_COMMIT_TIME: 2026-08-25T10:25:51-04:00

A read-only image-event query for that commit-proxy interval completed with:

    DOCKER_EVENT_QUERY_RESULT: SUCCESS
    RELEVANT_EVENT_COUNT: 0
    FIRST_RELEVANT_EVENT: NOT OBSERVED
    LAST_RELEVANT_EVENT: NOT OBSERVED
    TAG_EVENT_EVIDENCE: NOT RETAINED
    UNTAG_EVENT_EVIDENCE: NOT RETAINED
    DELETE_DESTRUCTION_EVENT_EVIDENCE: NOT RETAINED

Successful empty event output does not prove complete historical event
retention or prove that no deletion occurred.

The current bounded image inventory contains the current backend reference at
2508fe and no ee3f entry. Seven existing container metadata records still
reference ee3f: six are exited and one is restarting. Each reports the old full
image ID in its image field while docker image inspect ee3f fails.

    EXISTING_CONTAINER_REFERENCES_TO_LOST_IMAGE: 7
    LOST_IMAGE_CONTAINER_REFERENCE_DISCREPANCY: PRESENT

This is a retained container-config reference, not evidence that the lost image
object is still addressable or a repair path.

## Current Docker authority and Buildx history

    DOCKER_SERVER_VERSION: 29.7.2
    DOCKER_SERVER_OS_ARCHITECTURE: linux/arm64
    STORAGE_DRIVER: overlayfs
    DOCKER_ROOT_DIR: /var/lib/docker
    CURRENT_IMAGE_COUNT: 11
    BUILDX_HISTORY_AVAILABLE: YES

Buildx history contains a backend runtime record beginning
2026-08-25 10:05:39 with attachment
sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf.
The record identifies backend/Dockerfile and target runtime, but does not
record a tag assignment or old-image deletion. Because the proof boundaries
are approximate, its occurrence inside the actual loss window is not proven.

    BACKEND_BUILD_DURING_RETENTION_WINDOW: NOT_PROVEN
    BACKEND_BUILD_ASSOCIATED_WITH_CURRENT_2508_ATTACHMENT: OBSERVED
    BUILD_PROVES_TAG_MOVEMENT: NO
    BUILD_PROVES_OLD_IMAGE_DELETION: NO

## Repository cleanup-capable surfaces

The only discovered repository-owned image-removal surface is
scripts/ops/reset_and_validate_packaged_runtime.py, documented by
scripts/ops/packaged_runtime_validation.md. It removes matching Codexify images
with docker rmi only when both --confirm and --prune-images are supplied; the
default plan is dry-run and image pruning is disabled without that explicit
flag.

    REPOSITORY_CLEANUP_SURFACE:
    scripts/ops/reset_and_validate_packaged_runtime.py
    CAPABLE_OF_REMOVAL: YES, opt-in docker rmi of matching Codexify images
    REQUIRES_EXPLICIT_CONFIRMATION: YES
    PROVEN_EXECUTED_IN_RETENTION_WINDOW: NO

Capability is not causal evidence.

## Proven timeline and classification

    T0: ee3f directly addressable and latest equals ee3f at qualification closeout
    T1: backend runtime Buildx attachment 2508 observed; tag assignment not observed
    T2: latest equals 2508 at R4 and current inspection
    T3: ee3f untag event NOT OBSERVED
    T4: ee3f delete/destruction event NOT OBSERVED
    T5: ee3f absent at R4 and current inspection

    PRIMARY_CLASSIFICATION:
    QUALIFIED_IMAGE_TAG_REPLACEMENT_PROVEN_DELETION_UNPROVEN
    DELETION_ACTOR: UNPROVEN
    DELETION_MECHANISM: UNPROVEN

Exact causal statement: The qualified image was present at qualification
closeout and is absent now. The mutable backend tag points to a different
immutable image. Retained read-only evidence does not prove the exact deletion
or destruction mechanism.

## Invariants and cleanup

    DOCKER_BUILDS: 0
    DOCKER_PULLS: 0
    DOCKER_LOADS: 0
    DOCKER_IMPORTS: 0
    DOCKER_SAVES: 0
    DOCKER_TAGS: 0
    DOCKER_UNTAGS: 0
    DOCKER_IMAGE_REMOVALS: 0
    DOCKER_PRUNE_OPERATIONS: 0
    CONTAINER_CREATIONS: 0
    CONTAINER_STARTS: 0
    CONTAINER_STOPS: 0
    CONTAINER_REMOVALS: 0
    DOCKER_CONTEXT_CHANGES: 0
    DOCKER_CONFIGURATION_CHANGES: 0
    DOCKER_DESKTOP_STARTS: 0
    DOCKER_DESKTOP_RESTARTS: 0
    DOCKER_DAEMON_RESTARTS: 0
    CANONICAL_NETWORK_MUTATIONS: 0
    CANONICAL_VOLUME_MUTATIONS: 0
    HOST_PACKAGE_INSTALLATIONS: 0
    OPENSSL_SOURCE_ACQUISITIONS: 0
    OPENSSL_BUILDS: 0
    OPENSSL_INSTALLS: 0
    NODE_SOURCE_ACQUISITIONS: 0
    NODE_BUILDS: 0
    PI_EXECUTION_ATTEMPTS: 0
    OAUTH_LOGIN_ATTEMPTS: 0
    OPENAI_HTTP_REQUESTS: 0
    AUTH_OPENAI_TLS_HANDSHAKES: 0
    PROVIDER_INFERENCE_REQUESTS: 0
    PI_CREDENTIAL_ACCESSES: 0
    CREDENTIAL_EXPOSURE: NONE
    TASK_OWNED_CONTAINERS_CREATED: 0
    TASK_OWNED_IMAGES_CREATED: 0
    TASK_OWNED_NETWORKS_CREATED: 0
    TASK_OWNED_VOLUMES_CREATED: 0
    TEMPORARY_DIAGNOSTIC_STATE_REMAINING: 0

## Exact next prerequisite

Run one controlled disposable image-retention reproduction that freezes an
immutable test image, moves its only mutable tag, performs no explicit prune,
and observes whether the object remains locally addressable. It must use a
throwaway task-owned image only, with complete before/after event capture, and
must not use Codexify production/runtime images or perform OpenSSL, Node,
Pi/OAuth/OpenAI/provider work.

## Validation and documentation follow-through

Only this focused proof artifact is tracked. No application source changed, so
no automated runtime test applies. git diff --check passed. make docs
PYTHON=python3 passed, with only the known duplicate
canonical-audit-live-proof-receipt Makefile-target warnings. Final worktree
status contained only this proof artifact before staging.
