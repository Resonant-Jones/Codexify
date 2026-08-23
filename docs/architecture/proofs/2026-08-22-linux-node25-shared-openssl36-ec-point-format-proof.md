# Linux Node 25 shared-OpenSSL 3.6.3 point-format reproduction

## Result

**PASS — diagnosis only.**

```text
PRIMARY_REPRODUCTION_CLASSIFICATION:
  LINUX_SHARED_OPENSSL36_REPRODUCES_HOST_POINT_FORMATS
CONFIDENCE: HIGH
BUILD_LAYER_INTERPRETATION:
  LINUX_CAN_REPRODUCE_HOST_TLS_EXTENSION_POSTURE
```

An unmodified Linux/arm64 Node v25.9.0 source build, dynamically linked to an
unmodified task-built OpenSSL 3.6.3 shared-library prefix, emitted the same
normalized local ClientHello structure as the installed successful Homebrew
Node.  In particular, both emitted:

```text
ec_point_formats: [uncompressed]
ec_point_formats_payload_length: 2
```

This rules out Darwin as necessary for the observed TLS-extension posture. It
does not prove that this extension causes an OAuth outcome, that OpenAI uses it
for fingerprinting, that this disposable runtime is OAuth-safe, or that any
canonical runtime should change.

## Scope and authority boundary

- Execution lane: architecture-impact
- Task kind: credential-free TLS runtime reproduction proof
- ADR impact: **No ADR impact**

The work was aligned with ADR-020, ADR-066, ADR-068, the Pi Invocation
Boundary Contract, Agent Tool Loop Contract, Runtime Protocol Token Contract,
and Agent Protocol Operations. It changed no Guardian authority, credentials,
Pi runtime, canonical worker image, canonical Node/OpenSSL runtime, Compose
topology, release claim, or provider behavior.

## Lineage and drift gate

| Field | Value |
| --- | --- |
| Base / direct prerequisite | `d2014ef59b3bed902f9917256fb073c27679af94` |
| Proof branch | `proof/linux-node25-shared-openssl36-ecpoint` |
| Observed `origin/main` | `c90d3ca3ac3e5d4e70563fbc96e31a06e8cabb36` |
| `git fetch origin main` | PASS, attempted once |
| Relevant runtime/network drift | NONE |

The focused current-main review found no material change to the worker image,
Node or Pi materialization, worker network behavior, or OAuth/provider
contracts. A static Pi-readiness regression test was the only related-path
change and did not alter the proof assumptions.

## Disposable build provenance

The private mode-0700 diagnostic root, sources, build outputs, prefix,
collector, and one named build container were task-owned only. The selected
existing local Linux build image was:

```text
base image: codexify-backend-runtime:latest
immutable image ID / digest: sha256:f180559736892d2a1c0e1e11e1a79d1ff3d1bd0fe05499f6c84ea0919204c01a
distribution: Debian GNU/Linux 13 (trixie)
architecture: arm64 / aarch64
libc: 2.41
compiler: GCC 14.2.0
```

No canonical image was rebuilt or modified. Ordinary compiler dependencies and
Ninja 1.12.1 were installed only inside the disposable container.

| Official artifact | SHA-256 | Integrity |
| --- | --- | --- |
| OpenSSL 3.6.3 source | `243a86649cf6f23eeb6a2ff2456e09e5d77dd9018a54d3d96b0c6bdd6ba6c7f1` | PASS |
| Node v25.9.0 source | `d55d77187039d4cd85c732f76838f44e3be552054473459dfa9cc0eb611ea664` | PASS |

OpenSSL was configured without a source patch as:

```text
./Configure linux-aarch64 shared
  --prefix=<task-owned>/prefix/openssl-3.6.3
  --openssldir=<task-owned>/prefix/openssl-3.6.3/ssl
```

`openssl version -a` under the task-owned library path reported OpenSSL 3.6.3,
target `linux-aarch64`. Node's supported shared-library flags were inspected
from `./configure --help` and used without a source patch:

```text
./configure --ninja
  --prefix=<task-owned>/prefix/node-v25.9.0-shared-openssl36
  --shared-openssl
  --shared-openssl-includes=<task-owned>/prefix/openssl-3.6.3/include
  --shared-openssl-libpath=<task-owned>/prefix/openssl-3.6.3/lib
```

