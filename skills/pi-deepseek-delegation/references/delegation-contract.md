# Delegation contract

Use this template to create a bounded handoff. Remove irrelevant sections before sending it to Pi.

```markdown
# Objective
Produce one concrete, independently reviewable outcome.

# Repository context
- Working directory:
- Relevant modules/files:
- Current behavior:
- Desired behavior:

# Scope
Inspect or modify only:
- path/or/module

Do not touch:
- unrelated modules
- generated files
- lockfiles unless required and explained
- credentials or environment files

# Constraints
- Preserve these interfaces:
- Follow these repository conventions:
- Do not commit, push, merge, deploy, or access production.
- Do not broaden the task without reporting the blocker.

# Verification
You may run:
- exact test or lint commands

Do not run:
- destructive commands
- network mutation
- deployment or release commands

# Deliverable
Return:
1. Summary
2. Evidence with file paths and symbols
3. Findings or changes
4. Commands run and observed results
5. Risks and unresolved assumptions
6. Files touched, if any
```

## Good task shapes

- "Trace why an authenticated websocket reconnect loses project scope. Inspect only the websocket session and auth middleware modules. Return three ranked hypotheses with exact code evidence. Do not edit files."
- "Review this diff only for race conditions and idempotency failures. Cite the affected functions and propose minimal tests."
- "In the isolated worktree, add unit tests for the three documented parser edge cases. Do not change production code unless a test cannot be expressed, and explain any such blocker first."

## Weak task shapes

Avoid prompts such as:

- "Fix the repo."
- "Make this better."
- "Review everything."
- "Do whatever is needed."

These prompts erase the boundary that makes delegation useful and safe.
