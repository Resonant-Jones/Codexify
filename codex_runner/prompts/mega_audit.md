<file name=0 path=/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/prompts/mega_audit.md><CodexifyAudit>
You are conducting an evidence-based audit of the target repo. Do not guess; prefer file-path references (and line ranges if available). Do not ask follow-up questions before starting—if something is ambiguous, record it explicitly as a finding with evidence and a proposed “discovery” command.

PRIMARY GOAL
Produce ONE runner-consumable JSON object (printed to stdout) that conforms to the following template exactly (field names + overall structure), derived from mega_audit_output.schema.json:

IMPORTANT: Determine `agent.model` by running `python codex_runner/model_id_helper.py` before assembling the JSON.
- This helper prints exactly one line `MODEL_ID=<value>` after checking (in order) `CODEX_MODEL`, `OPENAI_MODEL`, then the Codex CLI config.
- Use the `<value>` portion verbatim for `agent.model` (example: output `MODEL_ID=gpt-5.3-codex` → `"agent.model": "gpt-5.3-codex"`).
- If the helper emits `MODEL_ID=unknown`, still set `agent.model` to `"unknown"` **and** add a `dx`/`WARN` runner_ready_finding titled `MODEL-ID-UNKNOWN` that records the helper command under `suggested_commands`.
- Do **not** guess or use generic labels like `GPT-5`; rerun the helper if needed.

HARD FAIL SELF-CHECK (before printing): If your JSON would contain `"model":"GPT-5"` (or any other generic model label), do **not** print it. Fix `agent.model` first.

{
  "audit_id": "AUDIT_YYYY_MM_DD",
  "repo": {
    "path": "/absolute/path/to/repo",
    "branch": "branch-name",
    "commit": "optional-commit-hash-or-null"
  },
  "generated_at": "ISO-8601 timestamp",
  "agent": {
    "name": "Codex",
    "model": "gpt-5.3-codex",
    "mode": "audit"
  },

  "reports": [
    {
      "report_id": "security_system_audit",
      "type": "system_audit",
      "path": "docs/reports/...",
      "severity_summary": {
        "RISK": 5,
        "WARN": 7,
        "INFO": 3
      }
    },
    {
      "report_id": "mvp_roadmap",
      "type": "mvp_roadmap",
      "path": "docs/...",
      "focus": "core-loop-closure"
    }
  ],

  "runner_ready_findings": [
    {
      "finding_id": "FINDING-YYYY-MM-DD-NNN",
      "area": "security | core-loop | dx | performance | testing | docs-drift | other",
      "severity": "RISK | WARN | INFO",
      "title": "short title",
      "description": "1–3 paragraphs",
      "evidence": [
        {
          "file": "path",
          "lines": "Lx-Ly | unknown"
        }
      ],
      "relates_to_core_loop": "rag | migration | doc-upload | image-gallery | image-gen | doc-gen | none",
      "suggested_task_outcome": "observable done statement",
      "suggested_commands": [
        "exact command",
        "exact command"
      ],
      "dependencies": [
        "ENV_VAR",
        "SERVICE"
      ],
      "notes": "ambiguity notes"
    }
  ],

  "campaign_derivation_rules": {
    "strategy": "one-or-more-campaigns",
    "group_by": [
      "severity",
      "core_loop"
    ],
    "priority_order": [
      "RISK",
      "WARN",
      "INFO"
    ]
  },

  "derived_campaigns": [
    {
      "campaign_id": "CAMPAIGN_YYYY_MM_DD_<SLUG>",
      "campaign_type": "security | mvp | followup",
      "source_findings": [
        "FINDING-YYYY-MM-DD-NNN"
      ]
    }
  ]
}

IMPORTANT OUTPUT RULES
- Output MUST be valid JSON (no trailing commas, no comments).
- Output MUST be the ONLY thing you print (no preambles like "thinking", no logs, no explanations).
- Output MUST be the ONLY thing you print (no prose, no markdown, no code fences, no "thinking" blocks, no tool logs).
- Do NOT write any files to the repo in this stage.
- The `reports[].path` values are INTENDED output locations for a later stage (Campaign Runner will write actual markdown reports). Use the same paths that the previous markdown-based version required.

INTENDED REPORTS (DO NOT WRITE THEM HERE)
The JSON must describe these two intended repo-written artifacts (paths recorded under `reports[]`):

1) A full “Senior Architect” system audit report (security/privacy/sovereignty + drift + DX + performance + risk register)
2) A Codexify MVP Roadmap & Core Loop Plan focused on closing the 6 core loops end-to-end

WORKTREE HYGIENE

- Begin with: git status --porcelain -uall
- If any untracked/modified files exist that are not required to produce the JSON output:
  - Do NOT delete or modify them.
  - Do NOT stop to ask what to do.
  - Add a finding with:
    - area: "other"
    - severity: "WARN"
    - title: "WORKTREE-DRIFT"
    - suggested_commands: cleanup commands
  - Continue, producing ONLY the JSON output.

SCORING (IN FINDINGS)
For each of the 6 core loops, ensure you include findings that enable the campaign compiler to compute two statuses:

- Code Present: (stubbed|partial|complete)
- Loop Closed: (yes|no) with explicit closure requirements: auth outside dev proxy, persistence via backend list, deterministic validation path.

MVP ASSUMPTION
For MVP, “works locally with documented env vars/services configured” is acceptable.
Do not require production hardening unless it blocks local end-to-end loop closure.

CRITICAL CONSTRAINTS (EVIDENCE-FIRST)

- Only assert what you can prove from code/config/docs in the repo.
- For every important claim, include file paths; include line ranges where possible.
- If you cannot access code or run commands, state that clearly and do not guess. In that case set evidence.lines to "unknown" and include discovery commands.
- Be ruthless about MVP scope: anything not needed to close a core loop goes to Deferred (severity INFO with explicit deferral notes).

RUNNER-READY FINDINGS MANIFEST (AUTHORITATIVE)
Populate `runner_ready_findings` such that:

- Every major gap you identify MUST correspond to at least one finding.
- Every RISK/WARN item you surface MUST be represented as a finding.
- Each finding MUST include:
  - evidence[] with at least one entry (file + lines or unknown)
  - suggested_task_outcome: an observable “done” statement
  - suggested_commands: exact commands to validate / reproduce (or to remove ambiguity)
  - dependencies: list required env vars/services/containers, or []

SEVERITY SUMMARY
Compute `reports[0].severity_summary` as counts of findings by severity across `runner_ready_findings`.

DERIVED CAMPAIGNS
In `derived_campaigns`, propose one-or-more campaign groupings using only the findings you emitted.
- Each derived_campaign MUST reference findings by ID.
- Use campaign_id format: CAMPAIGN_YYYY_MM_DD_<SLUG>
- campaign_type guidance:
  - security: findings primarily in area security/sovereignty
  - mvp: findings primarily in area core-loop/dx/testing
  - followup: cleanup / deferred / long-tail

BEGIN by scanning the repository now, then output ONLY the JSON object described above.
</CodexifyAudit>
</file>
