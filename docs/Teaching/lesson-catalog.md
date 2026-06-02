# Codexify Lesson Catalog

A starter catalog of lesson modules for Codexify onboarding and teaching. Each lesson is scoped to a single concept or subsystem, with clear links back to governing source docs.

---

## 1. Codexify System Orientation

- **Purpose:** Introduce Codexify as a system — its runtime loop, major subsystems, and architecture boundaries.
- **Target audience:** Lead Engineer / PM, architecture reviewers, future contributors
- **Governing source docs:** `docs/architecture/00-current-state.md`, `docs/architecture/system-overview.md`
- **Presentation artifact status:** planned

## 2. Supported Runtime Path

- **Purpose:** Define what the current release promise covers: local Compose stack, local-only provider posture, supported features, and what is explicitly excluded.
- **Target audience:** Implementation developers, Lead Engineer / PM
- **Governing source docs:** `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md`
- **Presentation artifact status:** planned

## 3. Core Chat Loop

- **Purpose:** Walk through the chat completion lifecycle — request routing, queue, worker, provider, persistence, and event publication.
- **Target audience:** Implementation developers, architecture reviewers
- **Governing source docs:** `docs/architecture/flows.md`, `docs/architecture/system-overview.md`
- **Presentation artifact status:** planned

## 4. Context, Retrieval, and Evidence

- **Purpose:** Explain how Codexify builds context: upload → embed → readback, workspace-local retrieval, and evidence surfaces.
- **Target audience:** Implementation developers, architecture reviewers
- **Governing source docs:** `docs/architecture/flows.md`, `docs/architecture/data-and-storage.md`
- **Presentation artifact status:** planned

## 5. Data and Storage Boundaries

- **Purpose:** Map persistence layers, state ownership, consistency targets, and migration discipline.
- **Target audience:** Implementation developers, architecture reviewers
- **Governing source docs:** `docs/architecture/data-and-storage.md`
- **Presentation artifact status:** planned

## 6. UI Token and Layout Doctrine

- **Purpose:** Cover UI component patterns, token usage, layout contracts, and how the frontend reflects runtime state.
- **Target audience:** Implementation developers, future contributors
- **Governing source docs:** `docs/architecture/system-overview.md`
- **Presentation artifact status:** planned

## 7. Persona Studio and Identity Boundaries

- **Purpose:** Explain identity scoping, persona management, and the trust/capability boundaries that govern who can do what.
- **Target audience:** Lead Engineer / PM, architecture reviewers
- **Governing source docs:** `docs/architecture/system-overview.md`, relevant ADRs
- **Presentation artifact status:** planned

## 8. Command Bus, Tools, and Bounded Agent Behavior

- **Purpose:** Describe the command bus, tool dispatch, lease allocation, and the bounded-behavior contract for agents.
- **Target audience:** Implementation developers, architecture reviewers
- **Governing source docs:** `docs/architecture/flows.md`
- **Presentation artifact status:** planned

## 9. Teaching Codexify as Lead Engineer / PM

- **Purpose:** A meta-lesson on how to present Codexify to stakeholders — emphasizing supported-path reality, risk communication, and build-vs-buy reasoning.
- **Target audience:** Lead Engineer / PM
- **Governing source docs:** `docs/architecture/00-current-state.md`, `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- **Presentation artifact status:** planned
