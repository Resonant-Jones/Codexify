# TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: Examples: utterances → compiled FlowSpec

## Metadata
- Task-ID: TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md
- Owner: resonant_jones
- Risk: LOW
- Commit mode: two-phase

## Objective
Provide three NL examples and the compiled FlowSpec JSON outputs as test vectors.

## Scope
### In-scope
- Add three example utterances with their compiled FlowSpec JSON:
  - Daily Digest
  - Weekly Reflection
  - Research Report
- Ensure FlowSpec JSON validates with FlowSpec v0.1

### Out-of-scope
- Executing these flows in production (runner tests handled in TASK-009)

## Allowed files (STRICT)
- docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md
- docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
- <optional: add a single docs/examples/flowspec_examples.json if desired>

## Preconditions (NO GUESSING)
```bash
cd <REPO_ROOT>
git status --porcelain -uall
# EXPECTED: (no output)
```

## Execution plan (copy/paste)
```bash
cd <REPO_ROOT>
git status --porcelain -uall
```
> NOTE: Add example utterances + FlowSpec JSON into this task artifact (and optional examples file).

## Example FlowSpec JSON Test Vectors (paste-in)

> These JSON blocks are the intended artifacts for TASK-008. Paste/keep them **in this section** so TASK-009 can load/validate them.

### Example 1 — Daily Digest (cron)

**User utterance**
> Every morning at 7:30, give me a digest of yesterday’s conversations and 3 actionable items. Save it as a Codex entry.

**FlowSpec JSON**
```json
{
  "flow_id": "daily_digest_v1",
  "version": "0.1",
  "enabled": true,
  "trigger": {
    "type": "cron",
    "schedule": "30 7 * * *",
    "event_name": null
  },
  "scope": {
    "user_id": "default",
    "project_ids": [],
    "thread_ids": [],
    "persona": "guardian.digest"
  },
  "budget": {
    "max_steps": 10,
    "max_tokens": 4000,
    "timeout_seconds": 120
  },
  "policy": {
    "min_confidence": 0.75,
    "require_confirmation_below_threshold": true,
    "allow_side_effects_without_confirmation": true
  },
  "steps": [
    {
      "step_id": "ctx",
      "primitive": "assemble_context",
      "params": {
        "intent": "Generate a daily digest of yesterday’s conversations and identify 3 actionable items.",
        "sources": {
          "threads": true,
          "memory": true,
          "codex": true,
          "personal_facts": true,
          "connectors": false
        },
        "window": {
          "threads_hours": 24,
          "memory_days": 7,
          "codex_days": 14
        },
        "search_depth": 2,
        "max_items": 50
      }
    },
    {
      "step_id": "summarize",
      "primitive": "summarize",
      "params": {
        "schema_name": "daily_digest_summary_v1",
        "instructions": [
          "Summarize yesterday’s activity in 5-10 bullets.",
          "Include only high-signal items.",
          "Do not invent facts."
        ]
      }
    },
    {
      "step_id": "actions",
      "primitive": "extract_actions",
      "params": {
        "schema_name": "action_items_v1",
        "max_actions": 3,
        "actionable_definition": [
          "Must start with a verb",
          "Must be specific and feasible",
          "Must reference something from context",
          "Must include a suggested next step"
        ]
      }
    },
    {
      "step_id": "post_thread",
      "primitive": "create_thread",
      "params": {
        "title_template": "Daily Digest — {{date}}",
        "body_template": {
          "format": "markdown",
          "sections": [
            { "title": "Summary", "from_step": "summarize" },
            { "title": "Top 3 Actions", "from_step": "actions" }
          ]
        }
      }
    },
    {
      "step_id": "codex_entry",
      "primitive": "write_codex_entry",
      "params": {
        "title_template": "Daily Digest — {{date}}",
        "tags": ["digest", "daily"],
        "content_from_steps": ["summarize", "actions"]
      }
    },
    {
      "step_id": "emit",
      "primitive": "emit_event",
      "params": {
        "event_name": "codexify.flow.daily_digest.completed",
        "payload_from_steps": ["codex_entry", "post_thread"]
      }
    }
  ],
  "output": {
    "store_as_thread": true,
    "store_as_codex": true,
    "emit_event": "codexify.flow.daily_digest.completed"
  },
  "idempotency": {
    "key_template": "daily_digest_v1::{{date}}",
    "mode": "return_cached"
  },
  "audit": {
    "log_trace": true,
    "record_cost": true,
    "redact_fields": ["api_key", "authorization", "cookie"]
  }
}
```

### Example 2 — Weekly Reflection (cron)

