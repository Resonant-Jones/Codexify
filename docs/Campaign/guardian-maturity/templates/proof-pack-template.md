# Proof Pack Template

Copy this template to `<campaign-folder>/proof-pack.md` and record evidence as it is collected.

---

## Campaign

- **Campaign ID**: `<CXX>`
- **Title**: `<campaign title>`

## Slice/Task

- **Slice/Task ID**: `<identifier>`
- **Description**: `<what was executed>`

## Evidence Collected

### Docs Proof

- [ ] `<evidence description>`
- [ ] `<evidence description>`

### Backend Seam Proof

- [ ] `<evidence description>`
- [ ] `<evidence description>`

### Frontend UI Proof

- [ ] `<evidence description>`
- [ ] `<evidence description>`

### Live Supported-Path Proof

- [ ] `<evidence description>`
- [ ] `<evidence description>`

### Operator Usability Proof

- [ ] `<evidence description>`
- [ ] `<evidence description>`

## Commands Run

```bash
# Verification commands and their output summaries
$ <command>
<output summary>

$ <command>
<output summary>
```

## Results

| Proof Category | Status | Notes |
|----------------|--------|-------|
| Docs proof | `pass` / `fail` / `not run` | `<notes>` |
| Backend seam proof | `pass` / `fail` / `not run` | `<notes>` |
| Frontend UI proof | `pass` / `fail` / `not run` | `<notes>` |
| Live supported-path proof | `pass` / `fail` / `not run` | `<notes>` |
| Operator usability proof | `pass` / `fail` / `not run` | `<notes>` |

## Known Gaps

- `<gap description>` — `<impact>`

## Gate Decision

- **Decision**: `go` | `hold` | `next-proof-needed`
- **Reason**: `<why this decision was made>`

## Follow-Up Required

- [ ] `<follow-up item>`
- [ ] `<follow-up item>`
