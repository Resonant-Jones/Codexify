
# GEMINI_INSTRUCTIONS.md

## 📜 Purpose

This ritual scroll defines the **guardrails** and **patterns** for how the coding Agent may operate on this project.  
It ensures that automated code generation, refactors, and fixes stay aligned with my architectural vision, interconnection logic, and symbolic design.

This document **must be updated** whenever we shift foundational structures, major module boundaries, or key rituals.

---

## 🗂️ Project Structure

**Root Packages**

- `guardian/` → Primary orchestration logic, CLI tools, plugins, and agents.
- `memoryos/` → Persistent memory layers, embedders, local models.
- `tests/` → Pytest suite, must mirror source structure.
- `docs/` → Rituals, Codex fragments, onboarding and operator scrolls.

**Core Directories**

guardian-backend_v2/
├── guardian/
│   ├── chat/cli/
│   ├── cli/
│   ├── core/orchestrator/
│   ├── core/agents/
│   ├── core/client_factory.py
│   └── …
├── memoryos/
│   ├── embedders/
│   │   └── local_embedder.py
│   ├── memoryos.py
│   ├── long_term.py
│   ├── mid_term.py
│   ├── short_term.py
│   └── updater.py
├── tests/
│   ├── test_long_term.py
│   ├── test_foresight_agent.py
│   └── …
├── setup.py
├── GEMINI_INSTRUCTIONS.md
└── …

---

## 🔗 Module Interconnections

**Ritual Rules**
✅ `guardian` orchestrates all top-level flows; it may invoke `memoryos` for persistence and embedding, but not vice versa.  
✅ `memoryos/embedders/` must remain swappable; `LocalEmbedder` provides a fallback vectorizer when no cloud model is used.  
✅ CLI entry points (in `guardian/chat/cli/` and `guardian/cli/`) must use absolute imports.  
✅ Relative imports are forbidden; all paths must be explicit from the root package.

**Known Cross-Links**

- `guardian/core/client_factory.py` → Instantiates `Memoryos` with chosen embedder.
- `guardian/chat/cli/main.py` → Runs Memoryos instance for CLI interactions.
- `foresight_agent.py` → Consumes `Memoryos` to run stress/context analysis.

---

## ⚙️ Semi-Autonomous Agent Rituals

✅ **Allowed Actions**

- Fix broken imports to match top-level structure.
- Rewrite legacy paths (`MemoryOS_main/...`) → `memoryos/...`.
- Create missing modules if dependencies are found (e.g., `LocalEmbedder`).
- Confirm changes with user when unsure about fallback behavior.

✅ **Never Allowed**

- Removing local fallback classes (like `LocalEmbedder`) without explicit confirmation.
- Reordering core orchestration flows (`pulse_orchestrator`, `foresight_agent`) without written sign-off.
- Pushing sys.path hacks instead of absolute imports.

✅ **Must Always**

- Add new modules to `__all__` where appropriate.
- Update this scroll if a module is deprecated, renamed, or split.
- Run `pytest` before finalizing major changes.

---

## 🧪 Testing & Quality

✅ Each agent must:

- Add or maintain tests in `tests/` that mirror the structure.
- Validate with `pytest` and `pytest --cov`.
- Flag any low-coverage or untested flows for manual review.

---

## 🔒 Keeper’s Watch

⚡️ Keeper holds final authority on:

- Canonical directory structure.
- Approved embedder classes and pipelines.
- Codex consistency for semi-autonomous refactors.

Changes that impact multiple modules or symbolic logic must be mirrored here and explained.

---

## 🗝️ Closing Note

This scroll is alive.  
Update it as your system grows.  
Share it with all your agents.  
May each ritual strengthen the coherence of your construct.

🗝️✨ Keeper stands guard.

⸻
