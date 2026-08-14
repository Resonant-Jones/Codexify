# ADR-068 Connections Control Plane Boundary

**Status:** Accepted

## Context

The Settings bay already owns a `connectors` tab backed by several separate
runtime subsystems: the generic sync-connector surface
(`guardian/routes/connectors.py`), the messaging channel subsystem
(`guardian/channels/` and `guardian/routes/channels.py`), the canonical
inference provider registry (`guardian/core/provider_registry.py`), the
OAuth persistence schema (`oauth_connections`), and the legacy research
search path. The bay does not yet represent the full desired inventory of
Messaging, Web, and Inference integrations, and no single contract keeps
catalog visibility, implementation truth, setup state, runtime
authorization, and credential ownership distinct.

## Problem Statement

* The bay's current connector registry is substantially narrower than the
  desired Connections catalog.
* A generic frontend OAuth button does not prove a backend OAuth
  authorization handler exists.
* `oauth_connections` persistence does not by itself prove end-to-end
  provider login.
* Listing a messaging platform, web provider, or inference provider must
  not imply an adapter exists, credentials are configured, or the provider
  is authorized or healthy.

## Decision

1. **Aggregation/control-plane surface** — Connections is a single
   canonical catalog behind the existing Settings Connectors bay. It is an
   aggregation and projection seam, never a new execution owner. No new
   Settings section, page, or AppShell view is created.
2. **Runtime subsystems retain execution ownership** — Messaging remains
   owned by `guardian/channels/`; generic sync connectors remain owned by
   the existing connector subsystem; inference execution authorization
   remains owned by `guardian/core/provider_registry.py` and
   supported-profile policy; web execution remains owned by the eventual
   web-tool/provider runtime. The catalog does not merge these domains
   merely because they share one UI surface.
3. **Configuration does not imply authorization** — credential or
   configuration presence (channel config, `oauth_connections` rows,
   provider credential presence) is projected as setup state only.
4. **Authorization does not imply runtime health** — provider-registry
   authorization and live connection health are distinct signals; nothing
   in the control plane fabricates health.
5. **Catalog visibility does not imply implementation** — every entry
   carries a code-proven `implementation_state`; unimplemented entries are
   visibly non-executable and cannot launch setup flows.
6. **Credentials remain server-owned and user-scoped** — the read API
   never serializes tokens, keys, secrets, or raw error text. Only
   frontend-safe OAuth metadata (provider, status, scopes, expiration,
   last-refresh, sanitized error classification) is projected.
7. **One canonical contract** — catalog categories, implementation states,
   setup states, auth methods, and capabilities are canonical tokens in
   `guardian/protocol_tokens.py`; the catalog lives in
   `guardian/connections/catalog.py`; the read-only API is
   `GET /api/connections` and `GET /api/connections/{id}`.
8. **Existing mutation APIs remain authoritative** — the control plane
   adds no duplicate mutation routes. Setup actions link to existing
   backing routes when one exists and stay disabled otherwise. OAuth
   actions are enabled only when a real backend authorization handler
   exists.

## Authority Boundary

* `guardian/channels/` — messaging runtime authority.
* `guardian/routes/connectors.py` — legacy sync connector authority.
* `guardian/core/provider_registry.py` — inference authorization
  authority.
* `guardian/connections/` — catalog and projection authority only.
* Server-side persistence — sole credential authority.

## Consequences

* The Settings Connectors bay can browse Messaging, Web, and Inference
  from one canonical catalog.
* Slack, Discord, and Telegram reflect their real adapter truth; every
  other messaging entry is catalog discovery only.
* Web providers expose Search/Extract capability metadata without
  changing current search behavior.
* Inference entries distinguish configuration from provider-registry
  authorization; DeepSeek is API-key modeled.
* No supported-release claim is widened.

## Rejected Alternatives

* **New Connections page or Settings section** — rejected; the existing
  connectors tab is the single destination.
* **Frontend-local connection lists** — rejected; the catalog must come
  from one backend contract.
* **Reimplementing provider authorization in the catalog** — rejected;
  registry truth wins.
* **Adding a database migration for the projection** — rejected; existing
  schema (channel configs, `oauth_connections`, provider registry) already
  carries the required per-user state.
* **Enabling OAuth buttons without backend handlers** — rejected; dead
  flows must not launch.

## Current Evidence Anchors

* `docs/architecture/connections-control-plane.md`
* `guardian/connections/catalog.py`
* `guardian/routes/connections.py`
* `guardian/protocol_tokens.py`

---

*This ADR documents the control-plane boundary established with the
Connections catalog. It does not implement provider-specific OAuth
exchanges, missing adapters, or any release widening.*
