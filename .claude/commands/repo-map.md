# repo-map

Quickly orient an agent to the Codexify repo structure before implementation.

## Execution Steps

1. **Inspect the relevant directories first**
   - Identify which area the task targets: `guardian/`, `backend/`, `frontend/`, `tests/`, or `docs/`
   - List the directory contents to understand the layout

2. **Identify exact edit targets before coding**
   - Search for the specific files that need modification
   - Read the files fully before making changes
   - Note existing patterns and conventions in use

3. **Confirm whether the target surface is mounted/wired/used**
   - Check if the code you're editing is actually imported and called
   - Verify routes are registered, components are rendered, services are instantiated
   - Search for usages of the target abstraction

4. **Identify neighboring tests before editing**
   - Find tests in `tests/` that cover the target area
   - For frontend changes, check `frontend/tests/`
   - Note the test patterns used (fixtures, mocks, assertions)

5. **Summarize findings before implementation**
   - State the edit targets clearly
   - Note any related files that may need updates
   - Identify the test files that should pass after changes
   - Confirm the runtime path is valid

## Output

Before coding, output a brief summary:
- Target directories inspected
- Files to be edited
- Neighboring tests identified
- Confirmation that target is runtime-wired (or note if it's a spec/stub only)
