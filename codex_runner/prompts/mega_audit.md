<CodexifyAudit>
You are conducting an evidence-based audit of the Codexify repo. Do not guess; prefer file-path references (and line ranges if available). Do not ask follow-up questions before starting—if something is ambiguous, record it explicitly as a finding with evidence and a proposed “discovery” command.

PRIMARY GOAL
Produce two repo-written artifacts:

1) A full “Senior Architect” system audit report (security/privacy/sovereignty + drift + DX + performance + risk register)
2) A Codexify MVP Roadmap & Core Loop Plan focused on closing the 6 core loops end-to-end

WORKTREE HYGIENE

- Begin with: git status --porcelain -uall
- If any untracked/modified files exist that are not required to produce the two requested outputs:
  - Do NOT delete or modify them.
  - Do NOT stop to ask what to do.
  - Record a finding WORKTREE-DRIFT with the file list and suggested cleanup commands.
  - Continue, writing ONLY the two requested output files.

SCORING (IN REPORT)
For each of the 6 core loops, include two separate statuses:

- Code Present: (stubbed|partial|complete)
- Loop Closed: (yes|no) with explicit closure requirements: auth outside dev proxy, persistence via backend list, deterministic validation path.

MVP ASSUMPTION
For MVP, “works locally with documented env vars/services configured” is acceptable.
Do not require production hardening unless it blocks local end-to-end loop closure.v
CRITICAL CONSTRAINTS (EVIDENCE-FIRST)

- Only assert what you can prove from code/config/docs in the repo.
- For every important claim, include file paths; include line ranges where possible.
- If you cannot access code or run commands, state that clearly and do not guess.
- Be ruthless about MVP scope: anything not needed to close a core loop goes to Deferred.

OUTPUT FILES (WRITE THESE)
A) System Audit Report

- Ensure folders exist: docs/ and docs/reports/
- Write: docs/reports/codexify-system-audit-YYYY-MM-DD.md
- Use the “Senior Architect System Audit” headings and include:
  - Metadata (repo, date, agent/model, env/runner, git branch + commit if possible)
  - Executive Summary with top 5 concerns tagged [RISK]/[WARN]
  - System Overview + subsystem status list (Implemented/Partial/Stubbed/Documented-only/Planned)
  - Security/Privacy/Sovereignty: secrets management, code-evidenced data egress map table, access control boundaries
  - Docs ↔ Code Consistency (docs drift vs code drift)
  - Code Quality / Testing / DX (how to run tests; gaps)
  - Performance & Scalability (mark implemented vs theoretical)
  - Risk Register table (top ~10–20 issues) with evidence

B) MVP Roadmap & Core Loop Plan

- Write: docs/codexify-mvp-roadmap-YYYY-MM-DD.md (prefer docs/ if present)
- Use the “Audit Prompt” structure:
  - Overview & Goals
  - For each of 6 core features:
    - Current State
    - Core Loop Definition (stepwise)
    - Gap Analysis table (loop step → current impl → gap → concrete fix)
    - Implementation Tasks
    - Validation Plan (manual scripts + automated test recommendations with paths)
  - Milestones & Timeline (M0..M5)
  - Risks / Assumptions / Dependencies
  - Deferred Features (parking lot)

BRIDGE OUTPUT (RUNNER-READY FINDINGS MANIFEST)
Inside the System Audit Report, add a dedicated section near the top:

## Runner-Ready Findings Manifest (authoritative)

Include a YAML list where EACH finding has:

- finding_id: FINDING-YYYY-MM-DD-NNN
- area: (security|sovereignty|core-loop|dx|docs-drift|performance|testing|other)
- severity: (RISK|WARN|INFO)
- title: short
- description: 1–3 paragraphs
- evidence:
  - file: path
    lines: "Lx-Ly" (if available) OR "unknown"
- relates_to_core_loop: (rag|migration|doc-upload|image-gallery|image-gen|doc-gen|none)
- suggested_task_outcome: an observable “done” statement
- suggested_commands:
  - exact commands to run to validate / reproduce
- dependencies: list (env vars, services, containers) or empty
- notes: any ambiguity + what would remove ambiguity

IMPORTANT: Every major gap you identify in the MVP Roadmap MUST correspond to at least one finding in this manifest. Every [RISK]/[WARN] in the Senior Audit MUST also appear here.

POST-WRITE TERMINAL SUMMARY (VERY SHORT)
After writing both files, print:

- The two report paths
- Bullet list of the top 5 [RISK] findings (finding_id + title)

BEGIN by scanning the repository now, then generate both files as specified.
</CodexifyAudit>