**User utterance**
> Every Friday, reflect on my last week: what I avoided, what moved forward, and one experiment for next week. Ask before saving if you’re unsure.

**FlowSpec JSON**
```json
{
  "flow_id": "weekly_reflection_v1",
  "version": "0.1",
  "enabled": true,
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * FRI",
    "event_name": null
  },
  "scope": {
    "user_id": "default",
    "project_ids": [],
    "thread_ids": [],
    "persona": "guardian.reflection"
  },
  "budget": {
    "max_steps": 12,
    "max_tokens": 5500,
    "timeout_seconds": 180
  },
  "policy": {
    "min_confidence": 0.85,
    "require_confirmation_below_threshold": true,
    "allow_side_effects_without_confirmation": false
  },
  "steps": [
    {
      "step_id": "ctx",
      "primitive": "assemble_context",
      "params": {
        "intent": "Reflect on the last week: what I avoided, what moved forward, and propose one experiment for next week.",
        "sources": {
          "threads": true,
          "memory": true,
          "codex": true,
          "personal_facts": true,
          "connectors": false
        },
        "window": {
          "threads_days": 7,
          "memory_days": 14,
          "codex_days": 30
        },
        "search_depth": 3,
        "max_items": 80
      }
    },
    {
      "step_id": "classify_themes",
      "primitive": "classify",
      "params": {
        "schema_name": "weekly_reflection_themes_v1",
        "labels": ["progress", "avoidance", "friction", "energy", "relationships", "work", "health", "learning"],
        "instructions": [
          "Classify notable items from context into these labels.",
          "Return counts and representative examples."
        ]
      }
    },
    {
      "step_id": "reflection",
      "primitive": "summarize",
      "params": {
        "schema_name": "weekly_reflection_report_v1",
        "instructions": [
          "Produce three sections: Avoided, Advanced, Experiment.",
          "Each claim must cite a referenced context snippet id if available.",
          "If evidence is thin, say 'uncertain' and lower confidence."
        ]
      }
    },
    {
      "step_id": "actions",
      "primitive": "extract_actions",
      "params": {
        "schema_name": "weekly_next_actions_v1",
        "max_actions": 5,
        "actionable_definition": [
          "Must be a next-week action",
          "Must be specific",
          "Must be realistically schedulable"
        ]
      }
    },
    {
      "step_id": "post_thread",
      "primitive": "create_thread",
      "params": {
        "title_template": "Weekly Reflection — Week of {{date}}",
        "body_template": {
          "format": "markdown",
          "sections": [
            { "title": "Themes", "from_step": "classify_themes" },
            { "title": "Reflection", "from_step": "reflection" },
            { "title": "Next Actions", "from_step": "actions" }
          ]
        }
      }
    },
    {
      "step_id": "codex_entry",
      "primitive": "write_codex_entry",
      "params": {
        "title_template": "Weekly Reflection — {{date}}",
        "tags": ["reflection", "weekly"],
        "content_from_steps": ["classify_themes", "reflection", "actions"]
      }
    },
    {
      "step_id": "emit",
      "primitive": "emit_event",
      "params": {
        "event_name": "codexify.flow.weekly_reflection.proposed",
        "payload_from_steps": ["codex_entry", "post_thread"]
      }
    }
  ],
  "output": {
    "store_as_thread": true,
    "store_as_codex": true,
    "emit_event": "codexify.flow.weekly_reflection.proposed"
  },
  "idempotency": {
    "key_template": "weekly_reflection_v1::{{iso_week}}",
    "mode": "return_cached"
  },
  "audit": {
    "log_trace": true,
    "record_cost": true,
    "redact_fields": ["api_key", "authorization", "cookie"]
  }
}
```

### Example 3 — Research Report (manual)

**User utterance**
> Research ‘local-first AI orchestration’ using my saved docs and recent threads, then write a report in a new thread.

