# TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: Remove hardcoded secrets from docker-compose.yml

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Remove hardcoded credentials/secrets in docker-compose.yml and ensure secrets are provided via environment variables (or Docker secrets if already supported), without changing runtime behavior beyond configuration safety.

### Scope
- Replace hardcoded values (e.g., GUARDIAN_API_KEY, postgres/neo4j passwords) with env-substitution.
- Update `.env.example` / `.env.template` if necessary to reflect required variables.
- Out-of-scope: new secrets manager integrations or auth changes.

### Expected Output
- Hardcoded secrets removed from docker-compose.yml; env-driven defaults documented.
- `docker compose config` succeeds.

## Allowed Files
- docker-compose.yml
- .env.example
- .env.template
- docs/tasks/TASK_2026_01_23_001_secrets_docker_compose.md
- docs/Campaign/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "GUARDIAN_API_KEY:|POSTGRES_PASSWORD:|NEO4J_PASSWORD:|OPENAI_API_KEY:" docker-compose.yml
- rg -n "GUARDIAN_API_KEY:\s*[0-9a-f]{16,}|POSTGRES_PASSWORD:\s*\S+|NEO4J_PASSWORD:\s*\S+" docker-compose.yml || true
- docker compose config >/dev/null

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: remove hardcoded secrets
- Commit B: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: finalize task summary

## Summary
- Replaced hardcoded compose secrets with env-substitution defaults for Postgres, Neo4j auth, and Guardian API key.
- Added docker-compose override vars to `.env.example` and `.env.template`.
- Checks:
  - `rg -n "GUARDIAN_API_KEY:|POSTGRES_PASSWORD:|NEO4J_PASSWORD:|OPENAI_API_KEY:" docker-compose.yml`
  - `rg -n "GUARDIAN_API_KEY:\s*[0-9a-f]{16,}|POSTGRES_PASSWORD:\s*\S+|NEO4J_PASSWORD:\s*\S+" docker-compose.yml || true`
  - `docker compose config >/dev/null`
- Git status: `git status --porcelain -uall` shows only allowed files pending finalize commit.
- Commit mode: two-phase.
- Implementation commit: `94c10071`.
- Finalize commit: pending.
- Campaign mapping requirement: `TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE -> [94c10071, <commitB>]`.
