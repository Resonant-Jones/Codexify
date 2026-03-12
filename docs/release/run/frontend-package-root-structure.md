# Frontend Package-Root Structure

**Date:** 2026-03-12
**Scope:** Codexify repository frontend build system topology

---

## Overview

This document maps the current frontend package-root structure and explains how build/test commands resolve across the layered `package.json` files and Tauri configuration.

---

## Package Structure

The repository has three levels of `package.json` files:

```
repo-root/
├── package.json                 # Root package (delegation layer)
├── pnpm-workspace.yaml          # Workspace definition
├── frontend/
│   ├── package.json            # Wrapper layer (pass-through)
│   └── src/
│       ├── package.json        # ACTUAL PACKAGE ROOT
│       ├── node_modules/       # Dependencies installed here
│       ├── vite.config.ts      # Build tooling config
│       └── dist/               # Build output (referenced by Tauri)
└── src-tauri/
    ├── Cargo.toml
    └── tauri.conf.json         # Tauri build configuration
```

---

## Package-by-Package Analysis

### 1. Root `package.json`

**Location:** `/package.json`

**Role:** Delegation layer. All scripts use `pnpm --dir frontend/src` to delegate to the actual package root.

```json
{
  "scripts": {
    "lint": "pnpm --dir frontend/src lint",
    "build": "pnpm --dir frontend/src build",
    "test": "pnpm --dir frontend/src exec vitest run",
    "format": "pnpm --dir frontend/src format",
    "format:check": "pnpm --dir frontend/src format:check"
  }
}
```

**Key insight:** The root package has no direct dependencies for frontend build. It exists as a convenience for running commands from the repo root.

---

### 2. `frontend/package.json`

**Location:** `/frontend/package.json`

**Role:** Wrapper/Pass-through layer. Scripts use `cd src && pnpm <command>` or `pnpm --dir src` to delegate to the actual package.

```json
{
  "name": "guardian-backend_v2",
  "scripts": {
    "dev": "cd src && pnpm dev",
    "build": "cd src && pnpm build",
    "test": "pnpm --dir src exec vitest run",
    "lint": "cd src && pnpm lint",
    "format": "cd src && pnpm format"
  }
}
```

**Key insight:** This package has its own `devDependencies` (including `@tauri-apps/cli`, `cypress`, `vitest`), but these are separate from the actual build dependencies in `frontend/src/`. This creates potential for version drift.

---

### 3. `frontend/src/package.json` - ACTUAL PACKAGE ROOT

**Location:** `/frontend/src/package.json`

**Role:** The true frontend package root. Contains all build tooling dependencies and actual application dependencies.

```json
{
  "name": "guardian-monorepo",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "test": "vitest",
    "format": "prettier . --write",
    "lint": "eslint ."
  },
  "devDependencies": {
    "vite": "^7.3.1",
    "vitest": "^4.0.13",
    "tailwindcss": "^4.1.14",
    ...
  },
  "dependencies": {
    "react": "19.2.0",
    "@tauri-apps/api": "^2.9.1",
    ...
  }
}
```

**Key insight:** This is where `node_modules/` actually exists. This is the directory where `pnpm install` must be run for frontend dependencies. This is also where `vite.config.ts` lives and where the actual build/test execution happens.

---

### 4. `pnpm-workspace.yaml`

**Location:** `/pnpm-workspace.yaml`

```yaml
packages:
  - frontend/src
```

**Key insight:** The workspace only includes `frontend/src`, not `frontend/` or the root. This confirms `frontend/src` is the canonical package root.

---

### 5. `src-tauri/tauri.conf.json`

**Location:** `/src-tauri/tauri.conf.json`

```json
{
  "build": {
    "frontendDist": "../frontend/src/dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "pnpm --dir frontend/src dev",
    "beforeBuildCommand": "pnpm --dir frontend/src build"
  }
}
```

**Key insight:** Tauri directly references `frontend/src` for both development and build commands. It does not go through the wrapper layers.

---

## Command Resolution in Practice

### Root-level commands

When you run from repo root:

```bash
# From: repo-root/
# Runs: pnpm --dir frontend/src exec vitest run
pnpm test
```

**Resolution path:**
1. Root package.json script delegates to `frontend/src`
2. pnpm changes to `frontend/src` directory
3. Executes `vitest run` using the vitest from `frontend/src/node_modules/.bin/`

### Frontend wrapper commands

When you run from `frontend/`:

```bash
# From: frontend/
# Runs: cd src && pnpm dev
pnpm dev
```

**Resolution path:**
1. frontend/package.json changes to `src/` subdirectory
2. Runs `pnpm dev` in that directory
3. Executes `vite dev` from `frontend/src/node_modules/.bin/`

### Direct commands (recommended)

