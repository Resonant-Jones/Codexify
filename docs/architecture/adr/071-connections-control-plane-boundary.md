# ADR-071 Connections Control Plane Boundary

**Status:** Accepted

**Proposed amendment:** 2026-11-02 — *delegated external credential custodian*
(see [Proposed amendment](#proposed-amendment-delegated-external-credential-custodian-2026-11-02)).
**Proposed only — not accepted, not operative.**

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

---

## Proposed amendment: delegated external credential custodian (2026-11-02)

> **Status: PROPOSED — pending human acceptance. No operative effect.**
>
> This is a proposal, not an accepted change. Decisions 1–8, the Authority Boundary,
> and the Consequences above remain the accepted decision, unchanged and in force.
> This amendment **extends** them for one named case; it does not supersede, weaken,
> reinterpret, or add an exception to any of them. It authorizes no implementation,
> no catalog change, no new Settings surface, and no release widening. The
> companion amendment to ADR-094 proposes the matching credential-authority
> reconciliation.

### A. The case this amendment admits

A **delegated external credential custodian** is a service that is not part of the
Guardian process and is not governed by the Guardian datastore, but that holds
provider credential material on behalf of a Codexify account and exposes a bounded
execution surface to an authorized adapter. The instance under review is an isolated
OpenConnector v1.9.4 gateway deployed as a separate service, with its own
credential database, its own administrative plane, and its own connection identity
vocabulary.

ADR-071 already draws the lines that matter — aggregation without execution
ownership, configuration without authorization, visibility without implementation,
server-owned and user-scoped credentials — but it assumed every runtime subsystem
lives inside the Codexify process. A custodian does not. It therefore needs an
explicit answer on three points where ADR-071 is currently silent: what the catalog
projects, who owns connection identity, and what "sole credential authority" means
when credential material is held in a separate service's database.

### B. Amendment clauses

**B1 — The custodian is not a catalog entry.** A delegated custodian is a runtime
binding behind ordinary provider entries, never an entry of its own. It therefore
does not add a category, an implementation state, a setup state, an auth method, or
a capability token to `guardian/protocol_tokens.py`, and it does not appear in
`guardian/connections/catalog.py` as a provider. Decision 1 and Decision 7 stand: the
catalog remains a projection over Codexify-owned provider identities, and the
custodian's own action or connection catalog is never projected as though it were
Codexify's.

**B2 — One connection-identity authority.** Guardian owns connection identity. The
custodian's connection identifiers, aliases, and provider-facing setup records are
custodian-internal identifiers, resolved through a Guardian-owned binding, and are
not a second connection-identity authority. Where a custodian exposes several
provider products or modes, they are not separate Connections identities unless
their authority or runtime domains are materially different — the same rule that
already governs provider products in the catalog.

**B3 — Custody is not catalog state and not authority.** The custodian's stored
credential records, connection records, discovery results, and setup state are
delegated custody, projected only as setup state, and they confer **no** execution
authority. A custodian that reports a connection as configured, connected, or
validated has not thereby established that any Codexify account may execute against
it. Decision 3 and Decision 4 stand and are extended by this clause: the projection
of a custodian-backed entry remains the merge of Guardian's own per-user setup state
with the provider's implementation truth, and per-user state is merged at request
time rather than stored in the catalog. A custodian record that no Guardian binding
references is not a Connections fact at all.

**B4 — "Sole credential authority" is clarified, not relaxed.** Guardian's
server-side persistence remains the **sole authority for Codexify account-scoped
authorization and for connection identity**. A delegated custodian may hold provider
credential material — that is custody, and it is delegated — but it holds no Codexify
account authority and grants none. Decision 6 stands: credentials remain
server-owned and user-scoped, the read API never serializes tokens, keys, secrets,
or raw error text, and a custodian's provider credentials remain inside the
custodian's own encrypted store rather than being projected, proxied, or
reconstructed in the control plane. The catalog is never handed a custodian
credential, and the custodian is never handed a catalog-wide grant.

**B5 — Aggregation without execution ownership is extended, not relaxed.** Decision 2
holds for a custodian exactly as it holds for `guardian/channels/` or the provider
registry: the custodian owns its own internal execution surface, Guardian owns
authorization for it, and the two are not merged because they appear behind one
entry. An agent-invocable custodian-backed operation remains a Command Bus command
with Guardian's permission profile, route posture, and bounded outcomes — ADR-024's
outcome vocabulary applies unchanged, and a catalog entry's visibility never
implies that an operation may be invoked.

**B6 — No second control surface.** This amendment authorizes no new Settings
section, page, tab, or AppShell view; no second setup flow; no duplicate mutation
route; and no model-facing custodian API. Decision 1 and Decision 8 stand. The
existing read-only Connections API and the existing backing setup routes remain the
only surfaces, and a custodian's administrative interface is not one of them.

**B7 — Release posture is unchanged.** Nothing here widens the supported-release
boundary. `docs/architecture/00-current-state.md` remains the release truth source,
and a custodian-backed provider entry is a catalog and projection concern only
until a separately qualified runtime implementation exists.

### C. Human acceptance required

**This amendment becomes accepted governing architecture only on explicit human
acceptance.** Until then it is a proposal: Decisions 1–8 and the Authority Boundary
stand alone, no catalog, schema, route, adapter, or UI work may be taken against it,
and the integration program remains held at the gate that precedes implementation.
Proposal status is not approval, and this section must not be cited as an authority
to build.
