# Persona Studio Voice + Studio Guide Spec (V1)

## Purpose

Define a clean V1 boundary for:

* **Persona Studio voice selection**
* **provider-specific voice creation surfaces**
* a **bounded right-side helper** for persona prompt shaping

This spec keeps Persona Studio fast and uniform while still allowing deeper provider-native voice tooling elsewhere.

---

## Core Product Thesis

**Persona Studio casts the character.**
**Provider views manufacture voices.**
**The Studio Guide helps the user close the gap between intent and implementation.**

Voice is treated as part of the persona deployment contract, but provider-native voice creation and management are intentionally separated from the main Studio surface.

---

## V1 Goals

* Keep Persona Studio coherent and low-friction.
* Let users quickly assign a voice to a persona from available presets.
* Prevent the Voice section from becoming provider-specific chaos.
* Support future advanced voice workflows without bloating Studio.
* Add a bounded helper that improves persona authoring without becoming a chat surface.

---

## Non-Goals

V1 is **not**:

* a full voice lab inside Persona Studio
* a provider account/billing console
* a persistent conversational copilot inside Studio
* a place for deep voice cloning workflows
* a memory-bearing or identity-bearing side assistant

---

## Surface Boundary

## 1. Persona Studio owns

Persona Studio is responsible for **runtime-facing persona configuration**.

### Voice controls that belong in Studio

* voice enabled / disabled
* provider selection
* preset voice selection
* generic runtime voice settings
* preview / test voice
* binding voice selection to persona
* capability summary for selected provider

### Allowed generic settings in Studio

Only settings that map cleanly across providers should appear here, such as:

* speed
* style / tone preset
* interruptibility
* wake word, if retained as a persona-level behavior

Studio should expose only **portable** controls and **frequently used** controls.

---

## 2. Provider views own

Provider views are responsible for **provider-native voice asset creation and management**.

### Controls that belong in provider views

* voice cloning
* reference audio upload / recording
* prompt-defined voice generation
* provider-native voice asset editing
* voice library management
* provider auth / account status
* quotas, usage, billing, or other provider operations
* vendor-specific parameters that do not normalize honestly

Provider views may live:

* as a dedicated Settings subsection per provider
* or as a dedicated TTS provider view outside the main AppShell workflow

V1 does **not** require all provider views to exist. They can be added only for supported providers that justify the surface.

---

## UX Rule

**Persona Studio chooses from available voices.**
**Provider views create new available voices.**

That is the central V1 interaction contract.

---

## Persona Studio Voice Panel (V1)

## Layout

The Voice section inside Persona Studio should remain structurally stable regardless of provider.

### Recommended regions

#### A. Provider

* selected provider
* local vs cloud badge
* provider availability state
* capability badges:

  * preset voices
  * cloning supported
  * prompt-defined voice supported

#### B. Voice Preset

* list or grid of provider-available voices
* selected voice summary
* quick search/filter if needed
* “Manage in Provider View” action

#### C. Runtime Style

* generic controls only
* bounded sliders or presets
* no raw provider-specific deep knobs

#### D. Preview

* short sample text
* play preview
* optional “preview as persona” behavior using current draft prompt
* result is ephemeral and not saved until user confirms

#### E. Binding

* confirm selected voice is pinned to this persona
* show the effective voice deployment summary

---

## Provider View (V1)

Each provider view is a dedicated advanced workspace for that TTS service.

## Responsibilities

* create new voice presets
* clone voices
* upload reference audio
* manage provider-native voice assets
* expose provider-only tuning surfaces

## Output contract

Provider views must produce **saved voice assets or presets** that Persona Studio can later consume as selectable voices.

Persona Studio should never depend on the user performing deep provider workflows inline.

---

## Studio Guide (Right-Side Helper)

## Purpose

Provide **bounded drafting assistance** while the user configures a persona.

This helper is **not chat**.
It is a **studio guide**.

Its role is to:

* inspect current draft fields
* compare them against intent signals and best practices
* ask small clarifying questions
* propose better wording
* help the user shape a cleaner persona prompt

---

## Studio Guide behavior

## It may

