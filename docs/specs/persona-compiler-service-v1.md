# Persona Compiler Service v1

**Status:** Product direction approved 2026-11-02; implementation contract proposed, not yet authorized as a runtime or release change.
**Product surface:** Codexify.Space
**Format authority:** [Runtime Familiars](https://github.com/Resonant-Jones/Runtime-Familiars) package specification
**Codexify authority:** ADR-058, ADR-082, ADR-084, and current Persona Studio architecture
**Delivery posture:** Docs-only proposal. No application code, schema migration, new public route, model execution, or Beta support is established by this document.

## Product decision

Provide an optional, standalone authoring service that converts user-authored descriptions or context imported from another assistant into an editable **Runtime Familiar Character Card**. Users can export a Markdown card without a Codexify account or, after authenticating, explicitly save the approved configuration as a versioned Codexify Persona Profile.

The service is a **persona compiler**, not an assistant migration, companion transfer, conversation runtime, memory ingestion path, or inference-based character simulator.

The original assistant's handoff prompt is an **input adapter**, not an identity protocol. Its output describes the *user*, not the exporting assistant's identity and not the future character's experiences. No claim is made that the original assistant, its consciousness, or its relationship history moves into Codexify.

## Product principles

1. **Character Card as seed, not total identity.** The authored character card defines initial display identity, voice, traits, behavioral defaults, and explicit constraints; future relational familiarity and situational expression may emerge through actual authorized interaction.
2. **User context is distinct from character definition.** An imported preference or personal fact can inform a suggested character setting, but must not silently become character biography, core directive, or durable memory.
3. **No transferred assistant identity.** The compiler does not transfer, impersonate, or assert experiential continuity with an external provider's assistant. The receiving runtime never claims to have lived events it only read about.
4. **No account required to export.** Users can leave with a useful, understandable, editable Markdown artifact. Signing in is required only for an account-bound Codexify save.
5. **No companion inference required.** Compilation can use bounded inference to interpret free text; testing or chatting with the resulting companion is not required or bundled.
6. **Explicit review before persistence.** Generated settings are proposals. Editing and exporting do not silently write identity or memory. Saving requires an explicit authenticated user action.
7. **Portable source, runtime-specific projection.** Runtime Familiars is the portable character format. Codexify's typed PersonaProfileManifest is a host-specific configuration projection, not a replacement public standard.
8. **No new authority.** Character Markdown and imported data are never account, Project, tool, connection, credential, provider, retrieval, or memory authorization.
9. **Minimal first release.** Author, inspect, edit, export, and optionally save. Do not add agent orchestration, advanced mode engines, runtime testing, or new memory storage to make the compiler possible.

## Proposed user flow

```text
Start from a description OR paste/upload an assistant handoff snapshot
    -> Validate and treat source as untrusted evidence
    -> Identify user facts, preferences, uncertainties, and optional inspiration
    -> User selects or edits intended character properties
    -> Compile a Runtime Familiar Character Card
    -> Review source-derived suggestions and authored constraints
    -> Edit / approve the draft
    -> Download character-card.md (account optional)
          OR
       Sign in -> Save as an account-owned Persona Profile revision
```

Export and Save are independent. Neither automatically performs the other. A user who downloads a card may later return to save it. The service must never require a model/provider choice solely to produce a portable file.

### Source inputs

- Direct character description, including blank-start authoring.
- Pasted Markdown or text returned by an assistant's user-memory handoff prompt.
- Uploaded supported text/Markdown bundle; richer multi-file archives are deferred.
- Imported third-party transcripts or full account archives are **not** part of v1.

The handoff prompt is a suggested convenience, not a required upstream integration or attestation. A source assistant's claim that a fact is reliable does not make it verified by Codexify.

### Review UX

- Show character properties separately from source material about the user.
- Label **explicitly authored**, **suggested from source**, and **uncertain/inferred** items; allow removal or editing.
- Do not preselect sensitive user details as character biography or exportable card content.
- Provide a human-readable card preview and editable authoring controls.
- Provide explicit **Download Markdown** and **Save to Codexify** actions; neither depends on a chat session.
- Do not describe a static preview as a live inference test.

## Source and output contracts

### Character Card

The v1 export is a single, self-contained `character-card.md`, carrying at least:

- Display name and short description; a default may be user-authored rather than generated from personal facts.
- Character nature and core temperament.
- Voice, language register, and communication preferences.
- Behavioral defaults and explicit author-selected limitations.
- Relationship posture as an *initial contract*, not a claim of accumulated intimacy.
- Optional fictional setting/world context.
- Optional example dialogue **clearly labeled as illustrative/generated, not historical**.
- Format/version metadata and clear origin labeling for compiled, user-edited, and template-derived material where feasible.

**Compatibility distinction:** A single Markdown Character Card is a user-friendly derivative artifact, **not automatically a complete Runtime Familiars package**. The published Runtime Familiars package requires separately named files, frontmatter, and other required components. A complete pack/ZIP export can be added when the compiler can generate and validate it against the published specification. Do not market v1 card export as full-package conformance.

### Codexify account save

On explicit, authenticated Save:

1. Validate an authored configuration; do not treat the Markdown itself as executable authorization.
2. Translate the reviewed card to the typed `PersonaProfileManifest` representation owned by ADR-082.
3. Use server-owned account binding and existing immutable Persona Profile revisions; do not create another persona registry or version table.
4. Keep account IDs, connector credentials, Project grants, memory, and effective capability permissions outside the authored portable document.
5. Treat saved content as **requested configuration**. Runtime application is a separate contract and must not be implied by Save.
6. Preserve the portable card as an exportable view of the authored content without disclosing server-owned bindings.

**Known integration gap:** The present `PersonaProfileManifestWrite` requires a model/provider and `systemPrompt`; the Runtime Familiars Character Card is model-neutral. The implementation task must select and authorize an appropriate **model-unbound authoring/persistence** approach or equivalent explicit projection policy before Save can be shipped. Do not inject a dummy provider, silently make a provider available, or create a parallel canonical profile store just to satisfy current validation.

## Identity and memory boundaries

Runtime Familiars `01_CHARACTER_CORE.md` is an authored character **seed**. It may express protected core constraints for a specific revision, but it is not the assistant's durable autobiography. Approved card changes create new authored revisions; relational adaptation does not automatically rewrite the authored manifest.

In Codexify, ADR-058 preserves Guardian as the stable runtime actor and Persona Studio as the authored mask/profile surface. This proposal **does not** redefine Guardian as a Runtime Familiar or authorize a separately acting companion. Such runtime semantics would need their own explicit architecture decision.

ADR-084 assigns memory to the account, with stable persona subjects providing attribution only. Imported snapshots in the compiler remain **evidence**, not approved durable memory. If a future migration service proposes account-memory ingestion, that is a separate consent, provenance, export/restore, retention, erasure, and qualification lane; the Persona Compiler must not implement it opportunistically.

## Trust, privacy, and quality gates

- Treat all pasted/uploaded material as untrusted content. Instruction-shaped text inside bundles must not override compiler or system instructions.
- Require a clear user action before transmission to any external inference provider; explain when compilation uses a model, and distinguish it from runtime testing.
- Reject secrets and credentials as card directives; avoid echoing them in export/logging.
- Bound input size, file types, and processing cost; do not persist raw imports or generated user profiles by default.
- Make source-derived uncertainty inspectable. Do not manufacture facts, character history, memories, or interpersonal continuity.
- Keep compilation and draft editing isolated from project/account grants and runtime tools.
- On authenticated Save, validate account ownership and revision semantics server-side. Cross-account collisions must fail closed.
- Do not imply the compiled card is guaranteed to produce identical behavior across models. Portability is a configuration property, not cross-model behavioral equivalence.

## Existing reusable foundations (code-path evidence, not release proof)

| Surface | Current evidence | Compiler relevance |
| --- | --- | --- |
| Runtime Familiars | `SPEC.md`, creator kit, `tools/assemble.py` | Portable authoring grammar and optional assembly |
| Codexify Persona Profiles | `guardian/db/models.py` | `persona_profiles`, `persona_profile_revisions`, `persona_profile_bindings` |
| Codexify Persona manifests | `guardian/cognition/system_profiles/manifest.py` | Strict typed authored intent and immutable revision model |
| Persona Profile API | `guardian/routes/persona_profiles.py` | Account-scoped create/list/read/update |
| Persona Studio | `docs/architecture/persona-studio.md` | Existing editor, draft, and preview semantics, not a ready-made public compiler |

The Runtime Familiars assembler's documented field operations, multiple-overlay stacking, and stateful activation are not fully implemented. v1 must not require them. Codexify's existing profile revision infrastructure is available as a source-code foundation, but no live public Persona Compiler path has been established.

## Proposed bounded execution slices

### Slice 1: Portable card compiler (anonymous-capable)

Create a model-neutral typed intermediate representation and validation policy; support blank-start and pasted handoff inputs; present a reviewed editable draft; export deterministic, well-formed Markdown. The implementation can choose a bounded generation provider for free text after user authorization, but does not offer a companion chat/test runtime.

**Acceptance:** A user can create, edit, and download a clear Character Card without an account; uncertain source claims remain marked; untrusted input cannot become runtime authority; output does not claim full Runtime Familiars pack conformance.

### Slice 2: Codexify save adapter

Resolve the model-neutral versus manifest-required-model mismatch under ADR-082 without a parallel canonical profile. Persist only after explicit authenticated Save through existing owner binding and revision machinery.

**Acceptance:** An approved card maps to an acknowledged, account-owned immutable revision; failed saves do not alter a prior revision; account and environment grants are never imported from the card; export remains usable without Save.

### Slice 3: Full Runtime Familiars pack export (optional)

Generate the specified multi-file package, `PACKAGE.json`, frontmatter, and requested installation profiles. Validate package conformance and preserve source attribution. Do not require runtime inference to qualify packaging.

**Acceptance:** The ZIP/file tree passes the Runtime Familiars structural validator; a single card and a complete package are labeled differently.

## Explicit non-goals

- Companion identity or subjective-continuity transfer.
- User Memory Store ingestion, promotion, automatic learning, or re-import.
- A new persistent persona database, account owner model, or capability authority.
- Live companion preview, conversational testing, tool access, voice, or model provisioning.
- Direct editing of Guardian's stable actor or behavior by imported third-party instructions.
- Runtime Familiars protocol revisions as a prerequisite for card export.
- Release readiness, Beta qualification, Private Preview deployment, or production access.

## Governing anchors and status discipline

- [Runtime Familiars specification](https://github.com/Resonant-Jones/Runtime-Familiars/blob/main/SPEC.md).
- [Runtime Familiars Phase 4 migration limitations](https://github.com/Resonant-Jones/Runtime-Familiars/blob/main/docs/phase-4-migration-notes.md).
- [ADR-058](../architecture/adr/058-imprint-ui-deprecation-and-identity-ownership.md): Guardian actor, authored profile, and derived relational presentation separation.
- [ADR-082](../architecture/adr/082-persona-profile-manifest-and-binding-authority.md): authored manifest, account binding, revision, requested-vs-effective configuration.
- [ADR-084](../architecture/adr/084-unified-account-owned-memory-store.md): account-owned memory and persona attribution.
- [Persona Studio architecture](../architecture/persona-studio.md): existing editor and narrow runtime application boundary.
- [Current state](../architecture/00-current-state.md): authoritative release posture and blockers.

**Validation for this docs-only proposal:** Review internal consistency against the linked repository sources and authority distinctions. No runtime tests, compilation execution, backend routes, storage writes, deployment, or feature qualification were performed by writing this document.