```bash
# From: repo-root/
# Direct execution in the actual package root
pnpm --dir frontend/src exec vitest run
pnpm --dir frontend/src build
pnpm --dir frontend/src dev
```

**Resolution path:**
1. pnpm changes to `frontend/src`
2. Executes command directly

### Tauri commands

Tauri automatically runs the beforeDevCommand/beforeBuildCommand:

```bash
# From: src-tauri/
cargo tauri dev      # Runs: pnpm --dir frontend/src dev
cargo tauri build    # Runs: pnpm --dir frontend/src build
```

---

## Integration Confusion During Merge

During the Beta Stabilization merge cycle, the following package-root ambiguities caused validation friction:

### Issue 1: Missing install state in `frontend/src`

**Symptom:**
```
$ pnpm --dir frontend/src exec vitest run
ERR_PNPM_NO_PKG_MANIFEST  No package.json found in /Users/.../frontend/src
```

Or:
```
$ pnpm test
 ERR_PNPM_CANNOT_RESOLVE_WORKSPACE_PROTOCOL  Cannot resolve workspace protocol
```

**Root cause:** `node_modules` existed in `frontend/` (the wrapper) but not in `frontend/src/` (the actual package root). The workspace is configured for `frontend/src`, so pnpm expects the install to be there.

**Resolution:** Install must happen in `frontend/src/`:
```bash
cd frontend/src && pnpm install
```

### Issue 2: Command execution from wrong directory

**Symptom:** Tests pass when run from `frontend/` but fail when run from root, or vice versa.

**Root cause:** Running `pnpm test` from `frontend/` uses the wrapper's script (`pnpm --dir src exec vitest run`), which should work, but if `frontend/src/node_modules` is missing, it fails.

### Issue 3: Dependency version confusion

The `frontend/package.json` and `frontend/src/package.json` have different versions of the same tools:

| Tool | frontend/package.json | frontend/src/package.json |
|------|----------------------|---------------------------|
| vite | ^7.1.0 | ^7.3.1 |
| vitest | ^3.2.4 | ^4.0.13 |
| tailwindcss | ^4.1.11 | ^4.1.14 |

This means the wrapper layer may have different tool versions than the actual build layer.

---

## Recommendation

**Classification:** `keep for now but document clearly`

### Rationale for keeping:

1. **Tauri integration depends on it:** The `src-tauri/tauri.conf.json` directly references `frontend/src` paths
2. **Workspace is configured:** `pnpm-workspace.yaml` explicitly defines `frontend/src` as the package
3. **Build output location:** `frontend/src/dist` is the expected output directory

### Why not "keep as-is":

The current structure creates real friction:
- Two levels of package.json wrapper cause confusion
- Version drift between wrapper and actual package
- `node_modules` location is non-obvious
- Documentation is needed to explain the topology

### Why not "simplify now":

Refactoring would require:
- Moving all source files from `frontend/src/src/` (current structure) to a new location
- Updating Tauri configuration
- Updating workspace configuration
- Updating CI/CD pipelines
- Verifying no other tools depend on current structure

This is significant work that should be its own campaign, not a side task.

### Recommended future simplification:

If a future campaign addresses this, consider:

1. **Option A:** Flatten to single `frontend/package.json`
   - Move all dependencies from `frontend/src/package.json` to `frontend/package.json`
   - Move `vite.config.ts` to `frontend/`
   - Update workspace to `frontend`
   - Update Tauri config to `../frontend/dist`

2. **Option B:** Clarify naming
   - Rename `frontend/` to `desktop/` or `app/`
   - Keep `frontend/src/` as `frontend/` (the actual frontend)
   - Makes the wrapper vs. actual package distinction clearer

---

## Quick Reference

### Where to run commands

| Task | Working Directory | Command |
|------|------------------|---------|
| Install frontend deps | `frontend/src/` | `pnpm install` |
| Run frontend dev | repo root | `pnpm --dir frontend/src dev` |
| Run frontend tests | repo root | `pnpm --dir frontend/src exec vitest run` |
| Build frontend | repo root | `pnpm --dir frontend/src build` |
| Run Tauri dev | `src-tauri/` | `cargo tauri dev` |
| Build Tauri app | `src-tauri/` | `cargo tauri build` |

### Which package.json to edit

| Change | Edit this file |
|--------|----------------|
| Add frontend dependency | `frontend/src/package.json` |
| Add dev/build tool | `frontend/src/package.json` |
| Change Tauri integration | `src-tauri/tauri.conf.json` |
| Change root convenience scripts | Root `package.json` |

---

## See Also

- `merge-worktree-operating-procedure.md` - Validation order section
- `pnpm-workspace.yaml` - Workspace configuration
- `src-tauri/tauri.conf.json` - Tauri build configuration
