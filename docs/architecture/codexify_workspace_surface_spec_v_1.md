# Codexify Workspace Surface Spec v1

> Classification: UI/design canon
> Scope: Workspace behavior, layout role, interaction model, persistence model, and view-specific rules for Dashboard, Guardian, and Documents
> Not runtime truth: This document does not define deployment/runtime topology, health surfaces, worker behavior, supported-path truth, or infrastructure or operator-truth guarantees
> Interpretation rule: If this document conflicts with the current runtime KB or short-horizon truth docs, runtime truth wins

## Purpose

Define Workspace as a persistent, summonable working surface that exists across Dashboard, Guardian, and Documents.

Workspace is no longer a passive selected-document viewer.
Workspace becomes a user-owned side surface for:

- **Shelf**: pinned and recent working materials
- **Scratchpad**: fast ephemeral notes and checklists
- **Inspector**: focused preview of the currently selected item

This spec defines the interaction model, layout behavior, component contract, persistence rules, and phased implementation scope for a V1 release.

---

## Product Goal

Codexify should feel like a **cognitive workspace**, not a collection of disconnected viewers.

Workspace must behave like a desk edge or side shelf:

- always available
- easy to dismiss
- persistent across view changes
- useful even when nothing is selected
- lightweight enough to avoid stealing the primary lane

---

## Core Thesis

Current model:

> select item → workspace shows item

New model:

> workspace exists first → selected item may temporarily occupy part of it

This makes Workspace:

- **user-owned**, not selection-owned
- **persistent**, not transient
- **multi-purpose**, not single-purpose
- **ambient**, not dominant

---

## Non-Goals

Workspace V1 is **not**:

- a full file manager
- a second documents view
- a Notion-style all-purpose page builder
- a diagnostics surface
- a mandatory permanently open sidebar
- a general chat sidebar replacement

Diagnostics remain in their existing diagnostic surfaces and are not moved into Workspace.

---

## Supported Views

Workspace V1 appears in three views:

1. **Dashboard**
2. **Guardian**
3. **Documents**

Each view shares the same Workspace shell and state model, but each may define a different default content policy.

---

## Canonical Roles

## 1. Shelf

The Shelf is a persistent holding area for items the user is actively orbiting around.

### Shelf content types

- pinned projects
- pinned documents
- recently viewed documents
- recent generated images
- saved snippets
- quick references
- thread-linked artifacts
- project-linked artifacts

### Shelf behaviors

- items may be pinned and unpinned
- items may be reordered later, but V1 can use stable grouped lists
- items open their primary destination on click
- items may also be inspected without navigating away
- shelf remains useful when nothing is selected in the main surface

### Shelf design intent

This should feel like a **desk edge** or **working shelf**, not a folder tree.

---

## 2. Scratchpad

The Scratchpad is a lightweight, fast note surface.

### Intended use

- jotting a thought
- temporary task list
- saving prompt fragments
- collecting short notes while reading or chatting
- parking rough text before promoting it elsewhere

### Scratchpad constraints

- plaintext or markdown-lite only in V1
- no complex document formatting
- no embedded media editing in V1
- autosave required
- low-friction interaction required

### Scratchpad lifecycle

- persists per project when project context exists
- otherwise persists as a general workspace note
- survives drawer dismissal
- can be cleared explicitly by user

---

## 3. Inspector

Inspector shows the currently selected object in a lightweight contextual preview.

### Supported inspector targets in V1

- document preview summary
- image preview
- project preview summary
- selected thread summary
- selected artifact metadata

### Inspector rules

- inspector content is contextual and temporary
- it must not define the whole identity of Workspace
- dismissing Inspector does not clear Shelf or Scratchpad
- changing selection should update Inspector without collapsing other workspace state

---

## Workspace Modes

Workspace supports four shell states.

## 1. Collapsed

Minimal state.

### Behavior

- Workspace is closed to the side
- a visible summon affordance remains
- no content occupies layout width beyond the collapsed affordance

### Use case

Maximum room for primary content.

## 2. Peek

Narrow shelf-style preview.

### Behavior

- shows a slim version of Shelf only
- intended for glanceable awareness
- no full editor in this state

### Use case

User wants peripheral awareness without opening full Workspace.

## 3. Open

Standard full workspace drawer.

### Behavior

- full width drawer
- tabbed access to Shelf, Scratchpad, Inspector
- standard interactive mode

### Use case

Default working state when Workspace is in use.

## 4. Focused

Temporary elevated mode for deeper interaction.

### Behavior

- same shell, but optimized for one tool
- especially useful for Scratchpad or Inspector
- may slightly expand within token constraints
- should remain dismissible back to Open

### Use case

The user is actively writing or previewing something in Workspace.

---

## Layout Contract

Workspace remains a **card-structured drawer** rather than a freeform panel.

