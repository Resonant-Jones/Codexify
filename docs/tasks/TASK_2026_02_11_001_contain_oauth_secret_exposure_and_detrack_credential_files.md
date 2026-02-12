# Task Receipt Draft

Task ID: 001
Title: Contain OAuth secret exposure and de-track credential files
Risk: HIGH
Source Finding: FINDING-2026-02-11-002

Goal:
- Remove credential-bearing OAuth files from git tracking.
- Keep only safe placeholder examples.
- Record external rotation requirement.

Must Stop If:
- Working tree is dirty before starting.
- Any out-of-scope file is modified.