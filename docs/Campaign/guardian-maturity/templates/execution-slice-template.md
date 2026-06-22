# Execution Slice Template

Copy this template for each atomic execution slice within a campaign. Each slice is a self-contained, testable, and independently mergeable unit of work.

---

## Slice Metadata

- **Slice ID**: `<CAMPAIGN>-SLICE-<NNN>`
- **Campaign**: `<CXX> — <campaign title>`
- **Status**: `planned` | `in-progress` | `complete`
- **Architecture Impact**: `yes` | `no`

## Objective

One sentence describing what this slice accomplishes.

## Scope

Specific files, routes, components, or behaviors this slice touches:
- `<path or surface>` — `<change description>`

## Out of Scope

What this slice explicitly does **not** touch:
- `<excluded surface>`
- `<excluded surface>`

## Architecture Impact

If `yes`, explain why:
- Governing ADRs: `<list>`
- Reason: `<why this touches architectural boundaries>`

## Files/Surfaces

| File | Change Type | Description |
|------|-------------|-------------|
| `<path>` | `create` / `modify` / `delete` | `<what changes>` |

## Acceptance Criteria

- [ ] `<criterion>`
- [ ] `<criterion>`

## Validation Commands

```bash
# Command 1
<command>

# Command 2
<command>
```

## Proof Artifact

After execution, record evidence in the campaign's [`proof-pack.md`](../proof-pack.md).

## Completion Rule

This slice is complete when:
1. All acceptance criteria are met.
2. All validation commands pass.
3. Changes are committed with a descriptive message.
4. Proof artifact is recorded.
5. Task index is updated.
