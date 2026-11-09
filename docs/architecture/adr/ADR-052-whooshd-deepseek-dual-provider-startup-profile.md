# ADR-052 — Whoosh'd Gemma and Approved DeepSeek Startup Profile

## Status

Accepted for operator-controlled load observation; not a change to the default
beta release promise.

## Decision

Add `v1-whooshd-deepseek-web` as a named Compose startup profile. It keeps
Whoosh'd's loopback Gemma 12B IT QAT inventory as the only local model, keeps
`local` as the primary provider, and admits only DeepSeek through
`CODEXIFY_EGRESS_ALLOWLIST=deepseek` with `deepseek-v4-flash` as its pinned
cloud model.

The profile starts or kickstarts the existing Whoosh'd LaunchDaemon, verifies
the exclusive `/v1/models` inventory and a bounded concurrent x2 completion
check, and then starts Codexify. It does not install or rewrite LaunchDaemons,
widen the listener, or treat provider health as proof of concurrent inference.
The x2 check is a startup gate; larger load collection remains an operator
measurement.

## Consequences

- Both provider lanes are visible to Codexify while cloud access remains
  allowlisted to DeepSeek.
- The local selector cannot be redirected to another configured local model by
  this profile.
- Secrets stay in the operator-selected env file.
- The profile is candidate/load-observation infrastructure and does not widen
  `docs/architecture/00-current-state.md` release claims.

## Amendment — live DeepSeek model roster (2026-09-15)

The approved DeepSeek cloud lane remains unchanged, including the exact
`deepseek` egress allowlist, per-thread selection boundary, and configured
`deepseek-v4-flash` compatibility default. The model selector now discovers
the authenticated DeepSeek `/models` inventory and exposes its chat-capable
entries. If discovery is degraded, routing retains only the configured default
as a bounded compatibility fallback. This amendment changes catalog/model
selection authority only; it does not admit another provider or establish live
provider execution or release support.

## Amendment — cloud voice egress lane (2026-11-06)

This amendment admits a **cloud voice egress lane** to the `v1-whooshd-deepseek-web`
profile. It does **not** admit a second cloud *LLM* provider: DeepSeek remains
the only cloud inference lane, and the local selector remains unable to be
redirected to another configured local model.

The profile's `CODEXIFY_EGRESS_ALLOWLIST` changes from `deepseek` to
`deepseek,deepgram`. `deepgram` is the voice lane that
[[110-cloud-voice-provider-registration-and-provider-declared-native-format|ADR-110]]
registers, and it is reachable only from the two cloud voice paths — the
provider adapter's construction check and the STT request path. Every other
egress target in the allowlist continues to require its own code path to ask
for it, so adding a voice target grants no other capability.

The egress allowlist is **one value for the whole profile**. Guardian validates
the running allowlist against the profile's provider contract at startup and
raises `LLMConfigError` on a mismatch, so a service that presents a different
allowlist fails to boot instead of degrading. Every deployment of this profile
must therefore present exactly `deepseek,deepgram`:

- the Private Preview overlay (`docker-compose.private-preview.yml`),
- the Whoosh'd dual-provider overlay (`docker-compose.whooshd-deepseek.yml`),
- the tester env template (`.env.tester.example`), and
- the supported profile's own `provider_contract`.

The stock deployment is **not** affected. `docker-compose.yml` does not declare
a cloud posture for the backend or the voice worker, so the stock deployment
stays local-only with an empty allowlist and continues to match the
`v1-local-core-web-mcp` profile contract. A deployment grants the voice lane
explicitly; it is never interpolated from an operator's env file, because an
interpolated value would drift from the active profile's contract.

This amendment does not widen `docs/architecture/00-current-state.md` release
claims, does not qualify default Beta, and does not establish live provider
execution or release support.

## Amendment — DeepSeek Flash model ID (2026-11-09)

The profile's configured default is now `deepseek-flash`, DeepSeek's current
API identifier for Flash. A saved DeepSeek thread with no model or the legacy
`default` marker resolves to the configured DeepSeek default. An explicit
thread model still wins. Provider admission and egress are unchanged.

