# Task: Build Campaign Audit Output

Date: 2026-02-04

## Objective
Create a fully compliant Codex Runner campaign audit output payload, including campaign and task markdown bodies, correct file naming, and a complete activation prompt.

## Inputs
- Campaign metadata (id, slug, date)
- Path constraints:
  - Campaign doc: docs/Campaign/CAMPAIGN_YYYY_MM_DD.md
  - Task artifact: docs/tasks/TASK_YYYY_MM_DD_NNN_lower_snake_slug.md

## Deliverables
- Campaign markdown content (full body)
- Task artifact markdown content (full body)
- Activation prompt that can be used to start the task

## Acceptance Criteria
- JSON output passes schema validation.
- Paths match required patterns exactly.
- Markdown bodies are complete and non-empty.
- Activation prompt is actionable and unambiguous.
