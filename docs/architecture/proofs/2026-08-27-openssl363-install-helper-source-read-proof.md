# Trace the OpenSSL install-helper source-read boundary

**Date:** 2026-08-27
**Result:** `BLOCKED`
**Primary classification:** `OPENSSL_HELPER_TRACE_TOOL_UNAVAILABLE`
**First causal boundary:** tracer qualification, before OpenSSL execution
**Evidence posture:** pre-execution blocker; no current helper/source-read runtime result
**Confidence:** High for the observed package transaction and stopping decision; no confidence claim is made about the unobserved helper boundary.

## Scope and stopping decision

This task was authorized to reproduce exactly one container-local OpenSSL 3.6.3 installation and trace the already identified install helper through source resolution, source read/transfer, destination write, and replacement. The task explicitly requires stopping if obtaining the required tracer materially changes libc, Perl, make, compiler, linker, or other OpenSSL build/runtime dependencies.

The exact qualified image did not contain `strace`. The predecessor package request was then applied to the disposable writer so the tracer could be obtained. That transaction upgraded four existing runtime packages:

```text
dpkg       1.22.21       -> 1.22.22
libc-bin   2.41-12+deb13u1 -> 2.41-12+deb13u3
libc6      2.41-12+deb13u1 -> 2.41-12+deb13u3
liblzma5   5.8.1-1       -> 5.8.1-1+deb13u1
```

This materially changes the qualified runtime/dependency posture. The packet’s fail-closed rule therefore applies:

```text
OPENSSL_HELPER_TRACE_TOOL_UNAVAILABLE
```

The writer was stopped immediately. No OpenSSL source was acquired, extracted, configured, built, or installed in this run. No helper invocation was executed, and no source-read boundary was inferred.

## Authority and current truth

The proof branch was based on the freshly observed `origin/main` after the one required fetch. The predecessor proof object was verified and read directly from Git before this preflight.

| Evidence | Value |
| --- | --- |
| Branch | `proof/openssl363-install-helper-source-read` |
| Task base HEAD | `321ea07c19ade38fb898ff8c2a449499c04bf3d9` |
| Observed `origin/main` | `321ea07c19ade38fb898ff8c2a449499c04bf3d9` |
| Immediate predecessor | `927eed965f7655e8564ec4bf4052d380e8abb3c7` |
| Destination-differential predecessor | `590e48133` |
| R5 predecessor | `721977af58cf2400539d209f60f2b228c93fbf16` |
| Archived-substrate predecessor | `9a319684b52444d87cb7c9b1e0fda31dd6e5ae29` |
| Required predecessor object | `git cat-file -e ...^{commit}` passed |
| Required fetch | one `git fetch origin main`, passed |

The direct predecessor proof records the earlier container-local corruption and the concrete `/usr/bin/cp` helper sequence. That evidence remains historical predecessor evidence; it is not substituted for the unrun current helper-input trace.

## ADR impact and governing contracts

**ADR impact:** `No ADR impact`.

This is a bounded diagnostic proof over disposable state. It changes no Guardian authority, runtime protocol, queue/worker semantics, provider routing, persistence, supported profile, Docker topology, canonical artifact ownership, or release boundary.

The governing material read for this task was:

- `docs/architecture/00-current-state.md`;
- `docs/architecture/adr/adr-index.md`;
- `docs/architecture/README.md`;
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`;
- `docs/architecture/adr/066-campaign-engine-runtime-recovery-contract.md`;
- `docs/architecture/adr/068-campaign-engine-live-role-execution-contract.md`;
- `docs/architecture/config-and-ops.md`;
- `docs/architecture/agent-protocol-operations.md`;
- `docs/architecture/pi-invocation-boundary-contract.md`;
- `docs/architecture/agent-tool-loop-contract.md`;
- `docs/axis-node/README.md` and `docs/axis-node/invocation-protocol.md`.

The ADR index confirms ADR-020 as the Guardian-mediated coding-agent execution contract, ADR-066 as the Campaign Engine runtime-recovery contract, and ADR-068 as the bounded live-role execution contract. None authorizes this proof to create runtime behavior or widen release claims.

## Qualified substrate preflight

The exact immutable image was inspected read-only before any writer activity:

| Field | Observed value |
| --- | --- |
| Image ID | `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf` |
| Platform | `linux/arm64` |
| Archive | `/Volumes/Dev_SSD/codexify-proof-images/backend-openssl-substrate-2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf.tar` |
| Expected archive SHA-256 | `689a3cb56fc688cca5ecd55ba946aa63bbdbea3dee2d42139606269c27a7df1c` |
| Archive load count | `0` |
| Mutable `latest` use | `0` |
| Docker context | `desktop-linux` |
| Docker endpoint | `unix:///Users/chriscastillo/.docker/run/docker.sock` |
| Docker version | client/server `29.7.2` |
| Docker platform | Linux/arm64 |

No archive load, image pull, image build, retag, prune, Docker context change, daemon restart, or Docker Desktop restart occurred.

## Single writer and package transaction

Exactly one writer was created from the immutable digest:

| Field | Observed value |
| --- | --- |
| Writer container ID | `b2a9d4051d2eb4a6daafbe6cbe24f073ccac758fe6f619447a72313a802cd9aa` |
| Writer container count | `1` |
| Continuation writer count | `0` |
| Name | `codexify-openssl-helper-source-read-TRY9PW` |
| Entrypoint | `/bin/sh` |
| Command | `trap "exit 0" TERM INT; while :; do sleep 3600; done` |
| Mount | `/Volumes/Dev_SSD/codexify-openssl-helper-source-read.TRY9PW` to `/work`, read-write |
| Application entrypoint/services | none |
| `.env`, Pi/provider credentials | none |

