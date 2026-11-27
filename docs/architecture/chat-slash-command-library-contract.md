# Chat Slash Command Library contract

## Ownership and authority

Guardian owns the canonical discovery metadata in [guardian/slash_commands.py](../../guardian/slash_commands.py). The published inventory contains 18 identities covering the 14 chat intents and five composer controls. React WebUI, Desktop/Tauri, and Scout SwiftUI can use the same read model from their configured Guardian endpoint when they implement consumption.

Both GET routes are mounted on the existing chat router and use its account-session and request-scope dependencies. Local installs follow the existing local authentication policy. Remote and Private Preview requests follow the existing account-session policy. Successful responses send `Cache-Control: private, no-store`. The catalog contains user-facing metadata only. Discovery performs no chat writes, connector probes, tool calls, or task dispatch. These routes are omitted from OpenAPI because the internal Command Bus builds its raw manifest from OpenAPI operations.

Discovery grants no execution authority. Chat request validation uses the registry's chat-intent IDs and accepts the same exact IDs as before. Aliases are for discovery. Client intent fields and retrieval hints still pass through the existing request and execution policies. Connector consultation remains turn-scoped under [ADR-024](./adr/024-context-command-active-connector-semantics.md). Codex Entry retains its explicit draft-first flow and separate save action under [ADR-029](./adr/029-codex-entry-command-first-draft-flow.md). Runtime exposure and qualification remain governed by [ADR-069](./adr/069-codexify-beta-runtime-support-boundary.md).

## Version 1 wire format

`GET /api/chat/slash-commands/manifest` returns the full collection in ascending canonical-token order. `GET /api/chat/slash-commands/search?q=<query>&limit=<n>` returns a ranked subset using the same envelope and command records.

| Field | Type | Meaning |
| --- | --- | --- |
| `schemaVersion` | integer | Wire contract version, currently `1`. |
| `manifestRevision` | string | Opaque content identifier for the full catalog, also returned by search. |
| `commands` | array | Command records. An unmatched search returns an empty array. |

| Command field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable command identity. Chat intent IDs retain their current spelling. |
| `token` | string | Unique canonical token including its leading slash. |
| `label`, `description` | strings | Display text. |
| `aliases`, `keywords` | arrays of strings | Aliases resolve to command identities. Keywords contribute only to search. |
| `scaffold` | string | Suggested text to insert. |
| `interactionModes` | array of strings | Supported interaction types for this identity. |
| `effects` | object or null | Declarative `intentKind` and `retrievalHint` for chat intents. Null for control-only commands. |
| `availability` | string | `available`, `unavailable`, or `unknown`. |
| `availabilityReason` | string or null | Bounded reason code. Version 1 currently emits `eligibility_not_evaluated`. |

`manifestRevision` is `sha256:<hex>` over compact UTF-8 JSON containing `schemaVersion` and the ordered `commands`, with object keys sorted. It changes with canonical published metadata and is independent of request time, account, and search parameters. Clients compare it as an opaque value. Any future account-specific availability projection is reconciled independently of the catalog revision.

## Identity, interaction modes, and search

- `chat_intent` describes an existing chat intent. The IDs are `image`, `sunburst`, `flare`, `thread`, `doc`, `project`, `workspace`, `profile`, `flow`, `secure`, `connect`, `obsidian`, `codex_entry`, and `help`.
- `composer_control` describes a client-side control with options supplied by its existing client context. The IDs are `project`, `provider`, `model`, `mode`, and `retrieval`. Discovery supplies metadata only.
- `/project` is a single record with both modes. `/repo` resolves to it. The legacy React catalog also listed `workspace` as a project alias. The backend reserves `/workspace` for its canonical `workspace` identity and omits that alias from `project`. An existing chat submission with `commandId: "project"` and legacy raw text is still accepted on the same terms.
- Canonical tokens are reserved before aliases are indexed. Duplicate IDs, duplicate normalized canonical tokens, and alias collisions fail catalog validation. An alias that shadows a canonical token must be removed. Ambiguous aliases must be resolved in the catalog before publication.

Search requires `q` and accepts up to 128 characters. The result limit defaults to 10 and accepts integers from 1 through 25. Out-of-range values return HTTP 422. Search trims whitespace, strips leading slashes, and folds case. An exact canonical token or alias returns its single owner. Otherwise, canonical token prefixes rank first, then alias prefixes, then keyword exact or prefix matches. Each group follows ascending canonical-token order. A command appears only at its best rank. Empty, slash-only, and unmatched queries return an empty collection. For example, `/obs` returns `/obsidian` and `/workspace` returns `/workspace`.

## Availability and compatibility

Recognition means the identity exists in the catalog. `available` requires authoritative evidence of present eligibility. `unavailable` requires authoritative evidence of a denial by current policy or capability state. `unknown` means current evidence is insufficient. The initial projection is `unknown` for every record because these reads do not evaluate the account, thread, turn, or client context needed for eligibility. An Obsidian listing establishes no connector configuration or access. Any future account-bound evidence must be resolved from authenticated authority. Query parameters and caller-provided identity hints confer none.

Clients should decode interaction modes independently and ignore unknown mode values for activation. A client can display a record without offering an action when it implements none of the record's modes. For implemented modes, clients continue to use the existing action checks. Treat `unknown` as missing eligibility evidence. Metadata updates require an installed handler to become actionable. Clients should check `schemaVersion` before interpreting the payload and treat unsupported versions as incompatible.

The future client refresh contract is to fetch the manifest after authentication, after reconnecting to Guardian, and after any endpoint or account change. Keep any in-memory snapshot scoped to the endpoint and authenticated account. Discard the previous snapshot immediately on an endpoint or account change, and discard late responses for the previous context. Use `manifestRevision` to invalidate derived command lists or search results when canonical metadata changes. Reconcile availability each time against the fresh account-scoped response, even when the revision matches. A stale snapshot provides no evidence of current eligibility.

This backend slice provides the registry, validation alignment, manifest, and search. Account-specific eligibility resolution, client consumption and automatic refresh, event publication, and client subscriptions are deferred. Repository tests establish the read contract. Live deployment and client interoperability require separate evidence.

## Image command reconciliation

`/image` (alias `/imagine`), `/sunburst`, and `/flare` retain the installed
image-generation flow. Selecting a catalog entry only fills the draft; sending
an explicit image request uses the image adapter rather than chat inference.
A bare image command opens the existing prompt form. General command selection
remains draft-only. Discovery does not probe providers or authorize spending.
The image catalog supplies provider/model compatibility and configuration
availability; generation retains server-side account scope, feature, egress,
and bounded-spend restrictions. Unavailable providers fail without fallback.
This reconciliation is source/test evidence, not Preview deployment proof.

Image sends require a current, successfully loaded discovery entry with an
implemented interaction mode; missing/failed discovery and explicit denials
fail closed. `unknown` does not confer execution eligibility. The image provider
catalog must positively admit the requested provider/model, then the server
rechecks account and dispatch policies. Ordinary prose, including passive
visual preferences, never triggers the image adapter; explicit slash submission
or confirmation in the image form is required.
