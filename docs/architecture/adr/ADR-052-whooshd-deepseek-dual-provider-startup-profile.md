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
