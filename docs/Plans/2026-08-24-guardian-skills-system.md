# Guardian Skills System — Design Sketch

> **Status:** Implemented (2026-08-28). `guardian/skills/` — contracts,
> discovery, loader, registry, exposure — plus `guardian/tests/skills/` and a
> `skills` segment seam in `guardian/cognition/modular_prompt_builder.py`.
> Not yet wired into a runtime call path: no module imports `guardian.skills`
> yet, and `modular_prompt_builder` gains the `skills_block` parameter without
> a caller passing it. This document remains the design record; §1 describes
> the pre-implementation baseline.
> **Grounding:** every seam below was verified against the working tree on
> 2026-08-24 (branch `main`, ahead 1 / behind 43).
> **Precedent:** `guardian/skills/marketing/SKILL.md` already exists as inert
> data — the convention is started, the system is not. This document is the
> system that makes it real.

---

## 1. What "deployed" means in Codexify today (honest answer)

**Nothing deploys skills today.** Verified by grep: no module in `guardian/`
imports `guardian.skills`, and the marketing skill's rules have never touched a
prompt. What exists:

| Piece | Location | Status |
|---|---|---|
| A skill-shaped file | `guardian/skills/marketing/SKILL.md` + `templates/` | Inert data; nothing loads it |
| Tool registry (HTTP-command-backed) | `guardian/tools/registry.py` | Active; loads from command-bus manifest |
| Command bus manifest | `guardian/command_bus/manifest.py` (`build_manifest(app)`) | Active |
| Chat tool exposure gate (Stage 2I/2K) | `guardian/tools/chat_exposure.py` | Active; **fixed allowlist** of health + repo-search |
| System prompt budgets | `guardian/cognition/modular_prompt_builder.py` (`PromptBudgets`, `estimate_tokens`) | Active |
| Markdown-into-prompt precedent | `guardian/cognition/system_docs/store.py` | Active (DB-backed, user-scoped) |
| Plugin precedent (code extension) | `guardian/plugins/plugin_base.py` | Active |
| YAML parsing | `guardian/config_loader.py` (pyyaml 6.0.3, in `pyproject.toml`) | Active |

The key architectural fact: **Guardian's tool registry is HTTP-command-backed
today** — a tool is derived from a FastAPI route through the command-bus
manifest, and `chat_exposure.py` is a deliberately narrow fixed allowlist
(health + repository search only). There is no seam for a *prompt-backed*
tool. The skills system is that seam.

---

## 2. Design goals

1. **Standard-first.** Consume the Agent Skills open standard (agentskills.io)
   — `name` + `description` + markdown body, `skill-name/SKILL.md` directory
   layout, optional `scripts/`, `references/`, `assets/` subdirs that load on
   demand. Tolerate-and-ignore unknown frontmatter. This is what makes
   migrating into Codexify trivial: any skill already written for Claude Code,
   Codex, Cursor, or Gemini CLI works unmodified.
2. **Scan, discover, ingest.** The loader scans the standard locations other
   harnesses use, so a user who already has skills on disk gets them in
   Codexify with zero migration steps.
3. **No private dialect.** Don't adopt the leaked snapshot's private fields
   (`hooks`, `shell`, inline `!`backtick`` shell execution). Use the snapshot
   as the shape reference for mechanics (progressive disclosure,
   untrusted-source restrictions) — never as code to port.
4. **Prompt-backed tools.** Expose each skill as both (a) ambient knowledge
   (a roster line in the system prompt) and (b) a callable tool with a tiny
   schema whose execution reads the body + referenced files. No server-side
   code execution from skill bodies.
5. **Progressive disclosure.** Startup cost = frontmatter only (~100 tokens
   per skill); body loads only on activation; `references/` and `assets/`
   only when the body calls for them. Matches both the open standard and
   `PromptBudgets` discipline.
6. **Trust & safety boundary.** Local skills are trusted for prompt
   injection. Imported/MCP-sourced skills are untrusted content, injected
   verbatim or not at all — never executed. Execution authority stays with
   the sandbox/permission layer (§6).

---

## 3. Component sketch

```
guardian/skills/
├── __init__.py            # public API: get_skill_registry()
├── contracts.py           # SkillRecord, SkillSource, TrustTier pydantic models
├── loader.py              # SKILL.md scanner/parser (frontmatter + body)
├── discovery.py           # multi-root scan: .agents, .claude, .cursor, .codex,
│                          #   .gemini, ~/.agents, guardian/skills, plugins
├── registry.py            # in-memory registry + warm cache + invalidation
├── exposure.py            # system-prompt injection (frontmatter roster) +
│                          #   skill activation body block
├── tool_surface.py        # skill_invocation ToolSpec → SkillRecord adapter
└── tests/
    ├── test_loader.py
    ├── test_discovery.py
    └── test_exposure.py
```