The Make backend produced malformed generated archive-response metadata on
this Debian toolchain. Node's supported Ninja backend was therefore used. A
four-job attempt was stopped by a resource kill in one V8 compiler process;
the same unmodified graph completed under a stable two-job recovery. The
direct Node installer then installed the already-built binary without invoking
Make again. These were disposable build-environment adjustments, not source
or runtime configuration changes.

## Runtime identity and local ClientHello result

Dynamic linkage resolved only to the task-owned OpenSSL prefix:

```text
libcrypto.so.3 => <task-owned>/prefix/openssl-3.6.3/lib/libcrypto.so.3
libssl.so.3    => <task-owned>/prefix/openssl-3.6.3/lib/libssl.so.3
CUSTOM_NODE_SHARED_OPENSSL_LINKAGE: PASS
```

| Property | Custom Linux runtime |
| --- | --- |
| Node | `v25.9.0` |
| OpenSSL | `3.6.3` |
| undici | `7.24.4` |
| platform / architecture | `linux` / `arm64` |
| `node_shared_openssl` | `true` |
| `tls.DEFAULT_ECDH_CURVE` | `auto` |
| `crypto.getCurves()` | 82; prime and binary-field curves present |

The local raw-TCP collector used the prior proof's SNI
`codexify-tls-probe.invalid`, ALPN `h2, http/1.1`, and TLS 1.2–1.3 bounds. It
normalizes/discards randoms, session IDs, GREASE, key-share bytes, cookie, and
PSK material; none were retained. The installed host reference first
reproduced successfully.

| Runtime | Safe structural fingerprint | EC point formats |
| --- | --- | --- |
| Installed host Homebrew Node25 | `213bd622362e550afcce` | `[uncompressed]`, length 2 |
| Custom Linux Node25/shared OpenSSL 3.6.3 | `213bd622362e550afcce` | `[uncompressed]`, length 2 |
| Official Linux Node25/bundled OpenSSL 3.5.5 (prerequisite) | `b374a148e9de856ad447` | `[uncompressed, ansiX962_compressed_prime, ansiX962_compressed_char2]`, length 4 |

```text
HOST_REFERENCE_REPRODUCED: PASS
CUSTOM_VS_HOST_ONLY_DIFFERENCE_EC_POINT_FORMATS: NO (no normalized structural difference)
CUSTOM_VS_OFFICIAL_LINUX_ONLY_DIFFERENCE_EC_POINT_FORMATS: YES
CUSTOM_VS_OFFICIAL_LINUX_DIFFERENCE: ec_point_formats only
```

The custom and host vectors share TLS version offers, all 52 cipher suites in
order, extension names/order, supported groups, signature algorithms, ALPN,
and key-share algorithms. Against official Linux Node25, the point-format
payload remains the only structural difference.

## Next prerequisite

> Qualify the disposable Linux Node25/shared-OpenSSL3.6.3 runtime as a safe Pi
> OAuth candidate by proving generic HTTP serialization, pinned Pi v0.72.1
> token-request semantics, and TLS-only auth.openai.com negotiation, with zero
> OAuth attempts.

That gate was not performed here.

## Zero-sensitive tuple and cleanup

```text
OAUTH_LOGIN_ATTEMPTS: 0
OPENAI_OAUTH_AUTHORIZATION_REQUESTS: 0
OPENAI_OAUTH_TOKEN_REQUESTS: 0
PROVIDER_INFERENCE_REQUESTS: 0
MODEL_PROMPTS: 0
CODING_TOOL_INVOCATIONS: 0
GUARDIAN_LIVE_INVOCATIONS: 0
CAMPAIGN_ENGINE_INVOCATIONS: 0
MINIMAX_INVOCATIONS: 0
HOST_PI_CREDENTIAL_ACCESSES: 0
WORKER_PI_CREDENTIAL_ACCESSES: 0
CANONICAL_CREDENTIAL_MUTATIONS: 0
CANONICAL_WORKER_IMAGE_CHANGES: 0
CANONICAL_NODE_RUNTIME_CHANGES: 0
NODE_SOURCE_PATCHES: 0
OPENSSL_SOURCE_PATCHES: 0
CREDENTIAL_EXPOSURE: NONE
TASK_OWNED_CONTAINERS_REMAINING: 0
TEMPORARY_BUILD_STATE_REMAINING: 0
```

Only this proof artifact is tracked. No current-state, ADR, Dockerfile,
Compose, canonical Pi/Node/OpenSSL, provider-support, or release document was
changed.
