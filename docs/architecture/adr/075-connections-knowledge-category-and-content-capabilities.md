# ADR-075: Connections Knowledge Category and Content Capabilities

**Status:** Accepted

**Date:** 2026-08-22

## Context

ADR-071 establishes the Settings Connectors bay as one canonical Connections
control plane over Messaging, Web, and Inference. Its category limitation is
now too narrow for an authenticated Notion connection: Notion is neither a
messaging transport nor an inference provider, and its provider-owned content
repository is not a Web-scale search/extraction surface.

The existing Web capabilities, `search` and `extract`, describe retrieval from
Web resources and Web-provider surfaces. They do not describe searching an
authenticated, explicitly scoped content repository or reading a selected
provider-owned object. The generic legacy `/api/connectors` subsystem is an
implementation family, not a category taxonomy, and the historical
Prefect-era Notion writer does not provide the new runtime authority.

Without a new canonical category and retrieval vocabulary, a Notion entry
would be mislabeled or would overload existing Web semantics. Future Google
Drive and Google Docs work has the same structural need.

## Decision

### Bounded taxonomy extension

Connections gains `knowledge` as its fourth canonical category. This ADR
partially supersedes ADR-071 only where ADR-071 constrains the catalog to
Messaging, Web, and Inference. ADR-071 remains authoritative for one
Connections control plane; aggregation without execution ownership;
configuration, authorization, and health being distinct; catalog visibility
being distinct from implementation; server-owned credentials; and the
read-only `/api/connections` boundary.

`knowledge` classifies external content systems whose primary value is access
to user-authorized structured or semi-structured knowledge. It is a catalog
and presentation classification, never a runtime ownership domain. It does
not imply ingestion, synchronization, indexing, memory writes, health,
authorization, or write access.

Representative future entries include Notion and Google Drive or Google Docs.
Those examples do not establish an implementation or release claim.

### Web versus Knowledge

`web` remains for providers whose primary capability is retrieval or
extraction from Web resources or Web-scale search surfaces. Its existing
`search` and `extract` capabilities retain their current meanings.

`knowledge` is for authenticated or explicitly scoped provider repositories
and applications that expose provider-owned content objects. The distinction
is semantic, not vendor-based: Gemini remains `inference`; Google Chat remains
`messaging`; and future Google Drive or Google Docs entries are `knowledge`.
A provider may therefore have separate Connection identities for materially
different authority and runtime domains. There is no overloaded generic
"Google" Connection.

### Knowledge capabilities

The canonical Connections capability vocabulary gains these future tokens:

- `content_search` — search or enumerate content objects visible through an
  authenticated and scoped knowledge connection, returning only bounded
  discovery metadata sufficient to select an object for a later read. The
  result may include external object identity, title or name, object type,
  parent or container when available, a permitted canonical locator, bounded
  preview or snippet, provider identity, and a pagination cursor. It is not
  arbitrary Web search, durable ingestion, memory mutation, content mutation,
  filesystem access, or authority beyond the established Connection scope.
- `content_read` — read and normalize the content and relevant metadata of one
  explicitly selected object that is accessible through the authenticated and
  scoped knowledge connection. Its normalized result must retain enough source
  identity for downstream provenance. It is not editing, deletion, creation,
  synchronization, durable import, embedding, or memory mutation.

`content_search` and `content_read` do not overload Web `search` and
`extract`. Shared implementation mechanics would not make the capabilities
semantically identical.

`sync_ingest` remains a separate existing concept. A Knowledge Connection does
not receive it merely by being a Knowledge Connection; a future provider may
advertise it only after a separately governed ingestion or synchronization
path exists.

### Ownership and authority

Connections remains a projection and control plane. The canonical shape for a
future Knowledge Connection is:

```text
Connections catalog/projection
        ↓
provider-specific setup and credential seam
        ↓
provider-specific knowledge adapter
        ↓
Command Bus for agent-invocable operations
```

Provider-specific setup and credential validation remain provider-specific.
The provider adapter owns remote API translation. Agent- or user-invocable
operations must pass through existing Guardian and Command Bus authority;
`/api/connections` remains read-only and does not become a generic RPC router.
The legacy `/api/connectors` subsystem is not the Knowledge runtime.

Knowledge credentials remain server-owned and user-scoped. They must not be
serialized through ordinary Connections payloads, retained in browser storage,
or written to logs. Configuration remains distinct from authorization and
health.

`content_search` and `content_read` return external evidence only. They do not
automatically create Codexify memory, infer durable identity, create document
records or embeddings, import an account, or mutate provenance. If an explicit
future persistence path stores retrieved content, that path must retain its
external-source provenance.

### Catalog identity rule

Each catalog entry has one primary category; provider brands do not determine
category. Separate provider products or modes may have distinct entries only
when their authority or runtime domains are materially different. The first
intended identity is `notion` in `knowledge`. The exact decomposition of a
future Google Workspace implementation is deferred.

### Explicitly deferred authority

This decision authorizes no content write capability. In particular,
`content_create`, `content_write`, `content_update`, and `content_delete` are
rejected in this slice. The first canonical Notion implementation is read-only.
Any provider mutation capability needs a later explicit architecture review
grounded in a product need and authority model. The historical Notion database
page writer grants no authority to recreate that behavior.

## Rejected alternatives

- **Put Notion in `web`.** Rejected because authenticated repositories and
  Web search/extraction have materially different scope, authority, and
  provenance semantics.
- **Put Notion in `messaging`.** Rejected because Notion is not a messaging
  execution surface.
- **Put Notion in `inference`.** Rejected because Notion does not own model
  execution.
- **Reuse Web `search` and `extract`.** Rejected because that would collapse
  authenticated repository search and object reads into Web retrieval
  semantics.
- **Reuse the legacy sync connector category implicitly.** Rejected because
  `/api/connectors` is a legacy runtime family, not the Connections taxonomy.
- **Create a Notion-only category.** Rejected because this capability is
  structurally broader than one vendor.
- **Create a generic `productivity` category.** Rejected for now because it
  would blur distinct messaging, calendar, content-repository, and
  collaboration authority domains. `knowledge` names the actual missing class.

## Consequences

The canonical category set becomes `messaging`, `web`, `inference`, and
`knowledge`. Existing Messaging, Web, and Inference behavior is unchanged;
existing Web `search` and `extract` semantics are unchanged.

A subsequent, separate implementation task may add `knowledge` to
`ConnectionCategory`, `content_search` and `content_read` to
`ConnectionCapability`, one canonical Notion catalog identity, and a
read-only Notion provider-specific adapter and Command Bus seam. That task
must preserve this ADR's authority, credential, provenance, and release
boundaries. This ADR does not itself implement Notion, Google Workspace,
tokens, routes, adapters, credentials, setup UI, commands, or live provider
calls.

## Proof and release boundary

This is a documentation and architecture decision. It proves no runtime
behavior, provider credential validity, adapter availability, Command Bus
execution, or live account qualification. It does not widen the Beta release
boundary; `docs/architecture/00-current-state.md` remains the current release
truth source.
