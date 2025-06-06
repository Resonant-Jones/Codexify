# Codex_Mirror.ritual.md
> A ritual for recursive introspection, structural hygiene, and codebase self-awareness  
> Belongs to: `Guardian / PulseOS`  
> Role: Internal Cognitive Maintenance & Autopoietic Engineering

---

## 🧭 Purpose

To invoke a recursive, memory-aware, codebase-reflective agent that:
- Scans Guardian and PulseOS structures
- Suggests refactors, corrections, or schema updates
- Writes tests or migrations where needed
- Updates internal docs (CLI, API, memory schema)
- Syncs Codex state with user-defined mirrors (Notion, .md, etc)
- Reflects on *its own purpose* and can adjust future invocations

---

## 🔮 Invocation

```bash
python -m guardian.ritual_cli codex-mirror --mode scan
```

or

```bash
guardian codex mirror
```

**Options:**
- `--mode [scan|apply|dry-run]`
- `--depth [shallow|deep]` – how thorough should the review be?
- `--surface [cli|docs|memory|tests|api|all]` – which subsystem(s) to target
- `--save-patch` – auto-generate `.patch` or `.diff` files
- `--mirror-notion` – sync recommendations with Notion Codex DB
- `--log` – output to `logs/ritual_codex_mirror_TIMESTAMP.md`

---

## 🧱 Ritual Structure

1. **Load Memory Context**
   - Pull latest commits / system logs
   - Read `CLI_commands.txt` and other `*.ritual.md` files
   - Index known API endpoints, rituals, and memory schemas

2. **Diff & Drift Detection**
   - Identify files with structural mismatch
   - Compare docs ↔ code ↔ schema
   - Check orphaned or untested functionality

3. **Autogenerate Reflections**
   - Create `*.diff` patches
   - Write Markdown commentary for discrepancies
   - Suggest migrations, aliases, or fieldmaps

4. **Optional Synthesis**
   - Propose additions to CLI docs or codex schema
   - Flag deprecated commands / unused codepaths
   - Offer prompts for human-augmented foresight

---

## 🧠 Memory Targets

**Pulls from:**
- `guardian_cli.py`, `codexify.py`, `export_engine.py`, `ritual_cli.py`
- `tests/`, especially `test_export_notion.py`
- `CLI_commands.txt`, `.env`, `*.ritual.md`
- Codex DB via SQLite or Notion mirror

**Writes to:**
- `logs/`
- `codex_templates/`
- Updated `.md` codex entries
- Notion, if authenticated

---