**`contracts.py`** — canonical record:

```python
class TrustTier(str, Enum):
    LOCAL = "local"           # guardian/skills/, project dirs — trusted
    IMPORTED = "imported"     # scanned from other harnesses — trusted read
    UNTRUSTED = "untrusted"   # MCP or remote — verbatim injection only

class SkillRecord(BaseModel):
    skill_id: str             # stable: f"{source_key}:{skill_name}"
    name: str                 # frontmatter name or dir name
    description: str          # frontmatter description
    when_to_use: str | None   # optional routing hint
    body_path: Path           # SKILL.md location
    base_dir: Path            # skill root (for references/, assets/)
    trust: TrustTier
    source_key: str           # discovery root that found it
    frontmatter_tokens: int   # est. via estimate_tokens()
    body_tokens: int          # est. via estimate_tokens()
    mtime_ns: int             # cache invalidation
    raw_frontmatter: dict     # unknown fields preserved, ignored
```

**`loader.py`** — parse `skill-name/SKILL.md`: split YAML frontmatter from
body on `---` delimiters. Extract standard fields, preserve unknown fields in
`raw_frontmatter` (tolerant reading), reject on malformed YAML with a logged
warning and skip. Never write back.

**`discovery.py`** — ordered scan roots (first wins, dedupe by resolved path
via `os.path.realpath`):

```python
SCAN_ROOTS = [
    ("project:.agents",    ".agents/skills"),      # neutral ecosystem default
    ("project:.claude",    ".claude/skills"),      # Claude Code compat
    ("project:.cursor",    ".cursor/skills"),      # Cursor compat
    ("project:.codex",     ".codex/skills"),       # Codex CLI compat
    ("project:.gemini",    ".gemini/skills"),      # Gemini CLI compat
    ("user:.agents",       "~/.agents/skills"),    # user-global
    ("user:.claude",       "~/.claude/skills"),    # user-global Claude
    ("user:.codex",        "~/.codex/skills"),     # user-global Codex
    ("project:native",     "guardian/skills"),     # Codexify-native
    ("plugin:*",           "<plugin_dir>/skills"), # plugin-contributed
]
```

**`registry.py`** — `SkillRegistry` mirroring `ToolRegistry`'s shape:
`load()`, `list()`, `get(skill_id)`, `get_by_name(name)`, plus
`get_frontmatter_roster()` for the exposure layer. Cache with mtime
invalidation; rescan trigger on route call. DB persistence of discovered
skills is observability, not v1.

**`exposure.py`** — two artifacts:

1. **Roster block** (always in system prompt, budgeted): `name — description`
   lines, one per skill, gated by a new `skills_max_tokens` budget knob
   (default ~1000). Ends with the standard instruction: "To activate a skill,
   invoke the `skill_invocation` tool with its name."
2. **Activation block** (on tool call): body + inline references. Reads
   `references/` files listed or linked in the body, resolves relative paths
   against `base_dir`, truncates per `references_max_tokens` (default ~4000).
   Never executes anything.

**`tool_surface.py`** — the prompt-backed tool. This is the new seam in
`guardian/tools/`: a `ToolSpec` whose `input_schema` is
`{"skill": <name>}` and whose execution path does NOT go through the command
bus — it's an internal invoke (`default_internal_invoke_schema` already
exists for this shape). Distinguishing property: `tags: ["skill"]`. Execution
= read body + inline references; never executes skill code. Arguments:
`{"skill": "<name>", "context": "<optional user context>"}`.

---

## 4. How a skill flows end-to-end

1. Startup (or route-triggered rescan): `discovery.scan_all_roots()` →
   `loader.parse()` → `SkillRegistry.load()`. Malformed skill files log a
   warning, never crash startup.
2. Prompt assembly: `system_prompt_builder` calls
   `skills.exposure.roster_block(user_id, project_id)` → injects the roster
   after system docs, within `PromptBudgets`.
3. Model sees roster, calls `skill_invocation(skill="marketing")` →
   `tool_surface` resolves the `SkillRecord` → returns the activation block
   as the tool result (body + resolved references, token-truncated).
4. Agent proceeds with the skill's guidance in context. If the skill's
   instructions require execution (e.g. "run `make test`"), the agent uses
   the normal sandboxed tools — skill *content* and skill *execution* stay
   cleanly separated.

The marketing skill works immediately under this design: roster line →
tool call → body + `templates/` resolved as references.

---

## 5. Route surface (minimal)