### Structural rules

- Workspace must use the existing card/drawer hierarchy
- Workspace width must be token-driven
- drawer width must not be animated with arbitrary CSS values
- Workspace must not break the shell or create a new layout system
- content inside Workspace may change by tab, but the shell remains stable

### Width behavior

Workspace width is governed by existing workspace width tokens.

Recommended V1 behavior:

- **Collapsed**: icon or narrow rail
- **Peek**: narrow tokenized width
- **Open**: standard drawer width
- **Focused**: wider tokenized width, still subordinate to main content

### Default view behavior

#### Dashboard
- Workspace allowed by default
- ideal home for Shelf-first experience
- right-side drawer pattern is primary

#### Guardian
- Workspace available as optional companion surface
- should not interfere with message lane readability
- Scratchpad and Inspector are highest-value here

#### Documents
- Workspace available as optional secondary card
- Inspector and Shelf are highest-value here
- Scratchpad remains accessible but not dominant

---

## Information Architecture

Workspace V1 uses a tabbed internal model.

### Top-level tabs

1. **Shelf**
2. **Scratchpad**
3. **Inspector**

### Default tab by view

- **Dashboard**: Shelf
- **Guardian**: Scratchpad
- **Documents**: Inspector

### Empty-state policy

#### Shelf empty state
- encourage pinning docs, projects, or artifacts
- offer quick actions to add current selection

#### Scratchpad empty state
- blank ready-to-type state
- optional tiny hint text

#### Inspector empty state
- “Select something to preview” style message
- should not feel like an error

---

## Persistence Model

Workspace state must persist across view navigation.

## State categories

### 1. Shell state

Persist:
- collapsed / peek / open / focused
- last active tab
- last drawer width mode if width presets are used

### 2. Shelf state

Persist:
- pinned items
- recent items list
- grouping preference if added

### 3. Scratchpad state

Persist:
- current text
- updated timestamp
- project binding if present

### 4. Inspector state

Do not treat inspector as durable authored content.
Persist only enough to restore context gracefully if desired.

## Persistence scope

Recommended V1:

- **Global UI state**: shell mode, last active tab
- **Per-project state**: shelf pins, scratchpad body where project context exists
- **Per-thread contextual hints**: optional current inspector target, not critical

---

## Context Binding Rules

Workspace is shared infrastructure with local context sensitivity.

### Project-aware behavior

If a project is active:

- Shelf prioritizes project-linked items
- Scratchpad writes to project-scoped workspace note
- Inspector prefers project-related selections

### Thread-aware behavior

If a thread is active:

- Shelf may show thread-linked docs or artifacts
- Inspector may preview selected thread-linked item
- Scratchpad may expose “promote to thread note” later, but not required in V1

### Global fallback

If no project exists:

- Shelf uses global recent/pinned items
- Scratchpad uses a global workspace note
- Inspector remains selection-driven

---

## Interaction Rules

## Summon / dismiss

Workspace must be summonable from any supported view.

### Required actions

- open workspace
- close workspace
- switch tabs
- move from peek to open
- move from open to focused
- restore previous mode

### Dismissal rules

- dismissal never destroys shelf state
- dismissal never clears scratchpad content
- dismissal only hides the shell

## Add to Shelf

The system should support lightweight “send to workspace” behavior.

### V1 sources

- selected document
- selected project
- selected image/artifact
- current context quick-add action

### Required behavior

- adding an existing pinned item should not duplicate it
- a subtle confirmation is enough
- item should appear in Shelf immediately

## Inspector takeover

Inspector may temporarily become the active tab when the user explicitly previews something.

Rules:

- explicit preview action can switch to Inspector
- passive selection should not aggressively steal focus unless user has chosen Inspector mode
- returning to previous tab should be easy

## Scratchpad editing

Rules:

- typing should autosave
- save should be debounce-based
- the editor must feel immediate
- no modal save flows

---

## View-Specific Experience

## Dashboard

### Role of Workspace here

Dashboard should feel like the **home desk**.

### Priority order

1. Shelf
2. Inspector
3. Scratchpad

### Recommended content

- pinned projects
- pinned documents
- recent generated images
- recent artifacts
- quick-add affordance

### UX note

Dashboard Workspace is the strongest expression of the shelf metaphor.

---

## Guardian

### Role of Workspace here

Guardian should treat Workspace as a **companion surface**.

### Priority order

1. Scratchpad
2. Inspector
3. Shelf

### Recommended content

- scratch text while chatting
- preview selected artifacts or docs
- quick access to thread-linked references

### UX note

Guardian must preserve the primacy of the conversation lane. Workspace should feel supportive, never dominant.

---

## Documents

### Role of Workspace here

Documents should treat Workspace as a **review and staging surface**.

### Priority order

