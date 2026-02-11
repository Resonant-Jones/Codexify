# Task Receipt Draft

Task ID: 002
Title: Require auth and ownership checks on thread document list endpoint
Risk: HIGH
Source Finding: FINDING-2026-02-11-003

Goal:
- Ensure /api/threads/{thread_id}/documents enforces API key auth.
- Ensure caller can only list documents for authorized thread scope.