The established dependency request was executed once inside this disposable writer:

```text
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  perl perl-modules-5.40 build-essential binutils ca-certificates \
  ninja-build python3 strace
```

`apt-get update` and the package transaction both exited 0. The transaction reported 4 upgrades and 51 new packages. The requested diagnostic tool became available as `/usr/bin/strace` version `6.13+ds-1`, and the established Perl gate passed:

```text
FILE_SPEC_FUNCTIONS_OK
```

However, `libc6`, `libc-bin`, and `liblzma5` were upgraded, and `dpkg` was upgraded as part of the same transaction. This is precisely the prohibited material posture change. No source, configure, build, install, or trace command followed.

The host package-install count was `0`; the package transaction was confined to disposable writer state.

## OpenSSL and helper evidence not reached

Because the tracer qualification failed closed, the following current-run operations were not attempted:

| Required operation | Current-run result |
| --- | --- |
| Official source acquisition | `0`; not attempted |
| Source checksum verification | not attempted in current run; predecessor authority is `243a86649cf6f23eeb6a2ff2456e09e5d77dd9018a54d3d96b0c6bdd6ba6c7f1` |
| Configure | `0`; not attempted |
| Build | `0`; not attempted |
| Build-tree source freeze | not reached |
| Generated recipe mapping | not reached |
| Helper source argument/resolution | not reached |
| Helper source open/read/transfer | not reached |
| Container-local `make install_sw` | `0`; not attempted |
| Bind-target install | `0` |
| Destination write/rename analysis | not reached |
| Post-helper source integrity | not reached |
| Immediate destination integrity | not reached |

The predecessor’s exact semantics remain the authority for any future rerun: official OpenSSL 3.6.3 source, `linux-aarch64 shared`, prefix `/work/prefix/openssl-3.6.3`, and one `make -j2` followed by one traced container-local `make install_sw`. They were not reconstructed or re-executed here.

## Invariant ledger

| Invariant | Result |
| --- | --- |
| `QUALIFIED_IMAGE_IDS_USED` | `1` |
| `QUALIFIED_ARCHIVE_LOADS` | `0` |
| `WRITER_CONTAINER_COUNT` | `1` |
| `CONTINUATION_WRITER_COUNT` | `0` |
| `OPENSSL_SOURCE_ACQUISITIONS` | `0` |
| `OPENSSL_CONFIGURES` | `0` |
| `OPENSSL_BUILDS` | `0` |
| `OPENSSL_INSTALL_SW_ATTEMPTS` | `0` |
| `BIND_TARGET_INSTALL_ATTEMPTS` | `0` |
| `DIRECT_COPY_WORKAROUND_ATTEMPTS` | `0` |
| `ALTERNATE_INSTALL_HELPER_ATTEMPTS` | `0` |
| `OPENSSL_SOURCE_PATCHES` | `0` |
| `OPENSSL_GENERATED_BUILD_FILE_PATCHES` | `0` |
| `OPENSSL_HELPER_PATCHES` | `0` |
| `NODE_SOURCE_ACQUISITIONS` | `0` |
| `NODE_BUILDS` | `0` |
| `NODE_EXECUTIONS` | `0` |
| `PI_EXECUTION_ATTEMPTS` | `0` |
| `OAUTH_LOGIN_ATTEMPTS` | `0` |
| `OPENAI_HTTP_REQUESTS` | `0` |
| `PROVIDER_INFERENCE_REQUESTS` | `0` |
| `MODEL_PROMPTS` | `0` |
| `CREDENTIAL_ACCESSES` | `0` |
| `DOCKER_PRUNE_OPERATIONS` | `0` |
| `DOCKER_CONTEXT_CHANGES` | `0` |
| `DOCKER_DAEMON_RESTARTS` | `0` |
| `DOCKER_DESKTOP_RESTARTS` | `0` |
| `CANONICAL_NETWORK_MUTATIONS` | `0` |
| `CANONICAL_VOLUME_MUTATIONS` | `0` |
| `HOST_PACKAGE_INSTALLATIONS` | `0` |
| `APPLICATION_SOURCE_EDITS` | `0` |
| `RELEASE_CLAIM_CHANGES` | `0` |

## Cleanup and retained inputs

The writer was stopped normally with a ten-second timeout. Its disposable policy removed the container; a post-stop container listing returned no matching container. The only task-owned scratch root was removed:

```text
/Volumes/Dev_SSD/codexify-openssl-helper-source-read.TRY9PW
```

The qualified immutable image, retained archive, and checksum receipt were not removed or modified. No canonical Docker network or volume was mutated.

## Supported causal statement and next prerequisite

Supported statement:

```text
The required helper trace could not be qualified without materially changing
the exact image's libc/dpkg/liblzma dependency posture, so this run stopped
before OpenSSL execution and does not classify the helper source-read boundary.
```

The earlier `INSTALL_HELPER_WROTE_ZERO_PAYLOAD` result remains valid predecessor evidence, but this run adds no narrower causal boundary and does not contradict it.

Exact next prerequisite:

```text
Obtain a fresh exact qualified writer with the required syscall tracer already
present, or a diagnostic package transaction proven not to upgrade or replace
libc, Perl, make, compiler, linker, or other OpenSSL build/runtime dependencies;
then rerun the source-read-boundary task from preflight without changing the
OpenSSL operation scope.
```

No workaround, source-location differential, Node work, Pi work, OAuth work, OpenAI request, provider inference, or architecture change is authorized by this blocked result.

## Validation and documentation follow-through

This is a docs-only blocked-proof artifact. Automated application tests do not apply. The required repository validation is `git diff --check` followed by `make docs PYTHON="$PY"` using the selected Python interpreter. Only this proof file is authorized for tracking.