**FlowSpec JSON**
```json
{
  "flow_id": "research_report_v1",
  "version": "0.1",
  "enabled": true,
  "trigger": {
    "type": "manual",
    "schedule": null,
    "event_name": null
  },
  "scope": {
    "user_id": "default",
    "project_ids": [],
    "thread_ids": [],
    "persona": "guardian.research"
  },
  "budget": {
    "max_steps": 12,
    "max_tokens": 7000,
    "timeout_seconds": 240
  },
  "policy": {
    "min_confidence": 0.7,
    "require_confirmation_below_threshold": true,
    "allow_side_effects_without_confirmation": true
  },
  "steps": [
    {
      "step_id": "ctx",
      "primitive": "assemble_context",
      "params": {
        "intent": "Research local-first AI orchestration using my saved docs and recent threads, then write a report.",
        "sources": {
          "threads": true,
          "memory": true,
          "codex": true,
          "personal_facts": false,
          "connectors": false,
          "documents": true
        },
        "query": "local-first AI orchestration",
        "window": {
          "threads_days": 30,
          "memory_days": 60,
          "codex_days": 180,
          "documents_days": 365
        },
        "search_depth": 3,
        "max_items": 120
      }
    },
    {
      "step_id": "retrieve_memory",
      "primitive": "retrieve_memory",
      "params": {
        "query": "local-first AI orchestration",
        "scope": "all",
        "k": 12,
        "confidence_threshold": 0.5,
        "search_depth": 2
      }
    },
    {
      "step_id": "report",
      "primitive": "summarize",
      "params": {
        "schema_name": "research_report_v1",
        "instructions": [
          "Write a structured research report with sections: Overview, Key Concepts, Tradeoffs, Recommendations, Sources.",
          "Prefer personal knowledge sources; only state claims supported by retrieved context.",
          "If something is speculative, label it as speculation."
        ]
      }
    },
    {
      "step_id": "actions",
      "primitive": "extract_actions",
      "params": {
        "schema_name": "research_recommendations_v1",
        "max_actions": 5,
        "actionable_definition": [
          "Must be a concrete next step",
          "Must be tied to the report content"
        ]
      }
    },
    {
      "step_id": "post_thread",
      "primitive": "create_thread",
      "params": {
        "title_template": "Research Report — {{query}} — {{date}}",
        "body_template": {
          "format": "markdown",
          "sections": [
            { "title": "Report", "from_step": "report" },
            { "title": "Recommendations", "from_step": "actions" }
          ]
        }
      }
    },
    {
      "step_id": "codex_entry",
      "primitive": "write_codex_entry",
      "params": {
        "title_template": "Research Report — {{query}} — {{date}}",
        "tags": ["research"],
        "content_from_steps": ["report", "actions"]
      }
    },
    {
      "step_id": "emit",
      "primitive": "emit_event",
      "params": {
        "event_name": "codexify.flow.research_report.completed",
        "payload_from_steps": ["codex_entry", "post_thread"]
      }
    }
  ],
  "output": {
    "store_as_thread": true,
    "store_as_codex": true,
    "emit_event": "codexify.flow.research_report.completed"
  },
  "idempotency": {
    "key_template": "research_report_v1::{{query}}::{{date}}",
    "mode": "always_run"
  },
  "audit": {
    "log_trace": true,
    "record_cost": true,
    "redact_fields": ["api_key", "authorization", "cookie"]
  }
}
```

## Expected results (explicit)
- Example FlowSpec JSON blocks are present and visually inspectable.
- A future automated validation step (TASK-009) can parse them.

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only
**Commit message (EXACT):**

“TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: example utterances -> FlowSpec”

**Manual commands:**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md <OPTIONAL_EXAMPLES_FILE>
git commit --no-verify -m "TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: example utterances -> FlowSpec"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: b81d6690

### Commit B (docs finalize + mapping) — two-phase only
**Commit message (EXACT):**

“TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: docs finalize + mapping”

**Manual commands:**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

### Campaign mapping (SOURCE OF TRUTH)

TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec -> [b81d6690, <commitB>]

### Completion Summary (fill after completion)

Status: DONE

What changed:

- Added machine-readable test vectors at `docs/examples/flowspec_examples.json` for Daily Digest, Weekly Reflection, and Research Report.
- Verified each example validates as `FlowSpec` and compiles successfully through `compile_flow()`.

Commands run:

git status --porcelain -uall
.venv/bin/python -c "import json; from guardian.flows.spec import FlowSpec; from guardian.flows.compiler import compile_flow; data=json.load(open('docs/examples/flowspec_examples.json')); names=[]; [names.append(example['name']) or compile_flow(FlowSpec.model_validate(example['flow_spec'])) for example in data['examples']]; print('validated', len(names), names)"
git add docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md docs/examples/flowspec_examples.json
git commit --no-verify -m "TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec: example utterances -> FlowSpec"

Tests:

FlowSpec + compile checks for all three vectors: pass

Scope check:

git status clean before starting: yes

Only allowed files modified: yes

Commit info:

Commit mode: two-phase

Commit A hash: b81d6690

Commit B hash: recorded in campaign mapping

Campaign mapping updated: yes

Notes / gotchas:

Runtime validation checks used `.venv/bin/python` in this shell due missing dependencies in system `python`.
