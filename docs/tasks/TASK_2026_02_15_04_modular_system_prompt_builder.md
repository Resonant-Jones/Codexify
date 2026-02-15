
TASK 4 — Modular System Prompt Builder (Segmented Assembly + Token Accounting)

Objective

Implement a single, deterministic system prompt assembly pipeline that composes:

- Immutable Base System Prompt
- Imprint_Zero (Light Identity) block (budgeted)
- Persona block (selected persona / mask)
- System Docs block (repo/system references)
- Optional Scratchpad block (ephemeral)

and returns:
- the assembled system prompt string
- structured metadata describing segments, sizes, and estimated token cost

This task turns prompt construction into software, not ad hoc string concatenation.

Scope

Backend-only for this task.
Do not modify frontend UI.
Do not implement new retrieval logic here (only assemble what is provided).
Do not implement persona persistence here (Task 5).
Do not implement diary/modeling enforcement here (Task 1).

Security / Correctness Invariants (Must Hold)

1) Single System Message
- The builder returns exactly one system prompt string (the system message content), not multiple competing system messages.

2) Deterministic Ordering
- Segment ordering is fixed and documented. No conditional reordering.

3) Explicit Segment Boundaries
- Each segment is delimited with stable markers so provenance is inspectable.

4) Budget Awareness
- Builder computes estimated token counts per segment and total.
- Builder supports optional hard caps per segment (at minimum: imprint and system_docs caps).

System Model

Create a prompt builder module that accepts structured inputs and returns a structured output.

A) Inputs (example shape)

- base_system_prompt: str (required)
- imprint_block: str | None
- persona_block: str | None
- system_docs_block: str | None
- scratchpad_block: str | None
- budgets:
  - imprint_max_tokens: int | None
  - system_docs_max_tokens: int | None
  - total_max_tokens: int | None (optional)

B) Output

- system_prompt: str
- meta:
  - estimated_tokens_total: int
  - segments: list of:
    - name: "base" | "imprint" | "persona" | "system_docs" | "scratchpad"
    - chars: int
    - estimated_tokens: int
    - truncated: bool
  - truncation_notes: list[str]

Token Estimation

- Prefer a repo-local tokenizer if one exists.
- If not available, use a conservative heuristic:
  - estimated_tokens = ceil(chars / 4)

Segment Truncation Policy

If a segment exceeds its budget:
- truncate that segment only
- set segment.truncated = true
- add a truncation note explaining what was truncated

Ordering (Fixed)

1) base
2) imprint
3) persona
4) system_docs
5) scratchpad

Delimiters (Required)

Use stable headers:

=== BASE SYSTEM ===
...
=== IMPRINT_ZERO ===
...
=== PERSONA ===
...
=== SYSTEM DOCS ===
...
=== SCRATCHPAD ===
...

Files Likely Affected

This change belongs in backend prompt assembly and chat route integration.
Likely locations include:

- guardian/core/prompt_builder.py (new) or an equivalent existing prompt module
- guardian/core/prompts.py (refactor to use builder)
- guardian/routes/chat.py (or the primary chat generation route) to call the builder
- backend tests directory (existing prompt/auth/core tests)

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Create the Builder Module
- Create a backend module for prompt assembly (choose the correct directory consistent with the repo).
- Implement:
  - build_system_prompt(inputs...) -> (system_prompt: str, meta: dict)
- Enforce fixed ordering and delimiters.

2) Refactor Existing Prompt Assembly
- Refactor existing prompt code so it passes already-fetched blocks into the builder.
- Do NOT move retrieval logic into the builder.
- The builder must be a pure function with no IO.

3) Token Estimation + Budgets
- Implement token estimation and per-segment budgets.
- Ensure imprint and system_docs can be capped independently.
- If truncation occurs, meta must reflect it.

4) Wire Into Chat Route
- Update the chat generation route to use the builder output for the system message content.
- Ensure only one system message is produced.

5) Tests (Required)
Add backend tests that fail before and pass after:

- Builder returns a single string system_prompt.
- Segment ordering is fixed and correct.
- Meta includes total + per-segment estimated token counts.
- Budget truncation truncates only the target segment and sets truncated=true.
- Delimiters exist exactly once per included segment.

6) Validation
Run backend tests:

pytest -v

7) Commit
Stage only modified files.
Commit message:

"Add modular system prompt builder with token metadata"

Output (Required)

- Summary of changes (files + key functions).
- Backend test results summary.
- Git commit hash.

Constraints

- Do not add frontend UI.
- Do not add new retrieval logic.
- Do not implement persona persistence.
- Do not change identity modeling behavior.

This task creates the prompt-assembly substrate required for token cost transparency and provenance tooling later.
