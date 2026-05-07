---
status: accepted
date: 2026-05-07
---

# ADR-024: Context Command and Active Connector Semantics

## Status

Accepted

## Classification

This ADR is architecture-impacting.

## Governing Docs

- [ADR-022: Guardian Intent Spine and Cross-Surface Control Plane](./022-guardian-intent-spine-and-cross-surface-control-plane.md)
- [Retrieval Router Decision Table](../router-decision-table.md)
- [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)
- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Self-Extending Agent Plugin System](../self-extending-agent-plugin-system.md)
- [Critical Flows](../flows.md)
- [Config and Ops](../config-and-ops.md)

## Context

Codexify needs a clean pattern for connector-backed context retrieval without crowding the composer or collapsing connector use into generic chat history.

The current architecture already separates several related concerns:

- retrieval posture
- provider/runtime truth
- command-bus or tool execution
- connector authorization and scope
- chat transcript integrity

What it does not yet have is one canonical interaction contract for composer-triggered connector use. Without that contract, the system can blur together:

- a standing retrieval posture
- a connector that is connected but idle
- a connector that is attached in the UI
- a connector that is actually consulted for a turn
- a one-off tool crossing event

This ADR defines that missing doctrine without claiming any live `/obsidian` or broader connector runtime is already implemented.

## Decision

Codexify uses **Context Commands** to open or invoke connector-backed context lanes.

The canonical pattern is:

- Context Commands open or invoke connector-backed context lanes.
- Active connectors are authorized and available until disconnected.
- Active connectors are not automatically consulted on every turn.
- Guardian may consult active connectors when the request strongly implies their domain.
- Explicit slash commands force or bias connector consultation for a turn.
- Connector use should be observable after the fact through trace, chip, or diagnostic surfaces, but not theatrically narrated unless permission, ambiguity, failure, or trust requires it.

Context Commands attach request metadata or context directives. They must not permanently pollute authored message text.

Connector evidence is additive to the normal thread/project conversation spine unless a future governed mode says otherwise.

## Canonical Terms

| Term | Canonical meaning |
|---|---|
| Connector | A durable, authorized bridge to an external or semi-external context or action surface such as Obsidian, GitHub, Drive, Discord, or an MCP-backed capability. |
| Connection | The active authorization and transport relationship that allows a connector bridge to exist. |
| Active connector | A connector that is connected and presently eligible for turn-scoped consultation. |
| Attached connector | A connector surfaced in the current thread, project, composer, or session context for visible use. |
| Context Command | A turn-scoped directive that opens, biases, or invokes connector-backed context for the current request. |
| Invocation | The intentional request to consult or act through a connector during a turn. |
| Tool call / crossing event | One runtime crossing event through the connector bridge, often the implementation-level event that produces returned evidence. |
| Context bundle | The additive block of connector-derived evidence, metadata, or normalized fragments attached to the normal conversation context for a turn. |
| Portal | A conceptual UI/session term for a connector entry surface or session wrapper; it is not an authority model. |
| Admin user | The human user or account holder who grants, scopes, or revokes connector authority. |
| Guardian requester/interpreter role | Guardian's role inside the system: interpret the request, apply policy, and ask for bounded crossings. Guardian is not the owner of connector authority. |

## State Semantics

The connector lifecycle is a set of related states, not a forced linear pipeline.

| State | Meaning | Notes |
|---|---|---|
| `connected` | The connector bridge exists and is authorized. | This is a bridge state, not proof of consultation. |
| `available` | The connector is connected and eligible under current policy and scope. | Available does not imply automatic use. |
| `attached` | The connector is selected or surfaced in the current UI/session context. | Attachment is visible state, not usage proof. |
| `invoked` | The current turn explicitly or implicitly requested connector consultation. | Turn-scoped unless a future governed feature pins it longer. |
| `consulted` | A tool call or equivalent crossing event occurred and connector evidence entered the context. | This is the proof-bearing use state. |
| `dismissed` | The connector was eligible but intentionally not used for the current turn. | Dismissal may be explicit or policy-driven. |
| `disconnected` | The connector bridge is no longer active, scoped, or authorized. | No new consultation should occur until reconnected. |

