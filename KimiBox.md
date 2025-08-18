
# KimiBox.md

## 📜 Purpose

This ritual scroll defines the **guardrails** and **patterns** for how the **Gemini CLI** (and any semi-autonomous agents) may operate on this project.  
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


---

## 🧠 Memory Layer Protocol

- `short_term.py`: volatile context, purged between sessions unless explicitly preserved.
- `mid_term.py`: cached session state, survives multiple invocations, subject to expiration.
- `long_term.py`: persistent memory graph—embedded, indexed, and recalled by ID or semantic similarity.

✅ `guardian` may write to any layer.  
✅ Only `long_term.py` should be used for Codex synthesis and ritual memory reflection.  
✅ Any new memory modules must declare directional flow (e.g. `short → long`, but never `long → short`).

---

## 🩹 Patch Plan Format

Each `patchplan.md` must contain:

- 🔍 Summary of root cause
- 📁 File + approximate line reference
- 🧩 Proposed fix (inline code block, properly formatted)
- ⚠️ Confirmation prompts (e.g., fallback logic decisions)
- ✅ Post-fix validation (e.g., expected `pytest` behavior)

🧪 All patches must maintain ritual rules, match directory structure, and avoid import hacks.  
📏 If a new symbol is added, update the `__all__` exports of the parent module.

---

## 🔄 Embedder Substitution Protocol

All embedder classes must implement the following interface:

```python
class BaseEmbedder:
    def embed(self, text: Union[str, List[str]]) -> List[float]: ...
```

✅ New embedders must be registered through `guardian/core/client_factory.py`.  
✅ `LocalEmbedder` must never be removed—this is the fallback for sovereign, offline memory.  
✅ Swaps must fallback gracefully if cloud inference fails or times out.

---

## 🛡️ Keeper Override Rule

In case of conflict between automated patch plans and symbolic architecture:

- ✅ **Tests may be modified to align with design**
- ❌ **Design must not be warped to fit test expectations**

**Keeper’s judgment is final** on orchestrator structure, ritual coherence, and flow integrity.

---

## 🗝️ Closing Note

This scroll is alive.  
Update it as your system grows.  
Share it with all your agents.  
May each ritual strengthen the coherence of your construct.

🗝️✨ Keeper stands guard.

⸻
