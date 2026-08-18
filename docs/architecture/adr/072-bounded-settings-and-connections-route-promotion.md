# ADR-072 Bounded Settings and Connections Route Promotion

## Status

Accepted.

## Date

2026-08-18

## Context

The default local profile already contains mature Guardian-owned identity,
system-prompt, system-document, and read-only Connections catalog seams. They
were still marked `quarantined`, so the frontend could not rely on the
supported-profile health projection and repeatedly probed routes that the
profile intentionally hid. The existing generic connector router is a
different authority surface: it owns connector configuration, authorization,
testing, and synchronization behavior and remains outside the default Beta
promise.

## Decision

1. The `v1-local-core-web-mcp` profile promotes these bounded route labels to
   `enabled`:

   - `imprint` — authenticated Imprint status, proposal, accept, reject, and
     persona operations;
   - `system_prompt` — authenticated system-prompt summary inspection;
   - `system_docs` — authenticated system-document read and toggle operations;
   - `connections` — authenticated, read-only Connections catalog and
     per-entry projection.

2. The Connections catalog receives its own `connections` route label and
   `CODEXIFY_ENABLE_CONNECTION_ROUTES` feature flag. The legacy `connectors`
   label and `CODEXIFY_ENABLE_CONNECTOR_ROUTES` flag remain separate and
   quarantined in the default profile.

3. These surfaces are Beta Bounded / Conditional within the local,
   single-user, API-key-authenticated Guardian boundary. The frontend is a
   projection client; Guardian and the existing identity, prompt, document,
   channel, OAuth, and provider-registry seams retain authority.

4. Startup publishes the effective mounted-route inventory into `/health`
   before clients consume runtime capability state. A frontend may use that
   inventory to stop speculative optional-route probes; it must not infer
   authority from a declared route that is not mounted.

## Authority and safety boundary

- This promotion does not revive the standalone Imprint UI as a separate
  identity owner; ADR-058's Settings-owned identity governance boundary still
  applies.
- Connections catalog visibility does not imply an adapter, setup completion,
  authorization, credential possession, or live health. ADR-071 remains the
  catalog control-plane boundary.
- No cloud provider, OAuth exchange, voice/TTS, federation, generic tool,
  shell/filesystem, or arbitrary connector execution capability is promoted.
- API-key authentication and existing account/user scoping remain mandatory;
  route mounting is not authorization.

## Evidence and remaining proof

The route split, supported-profile posture, startup health projection, backend
route inventory, and frontend capability gate are covered by focused code-path
and test evidence. A fresh authenticated live Compose/browser proof remains a
separate operational check; the existing local runtime model/worker health
blockers are not resolved by this route promotion.

The promotion remains within the existing canonical identity posture assertion
(`codexify:capability:identity`) and ADR-071's Connections control-plane
contract; it does not invent a new Product Architecture Ontology subject.

## Consequences

- `/api/connections` can be exposed without exposing `/api/connectors`.
- Identity and prompt settings routes can be mounted intentionally instead of
  appearing as unexplained 404s.
- `/health` becomes the authoritative route-capability source for the web
  client when startup succeeds.
- Generic connector mutation and sync behavior remains a separately governed
  future promotion.
