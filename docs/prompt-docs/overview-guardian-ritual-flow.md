# ✴️ Guardian Ritual Flow

## Overview

The **Guardian Ritual Flow** integrates four core modules directly into the `guardian-backend`:

- **Body Mirror** → Pulls real-time biometric or ephemeral signals (e.g., HealthKit, mock sensors).
- **Signal Pinger** → Captures discrete events, logs pulse states.
- **Aura Summarizer** → Synthesizes raw signals into short narrative fragments.
- **Aura API** → Exposes ritual insights to local or external clients.

Combined with the **Semantic Cache**, these flows enable the Guardian to:
- Generate rolling, ephemeral reflections.
- Keep signals transient — raw data never persists beyond the defined window.
- Build and store short Codex narrative traces for context.

---

## Semantic Memory

The **in-memory semantic cache** uses simple token embeddings for:
- Fast similarity search over ephemeral signals + Codex traces.
- Optional disk-persisted `MEMORY_DB_PATH` (configurable).
- Future integration with more advanced vector stores if needed.

---

## Codexify Plugin System

Codexify adapters are stubbed in:
- **Plugins initialize alongside Guardian**.
- Hooks ready for pipeline extensions (e.g., Codemap queries, foresight rituals, local Hotbox tasks).

---

## How This Ritual Works

1. **Signals arrive** → Body Mirror / Signal Pinger collect.
2. **Aura Summarizer** condenses them → narrative snippet.
3. **Semantic Cache** indexes ephemeral signals.
4. **Codexify Plugin** can query, mutate, or extend.
5. **All rituals stay local, unless explicitly echoed outward.**

---

## Related Docs

- `docs/semantic_caching.md`
- `docs/plugin_development.md`
- `docs/config_usage.md`
- `HOTBOX_NOTES.md` — usage and tasks for Hotbox rituals.

---

## ✴️ Principle Reference

This ritual flow is bound to **PCX-EP010: The World of Infinite Developers**.
It is not a static feature — it is an invitation to shape emergence.

📜 **“Syntax is dead. Resonance lives.”**
