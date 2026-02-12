# Task Receipt Draft

Task ID: 003
Title: Wire image generation to real thread and project context
Risk: MED
Source Finding: FINDING-2026-02-11-009

Goal:
- Remove hardcoded project_id and thread_id from image generation requests.
- Use active context from runtime UI state.