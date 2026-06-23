# Remote Account Access and User Profile Contract

> Classification: architecture contract
> Status: normative
> Scope: docs/contract only

Last updated: 2026-06-22
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/identity-and-runtime-mode.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/config-and-ops.md
- docs/architecture/persona-studio.md
- docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md

## Purpose

This contract defines the semantics for trusted remote account access and user profile behavior in Codexify.

Tailnet or trusted private-LAN access is still remote browser access to a local runtime. It does not change the deployment model into public SaaS, and it does not change the fact that the operator's Codexify machine remains the runtime boundary.

This contract does not implement authentication, networking, UI, database changes, session creation, or any runtime behavior. It only defines the terms, boundaries, and invariants that future implementation slices must satisfy.

## Current Status

### What is true now

- Local Docker Compose remains the supported path.
- Local-only provider posture remains unchanged.
- Auth and exposure configuration already exists through current env/config seams.
- Browser storage may hold auth, session, or API-key material depending on mode.
- Persona and profile configuration exist as a separate concept from account identity.
- A backend User Profile spine now exists for current-user profile metadata.

### What is not yet true

- No dedicated Login page is implemented by this task.
- No User Profile page is implemented by this task.
- No true multi-user runtime claim is introduced by this task.
- No public internet exposure is introduced by this task.
- No Tailnet automation is implemented by this task.

## Terminology

| Term | Meaning |
|---|---|
| `Account` | The durable owner boundary for user-scoped data, settings, and relationships. In multi-user mode, an account is the entity that owns threads, documents, memories, and profile metadata. |
| `Authenticated Principal` | The identity the backend resolves from a successful auth/session check. This is the subject used for request-scoped authorization decisions. |
| `User Profile` | Account-scoped presentation and preference metadata such as display name, avatar/color, and safe inspection fields. It is not persona identity. |
| `Persona Profile` | Runtime preset and behavioral configuration for assistant execution, including prompt, model, tools, retrieval, and similar runtime controls. |
| `Runtime Mode` | Bootstrap-selected runtime posture, currently `single_user` or `multi_user`, that governs how identity and ownership are enforced. |
| `Single-User Mode` | Runtime mode where identity is implicit and the system behaves as if all data belongs to one user. |
| `Multi-User Mode` | Runtime mode where identity is explicit, every request resolves a user, and data access is user-scoped. |
| `Trusted Remote Access` | A remote browser session from a trusted operator or peer over Tailnet/private LAN, backed by explicit app-layer auth and exposure policy. |
| `Tailnet / Private LAN Access` | Restricted network reachability over a private mesh or trusted LAN. This is transport posture, not application auth. |
| `Display Name` | A human-facing label shown in the UI. It is not a canonical ownership identifier. |
| `Canonical User ID` | The stable internal identifier used by the runtime, storage layer, and access-control logic to bind requests and account-owned data. |

## Boundary Model

The following boundaries must stay distinct:

- Account identity
  - The durable owner boundary for data and permissions.
  - This is the scope export/restore and ownership rules must preserve.
- User Profile metadata
  - Human-facing, account-scoped presentation data.
  - Safe for UI use when it does not leak private facts or secrets.
- Persona Profile / runtime preset
  - Assistant-behavior configuration.
  - Governs model, tools, prompt, and retrieval posture.
- Chat/thread/project/document ownership
  - Data residency and authorization boundary for content and artifacts.
  - Must resolve to an account boundary, not a display label.
- Browser session state
  - Cookies, tokens, local storage, and client-side runtime overrides.
  - May be sensitive and must be treated as a risk surface.
- API-key / dev access
  - Operator or developer access path for local and legacy flows.
  - Distinct from authenticated end-user session identity.

The core separation is:

1. Account identity answers "who owns the data?"
2. User Profile answers "how should this account be presented and lightly customized?"
3. Persona Profile answers "how should the assistant behave?"
4. Browser session answers "who is currently authenticated in this client?"
5. API-key/dev access answers "which transport or operator path is allowed to reach the runtime?"

Display names must never be promoted into canonical ownership identifiers.

## Login Surface Contract

The future dedicated Login page may:

- collect credential or session input
- establish an authenticated browser session when remote/session mode is enabled
- show clear local/remote runtime posture
- avoid exposing raw API keys in browser-delivered production-style flows
- avoid silently creating durable identity from display labels

The future dedicated Login page must not:

- bypass backend auth or exposure policy
- infer persistent ownership from arbitrary request payload values
- expose cloud-provider capability
- claim public internet support
- mutate persona identity or memory
- widen release promises

The login surface is an entry point for an authenticated browser session. It is not a shortcut around the backend boundary, and it is not a substitute for operator-managed auth configuration.

## User Profile Surface Contract

Backend implementation note:

- The durable `user_profiles` table and current-user profile API now exist.
- This contract still describes the frontend/presentation surface that must sit on top of that backend spine.
- The frontend User Profile page is still not implemented by this task.

The future User Profile page may own:

- display name
- avatar, color, and local preference metadata
- account-scoped UI preferences
- optional profile description or contact label
- session or account inspection metadata when safe

The future User Profile page must not own:

- persona or system prompt identity
- retrieval policy
- chat memory
- personal facts without explicit review
- provider or model routing
- account export or restore semantics by implication

