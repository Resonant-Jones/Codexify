# runtime-check

Pre-coding verification discipline to ensure changes are runtime-valid.

## Before Coding, Verify

### 1. Import Validity
Check that imports resolve correctly in the current package/runtime layout:
- Is the module path correct for the current working directory?
- Are circular imports introduced?
- Does the import exist, or is it a dead reference?

### 2. Mount/Reachability Confirmation
Verify the target route/component is actually mounted and reachable:
- For routes: Check registration in the router/app mounting
- For components: Verify they are rendered or exported to consumers
- For services: Confirm instantiation and injection points

### 3. Liveness of Abstractions
Determine whether referenced abstractions are live or dead:
- Is the class/function actually imported and used elsewhere?
- Or is it defined but never called?
- Check `git log` for last modification date - abandoned code is suspect

### 4. Real Wiring vs Declared Spec
Distinguish real runtime wiring from declared specs/interfaces:
- A type definition does not mean implementation exists
- An interface or protocol may have no concrete implementation
- Check for actual usage, not just presence in the codebase

### 5. Smallest Valid Fix
Determine the minimal intervention:
- Is deletion the answer? (remove dead code)
- Is direct wiring needed? (connect existing pieces)
- Is a thin shim appropriate? (bridge a gap without over-engineering)

## Explicitly Discouraged

- **Speculative adapters** - Do not create abstractions for hypothetical future use
- **Reviving abandoned abstractions without proof** - Dead code is dead for a reason
- **Treating stub-bound surfaces as production-ready** - A stub is not a capability

## Output

Before implementation, state:
- Verification steps completed
- Confirmation that target is runtime-wired (or note if stub/spec only)
- The chosen fix type: deletion, direct wiring, or thin shim