Key rules:

- `connected != consulted`
- `attached != consulted`
- `invoked` is turn-scoped unless explicitly pinned by a future governed feature
- `available` still does not mean automatic consultation

## UI Doctrine

- The composer slash-command palette is the preferred low-clutter invocation surface.
- Active context chips are the preferred visible representation of connector use or attachment.
- Vault, repo, or server switching belongs in connector configuration or a chip/modal selector, not as permanent composer clutter.
- V1 should support a narrow `/obsidian` style context command before broader folder, note, or vault targeting.
- Future nested command structure may support folders, notes, tags, vaults, repos, servers, and MCP namespaces.

## Sources Menu Boundary

- The Sources menu controls standing internal retrieval posture.
- Context Commands control turn-scoped connector invocation.
- Obsidian should be additive context, not a replacement for Thread or Project chat history.

This boundary keeps retrieval posture stable while allowing connector-backed evidence to enter a turn explicitly.

## Runtime and Authority Boundary

- Software maintains connector bridges.
- Guardian requests crossings.
- The host runtime checks policy, connection, scope, and approval state.
- User/admin grants, revokes, or scopes authority.
- Guardian receives bounded results or bounded failure states.
- Guardian does not need metacognition of approval UI state or backstage auth ceremonies.

This preserves the separation between authority, enforcement, and request interpretation.

## Tool-Call Relationship

- Connector use may be implemented as a tool call.
- Product semantics should still present connector and context language to users.
- Developer and diagnostic surfaces may expose tool-call details.
- Normal conversation surfaces should expose concise evidence of connector use, not raw invocation machinery.

The runtime event can be implementation-level while the product vocabulary stays connector-facing.

## Failure and Denial States

The canonical bounded outcomes for a connector invocation or consultation are:

| Outcome | Meaning |
|---|---|
| `success` | The connector returned usable bounded evidence or completed the requested action. |
| `denied` | Policy, approval, scope, or authority blocked the request. |
| `unavailable` | The connector was not reachable, not connected, or not eligible for this turn. |
| `needs_configuration` | The connector exists but lacks required setup, scoping, or target selection. |
| `timed_out` | The crossing did not return within the allowed time. |
| `failed` | The crossing or tool execution failed for a non-recoverable reason. |

These are outcome classes, not connector-lifecycle states.

## Non-Goals

- No implementation of `/obsidian`
- No slash-command palette implementation
- No connector dashboard implementation
- No MCP runtime implementation
- No auth or OAuth implementation
- No live proof claim
- No change to release readiness

## Consequences

- Future Obsidian, GitHub, Discord, Drive, and MCP connector work can align to one doctrine instead of inventing local semantics.
- Connector behavior gains a stable vocabulary before UI or runtime implementation.
- The current architecture can avoid conflating sources, tools, connectors, and model autonomy.
- Context retrieval remains additive to the thread/project spine instead of replacing it.

## Proof Surface

Future implementation tasks must prove:

- Slash-command text is parsed into metadata or directives rather than persisted as authored prose.
- Thread and Project context remains included when connector context is added.
- Connector use is observable in trace or metadata.
- Active connector availability does not force automatic consultation on unrelated turns.
- Explicit command invocation causes connector consultation when available.

This ADR itself does not prove live connector behavior.

## Links

- [ADR Index](./adr-index.md)
- [ADR-022: Guardian Intent Spine and Cross-Surface Control Plane](./022-guardian-intent-spine-and-cross-surface-control-plane.md)
- [Retrieval Router Decision Table](../router-decision-table.md)
- [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)
- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Self-Extending Agent Plugin System](../self-extending-agent-plugin-system.md)