| Route | Purpose |
|---|---|
| `GET /api/skills` | List discovered skills (name, description, trust tier, source, tokens) |
| `POST /api/skills/rescan` | Trigger discovery rescan (mtime-based cache bypass) |
| `GET /api/skills/{skill_id}/body` | Fetch activation block (for UI preview / debugging) |

Admin/owner-scoped. The skills system is a read-only scanner over trusted
local dirs — routes are observability, not authority.

---

## 6. Trust, security, and the two-state-machine rule

- **No execution from skill content.** `scripts/` in a skill directory is
  data we can point the agent at (a *suggestion* it may run through the
  normal sandboxed tool flow), but Guardian never executes it directly.
  Execution authority stays with the existing sandbox + approval flow. This
  mirrors the snapshot loader's refusal to execute inline shell from
  untrusted sources, but goes further: we don't execute inline shell from
  *any* skill content, because our agent has a real sandbox with a real
  permission system.
- **Untrusted tier = verbatim injection or nothing.** MCP-sourced skills
  inject verbatim under strict budgets or are skipped. Never executed,
  never interpreted.
- **Two-state-machine rule (CLAUDE.md):** discovery/registry state is
  startup-or-rescan state (provider-ish); the roster block and activation
  block are per-request prompt state. A tool call producing an activation
  block is per-request state and must not write registry state. The rescan
  route must not assume enqueue = executed.
- **Path safety.** All paths resolved under each scan root; no `..`
  escapes; references resolved relative to `base_dir` and confined to it.
- **Budget discipline.** Roster + activation blocks respect
  `PromptBudgets`; a huge skill body can't blow the prompt budget.

---

## 7. Open design decisions (yours to make)

| # | Decision | Options & notes |
|---|---|---|
| 1 | Injected context vs. callable tool vs. both | Recommend **both** (roster + tool). The tool call is what makes activation explicit and observable. |
| 2 | Canonical Codexify-native path | `guardian/skills/` (recommended, marketing already there) vs `.codexify/skills/` |
| 3 | Scan other harnesses' dirs by default? | Recommend **yes** — that's the "migration is pie" feature. Con: reads dirs outside the repo. Make it a config flag, default on. |
| 4 | Roster budget | New `skills_max_tokens` PromptBudgets knob, default ~1000 (~10 skills at ~100 tok). |
| 5 | DB persistence of discovered skills | Not v1. Cache is in-memory + mtime. Persist later for observability. |
| 6 | `skillify` equivalent | Defer. Turning a session into a skill is a great v2. |
| 7 | MCP-sourced skills | Defer. The snapshot's `mcpSkillBuilders` is the shape reference when we get there. |

**Decisions locked 2026-08-24:** #1 → both; #2 → `guardian/skills/`; #3 →
**yes, outside-repo scanning default-on** (user confirmed — "kind of
expected" for a personal workspace system); #4 → default 1000,
configurable; #5 → no DB in v1; #6/#7 → deferred.

---

## 8. Rollout sequence (small blast radius)

| Phase | What | Verification | Status |
|---|---|---|---|
| 1 | `contracts.py` + `loader.py` + tests: parse the marketing skill, a malformed one, one with unknown frontmatter | `pytest guardian/tests/skills/` | ✅ Done 2026-08-25 — 22 tests |
| 2 | `discovery.py` + tests: tmp dirs with `.agents/skills`, `.claude/skills`, symlinked-duplicate detection | `pytest` | ✅ Done 2026-08-25 — 14 tests; live scan found 11 Codex skills in `~/.codex/skills/` + native marketing |
| 3 | `registry.py` + cache invalidation tests | `pytest` | ✅ Done 2026-08-25 — 12 tests; cache self-heals on index corruption |
| 4 | `exposure.py` roster block + budget tests | prompt snapshot tests | ✅ Done 2026-08-28 — 15 tests; `PromptBudgets` gained `skills_max_tokens` + `build_system_prompt` gained the `skills` segment (regression-verified) |
| 5 | `tool_surface.py` + `chat_exposure` extension for the skill tool | tool manifest + exposure tests | ⬜ Next |
| 6 | Routes (§5) + frontend skills list (later) | route tests | ⬜ |

Note: `guardian/tests/core/test_provider_registry.py` has 2 pre-existing
failures unrelated to skills (verified by stashing changes and re-running).

---

## 9. Relation to the leaked snapshot

Shapes only, never code: frontmatter parsing → record, directory scan →
registry, progressive disclosure via frontmatter-only token estimates, and
the untrusted-source execution refusal. Our implementation is Python on the
queued worker model, our exposure layer is budgeted prompt injection, and our
ToolSpec seam goes through the existing manifest/registry machinery — not a
translation of their loader.
