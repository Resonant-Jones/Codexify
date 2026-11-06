---
tags:
  - architecture
  - adr
  - voice
  - tts
  - stt
  - provider
  - accepted
aliases:
  - ADR-110
  - Cloud Voice Provider Registration and Provider-Declared Native Format
---

# ADR-110: Cloud Voice Provider Registration and Provider-Declared Native Format

## Status

Accepted

## Date

2026-11-05

## Context

Codexify carries **four** distinct voice-provider registries, and choosing the
wrong one is the single largest implementation risk in the voice subsystem:

1. `guardian/voice/runtime.py` — the **voice runtime** provider tuples
   (`SUPPORTED_TTS_PROVIDERS`, `SUPPORTED_STT_PROVIDERS`). This is the agent
   voice service: it owns provider dispatch for both synthesis and
   transcription, and it is the registry of record.
2. `guardian/tts/providers/` — the legacy `TTSProvider` abstract base class.
   This is the **mechanism** the voice runtime calls, not a registry of
   record.
3. `guardian/tts/backends/` — the canonical executable TTS backends. Only
   `qwen3_tts` is registered. These back the `/api/tts/render` render path,
   the `/api/tts/backends` health surface, and voice profiles.
4. `backend/tts_service/` — a separate local-HuggingFace microservice invoked
   by the chat worker over the plugin `/invoke` envelope.

The voice runtime resolved a provider's output container with a hardcoded
provider-name map: `{"elevenlabs", "minimax"} → mp3`, everything else `wav`.
That map is a provider-agnosticism leak in the runtime, and any new provider
had to be added to it by name.

Adding a cloud provider also runs into the cloud posture gates. A provider
classified as `cloud` returns state `degraded` with an empty voice list when
`ALLOW_CLOUD_PROVIDERS` is false; `guardian/core/egress.py` additionally
requires a cloud target to appear in `CODEXIFY_EGRESS_ALLOWLIST`; and the
voice profile `backend_id` carries a CHECK constraint that admits only
`qwen3_tts`, `local_openai_compatible`, and `local`.

## Decision

### 1. A cloud voice provider is registered as a `providers/` adapter

A new cloud provider lands in `guardian/tts/providers/` as a `TTSProvider`
implementation and is registered by name in `guardian/voice/runtime.py`'s
provider tuples. It is **not** added to `guardian/tts/backends/`.

Consequently the executable-backend registry, the `backends/` CHECK
constraint, and the local HuggingFace microservice are unchanged. The existing
contract tests that assert an unknown *backend* id raises
`UnsupportedTTSBackendError` remain valid, because a `providers/` adapter and
a `backends/` entry are different things. A dedicated test now states that
distinction explicitly so it cannot be silently collapsed later.

### 2. A provider declares its own native output container

`TTSProvider` gains a `native_output_format` class attribute, and
`TTSManager.native_output_format()` resolves it. The voice runtime asks the
manager instead of encoding provider names. Providers that predate the
declaration inherit the `wav` default.

The provider-name map is therefore **removed**, not extended. A new provider
does not have to be added to a runtime map to be correct, and the runtime
carries no provider-specific knowledge.

### 3. Voice providers stay behind the existing cloud posture

A cloud voice provider is classified `cloud` and therefore requires
`ALLOW_CLOUD_PROVIDERS=true` **and** an egress allowlist entry. The Private
Preview is the sanctioned cloud lane: it already sets
`ALLOW_CLOUD_PROVIDERS=true` and `CODEXIFY_LOCAL_ONLY_MODE=false`.

The egress allowlist entry is a **profile contract change**, not a runtime
knob. The `v1-whooshd-deepseek-web` profile declares one allowlist string, and
Guardian validates the running allowlist against it at startup, raising
`LLMConfigError` on a mismatch. Admitting the voice lane therefore means the
profile's `provider_contract` changes to `deepseek,deepgram` and **every**
deployment of that profile presents exactly that string — the Private Preview
overlay, the Whoosh'd dual-provider overlay, and the tester env template. This
is recorded as an amendment to
[[ADR-052-whooshd-deepseek-dual-provider-startup-profile|ADR-052]].

The stock deployment is unaffected: `docker-compose.yml` declares no cloud
posture for the backend or the voice worker, so it stays local-only with an
empty allowlist and continues to match the `v1-local-core-web-mcp` contract. A
deployment grants the voice lane explicitly rather than interpolating it from
an operator's env file.

A cloud provider that is registered but not allowed resolves to `degraded` with
an **empty** voice list, exactly as every other cloud provider does. A
provider bound to a voice profile on the Private Preview therefore does not
work on a workstation; that is the posture working as intended, not a defect.

### 4. Binding a cloud provider to a voice profile requires a migration

The `tts_voice_profiles.backend_id` CHECK constraint admits only
`qwen3_tts`, `local_openai_compatible`, and `local`. A cloud provider cannot
be bound to a durable voice profile without a new migration. Because the
migrator reads migrations from the baked image, such a migration requires an
image rebuild.

This decision does **not** add that migration. Provider registration and
runtime selection do not depend on it.

### 5. The Private Preview profile admits the voice route posture

The `voice` route label was quarantined in *every* supported profile, so the
route was never mounted and `/api/voice/*` was unreachable on the Private
Preview. A registered cloud voice provider is therefore not observable on the
Private Preview until the route itself is admitted.

This decision admits `voice` in the `v1-whooshd-deepseek-web` profile — the
shared Whoosh'd Private Preview profile — and **only** there. Every other
supported profile keeps `voice` quarantined, including
`v1-local-core-web-mcp`, which is the default supported profile that
[[069-codexify-beta-runtime-support-boundary|ADR-069]] governs. The admission
therefore does not qualify default Beta and does not weaken ADR-069.

The admission is a freeze-surface change, so it is recorded rather than made
silently: the assertion in `tests/core/test_supported_profile.py` that
previously required `voice` to be quarantined in the Whoosh'd profile is
updated in the same change, and the updated assertion now pins `voice` as
quarantined in the local and tester profiles so the admission cannot widen
past the Private Preview.

## Consequences

- A cloud voice provider is reachable from the existing agent voice surface
  by configuration alone, with no provider-specific logic in the runtime
  dispatch beyond registration.
- The runtime no longer encodes provider names to learn a container. A format
  mismatch cannot be introduced by forgetting to update a map.
- A cloud provider is unreachable unless the cloud posture and the egress
  allowlist both admit it. Enabling a provider on one surface does not enable
  it on another.
- Cloud voice providers remain outside default Beta. The Private Preview
  profile admits the `voice` route posture and no other supported profile
  does.

## Relationship to other ADRs

Extends [[069-codexify-beta-runtime-support-boundary|ADR-069]] without
superseding it, and is independent of
[[109-sandbox-execution-contract-and-kernel-enforced-storage-posture|ADR-109]].
It amends
[[ADR-052-whooshd-deepseek-dual-provider-startup-profile|ADR-052]] only for the
cloud voice egress lane of the `v1-whooshd-deepseek-web` profile. It does not
change the local TTS microservice, the executable-backend registry, or the
voice-profile schema.

## Current-truth boundary

Architecture only. The provider implementation, the runtime registration, the
provider-declared container, the egress registration, the Private Preview
credential wiring, and the Private Preview route-posture admission are
implemented, but no live provider conformance proof exists, and this decision
does not qualify default Beta.
[[../00-current-state|00 Current State]] remains release authority.