1. Inspector
2. Shelf
3. Scratchpad

### Recommended content

- document metadata or preview
- related/pinned docs
- image/doc artifact preview
- quick notes while reading

### UX note

Documents already has a natural split-view relationship with Workspace. V1 should strengthen that rather than reinvent it.

---

## Component Model

Workspace V1 should be built as a stable shell with swappable internal content.

## Suggested component tree

- `WorkspaceDrawer`
  - shell, width mode, collapse/open behavior
- `WorkspaceTabs`
  - Shelf / Scratchpad / Inspector tab switcher
- `WorkspaceShelfPanel`
  - grouped tile/list content
- `WorkspaceScratchpadPanel`
  - text area + autosave state
- `WorkspaceInspectorPanel`
  - selection preview renderer
- `WorkspaceToggle`
  - summon/dismiss affordance

Optional helpers:

- `WorkspaceEmptyState`
- `WorkspaceQuickAddButton`
- `WorkspaceSection`
- `WorkspaceTile`
- `WorkspaceRecentList`

## Rendering principle

The drawer shell should not know the semantic details of documents, images, or threads beyond a compact rendering contract.

---

## Data Model Guidance

V1 does not require a large new domain model.

A pragmatic shape is enough.

## Suggested storage concepts

### Workspace UI state

- `mode`
- `activeTab`
- `viewDefaultsSeen`

### Shelf item

- `id`
- `type` (`project`, `document`, `image`, `thread`, `artifact`, `snippet`)
- `sourceId`
- `label`
- `metadata`
- `pinned`
- `recency`
- `projectId?`
- `threadId?`

### Scratchpad note

- `id`
- `body`
- `projectId?`
- `updatedAt`

### Inspector target

- transient selection descriptor
- not a primary durable authoring entity

---

## Navigation Rules

Workspace actions should not cause confusing route churn.

### Preferred behavior

- clicking a shelf item may either inspect or navigate depending on affordance
- “open” and “preview” should be distinct when ambiguity matters
- inspector preview should not always change main content route
- route changes should not reset workspace shell state

---

## Accessibility

Workspace must be fully keyboard navigable.

### Required

- keyboard shortcut to open/close workspace
- keyboard navigation between tabs
- focus management on open/close
- visible active states
- proper labeling for tab buttons and drawer controls
- scratchpad usable without pointer interaction

---

## Performance Constraints

Workspace must remain light.

### Requirements

- shell open/close should feel immediate
- shelf items should render quickly
- inspector previews should lazy-load heavier content when needed
- scratchpad autosave must be debounced
- workspace should not trigger heavy fetch storms on every route change

---

## Visual and Structural Constraints

Workspace must obey Codexify token and layout law.

### Required

- tokenized widths, spacing, radii, and colors only
- card hierarchy must remain intact
- no ad hoc panel geometries
- no arbitrary layout wrappers around the primary shell
- no diagnostics leakage into workspace

### Design intent

Workspace should feel like a natural structural primitive inside Codexify, not a special-case sidecar.

---

## V1 Scope

Ship only the minimum coherent experience.

## Included

- Workspace drawer shell
- shelf tab
- scratchpad tab
- inspector tab
- persisted shell state
- persisted scratchpad
- pinned/recent shelf content
- per-view default tab behavior
- summon/dismiss interaction

## Excluded from V1

- drag-and-drop shelf reordering
- rich text editor
- arbitrary embedded widgets
- diagnostics tools
- collaborative workspace state
- multi-note workspace notebooks
- advanced artifact composition
- workspace automation rules

---

## Acceptance Criteria

Workspace V1 is successful when:

1. Users can summon and dismiss Workspace from Dashboard, Guardian, and Documents.
2. Workspace remains useful when no item is selected.
3. Shelf provides glanceable persistent context.
4. Scratchpad feels immediate and survives dismissal/navigation.
5. Inspector previews selected items without taking over the whole experience.
6. Workspace obeys existing card, token, and layout contracts.
7. Guardian remains conversation-first.
8. Documents remains reading/review-first.
9. Dashboard becomes a stronger “home desk” surface.

---

## Recommended Delivery Sequence

## Phase 1
Workspace shell + tabs + local persisted UI state

## Phase 2
Scratchpad with autosave

## Phase 3
Shelf with pinned and recent items

## Phase 4
Inspector renderers for documents, images, projects, and thread-linked artifacts

## Phase 5
View-level tuning for Dashboard, Guardian, and Documents

---

## Final Product Principle

Workspace should feel like:

- a **desk edge**
- a **working shelf**
- a **private jotting surface**
- a **preview bay**

It should not feel like:

- a second app inside the app
- a mandatory sidebar
- a dumping ground for unrelated system features

Codexify wins when Workspace makes the product feel more inhabited, more continuous, and more user-owned without adding structural chaos.