User Profile is presentation and safe preference state. Persona Profile is runtime behavior. Those surfaces must stay separate even if they share similar labels in the UI.

## Runtime Mode and Ownership Rules

The following invariants apply:

- `single_user` and `multi_user` must remain explicit runtime modes.
- Runtime mode must not silently switch on a live database.
- Multi-user mode requires stable authenticated subject resolution.
- Display names must not be treated as canonical ownership identifiers.
- Retrieval and context assembly must remain scoped to the resolved account boundary once multi-user mode exists.
- Existing single-user local behavior must remain compatible until deliberately migrated.

Interpretation:

- bootstrap selects the runtime mode
- the database must not infer mode by itself
- user-scoped retrieval must follow the resolved canonical user identity
- profile labels are presentation data, not ownership proof

## Tailnet / Private LAN Access Posture

Tailnet/private-LAN access is trusted remote access, not public SaaS exposure.

This posture means:

- the network path is private or operator-trusted
- application-layer auth is still required
- allowed origins, session secrets, auth mode, and exposure mode must be configured explicitly
- session/JWT auth is preferred over browser-shipped API keys for a friend using a remote browser

Tailnet does not replace the app boundary. It only reduces network exposure. The application still has to know who the authenticated principal is and what that principal may access.

## Security and Privacy Invariants

- No raw API key should be shipped to a remote browser in production-style access.
- Session/JWT secrets are operator-managed.
- Browser storage may contain sensitive auth material and must be treated as a risk surface.
- User-owned data, chat content, documents, personal facts, and media remain account-bound.
- Export/restore obligations must preserve account and profile ownership if these fields become durable.
- Trusted remote access must not be described as public internet support.
- Display names, contact labels, and avatars are not security principals.

## Implementation Slice Map

Future work should land in atomic slices:

1. Contract and docs: this task
2. Backend auth/session proof or audit
3. User/account/profile schema audit
4. Dedicated Login page UI
5. Dedicated User Profile page UI
6. Route/auth integration
7. Tailnet/private-LAN operator runbook
8. End-to-end trusted remote access proof

This contract intentionally stops before any of those slices are implemented.

## ADR Impact

Classification: aligned with existing ADR(s), unless the pre-read proves a new ADR is required.

Governing ADRs / contracts:

- [ADR-005 Runtime Mode and Account Boundary Invariants](./adr/005-runtime-mode-and-account-boundary-invariants.md)
- [Account Export + Restore Contract](./account-export-restore-contract.md)
- [Config and Ops](./config-and-ops.md)
- [Persona Studio Architecture](./persona-studio.md)

Brief reason:

This contract does not redefine runtime mode, identity ownership, exportability, or profile semantics. It formalizes the future remote-login and user-profile surfaces so later UI and auth work stays inside the existing account-boundary and persona-separation doctrine.

## Current-Truth Anchors

### What is true now

- Local Docker Compose is the supported path.
- Local-only provider posture remains the active release truth.
- Auth/exposure seams already exist in config and dependency layers.
- Browser storage can already carry sensitive runtime material depending on the selected mode.
- Persona/profile configuration already exists as a distinct concept from account ownership.

### What is not yet true

- No Login page exists as a supported surface.
- No User Profile page exists as a supported surface.
- No multi-user runtime support is being claimed here.
- No Tailnet automation or public internet exposure is being introduced here.

### What this task may assume

- `single_user` and `multi_user` are the only explicit runtime-mode labels used by the account-boundary doctrine.
- Tailnet/private LAN is a trust and transport choice, not a replacement for application auth.
- Display labels must not become ownership identifiers.
- User Profile and Persona Profile must remain separate concepts.

## Invariants

The non-negotiable rules for this contract are:

- trusted remote access is still remote access to a local runtime
- local-only provider posture remains unchanged
- no public internet support claim is introduced
- no code, migration, or runtime change is implied by this docs slice
- no display name may stand in for canonical account identity
- no profile label may mutate persona or memory state
- no raw API key should be shipped to a remote browser in production-style access
- app-layer auth remains required even over Tailnet/private LAN
- browser storage is a risk surface, not a trust boundary
- account-owned data must remain account-bound
- export and restore semantics must preserve ownership if durable profile fields are added later

## Proof Surface

Before anyone claims trusted remote user access works, the future proof set must show:

- backend health surfaces remain green
- configured auth mode is visible and expected
- a remote browser can log in without receiving raw API key material
- the authenticated subject maps to a canonical account or user ID
- thread, document, and retrieval reads are account-scoped
- logout and session expiry work
- local-only provider posture remains unchanged
- no cloud-provider or public-exposure claim is implied

This proof surface is intentionally stricter than "the page loads." It has to prove identity, ownership, and posture together.

## Explicit Non-Goals

- no code changes
- no migrations
- no login UI implementation
- no profile UI implementation
- no Tailnet configuration
- no new runtime support claim
- no public internet exposure
- no provider or routing changes
- no memory or persona mutation

## Notes

This contract is a guardrail for future implementation. It should be read before any work that might blur:

- display labels vs canonical user IDs
- account metadata vs persona configuration
- private transport vs application auth
- browser session state vs durable account ownership

If later implementation work needs to relax any of these invariants, that should be treated as a new architecture decision rather than an implicit extension of this note.