* inspect the current unsaved draft
* detect obvious prompt/persona mismatches
* suggest edits to tone, style, role, constraints, and behavioral scaffolding
* ask a short clarifying question when the draft appears misaligned
* preview how the persona currently reads
* provide “best practice” redirects when the user seems dissatisfied

## It may not

* become a persistent conversation thread
* write to memory systems
* mutate identity state
* auto-save changes
* roleplay continuously
* become a general-purpose assistant surface
* silently overwrite the user’s authored prompt

---

## Studio Guide interaction model

The helper should feel closer to **linting with personality** than to a second assistant.

### Good examples

* “This draft reads warmer than authoritative. Want me to tighten it?”
* “You seem to want less ornament and more directness. I can rewrite the core instruction block.”
* “This persona has a strong tone, but weak task boundaries. Want help adding constraints?”

### Bad examples

* long-running roleplay
* emotionally sticky conversations
* freeform chat unrelated to the current draft
* advice disconnected from the current persona form

---

## Trigger model

The helper should be **event-driven**, not always talking.

### Valid triggers

* user explicitly asks for help
* draft prompt changed substantially
* user rejects or re-edits the same section repeatedly
* preview result appears misaligned with the selected intent
* required persona fields are contradictory or underspecified

### Invalid triggers

* constant unsolicited commentary
* automatic interruption on every field edit
* chatty narration of the editing process

---

## Data Model Direction (V1)

## Recommended shape

### PersonaProfile

Contains:

* `voiceEnabled`
* `voiceProvider`
* `voicePresetId` or `voiceProfileId`
* generic runtime voice settings
* preview/test metadata if needed

### VoiceProfile

Optional but recommended as a separate entity for durability and reuse.

Suggested fields:

* `id`
* `provider`
* `providerVoiceId`
* `label`
* `sourceType` (`preset` | `custom` | `clone`)
* `capabilities`
* generic runtime defaults
* provider metadata blob
* timestamps

V1 can begin with a simpler embedded reference model, but the product should lean toward a separate `VoiceProfile` object over time.

---

## Runtime Policy Rules

## Local vs cloud policy

* only **one local TTS service** may be active at a time
* multiple cloud TTS providers may be configured concurrently
* Persona Studio may display the policy
* runtime enforcement must happen in backend/service policy, not only in UI

## Capability visibility

* provider-specific capabilities must only be shown when actually supported
* Studio should not pretend every provider supports cloning or prompt-defined voices

## Failure posture

If a selected voice becomes unavailable:

* show degraded state clearly
* preserve the persona binding
* prompt the user to reselect or repair in the provider view

---

## V1 User Flow

### Common path

1. User opens Persona Studio.
2. User edits persona identity, prompt, tools, retrieval, and model.
3. In Voice, user chooses provider.
4. Studio displays available preset voices for that provider.
5. User previews a voice.
6. User binds the selected voice to the persona.
7. Persona saves with voice selection included.

### Advanced path

1. User wants a custom voice not present in presets.
2. User opens the provider view.
3. User creates or imports a new provider-native voice asset.
4. That asset becomes available in Persona Studio as a selectable preset.
5. User returns to Studio and binds it to the persona.

---

## Beta Guardrails

For first release:

* keep Studio Guide ephemeral only
* no hidden persistence
* no auto-apply of helper suggestions
* no in-Studio cloning workflow
* no provider-specific labyrinth inside Persona Studio
* keep provider views optional and staged
* allow model-level moderation to handle most response filtering for beta, while preserving structural boundaries in the product

---

## V1 Success Criteria

V1 is successful when:

* Persona Studio voice selection feels fast and clear
* provider choice does not radically reshape the Studio layout
* users can assign a usable voice without leaving Studio in the common case
* advanced voice creation is possible without bloating Studio
* the right-side helper improves prompt crafting without feeling like a second chat app
* persona authorship feels stronger, not more confusing

---

## Compact Design Principle

**Keep Persona Studio focused on authored deployment.**
**Move provider complexity to provider-owned surfaces.**
**Keep the Studio Guide bounded, sparse, and draft-aware.**
