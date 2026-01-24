# TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: Remove hardcoded secrets from docker-compose.yml

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Remove any hardcoded secrets from docker-compose.yml and ensure secrets are env-driven.

### Expected Output
- docker-compose.yml has no literal secret values committed.
- docker compose config renders without errors.

## Allowed Files
- docker-compose.yml
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md
- docs/*.md (optional docs-only if needed)

## Checks to Run
- rg -n "GUARDIAN_API_KEY|OPENAI_API_KEY|GROQ_API_KEY|ANTHROPIC_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD|POSTGRES_USER|REDIS_PASSWORD" docker-compose.yml
- rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" docker-compose.yml
- docker compose config >/tmp/codexify.compose.rendered.txt
- rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" /tmp/codexify.compose.rendered.txt || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: remove hardcoded secrets
- Commit B: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: finalize task summary

## Summary
- Removed hardcoded defaults for Postgres and Neo4j secrets in docker-compose and re-used env-sourced values in DSNs.

## Checks Run
- `rg -n "GUARDIAN_API_KEY|OPENAI_API_KEY|GROQ_API_KEY|ANTHROPIC_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD|POSTGRES_USER|REDIS_PASSWORD" docker-compose.yml`
- `rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" docker-compose.yml`
- `docker compose config >/tmp/codexify.compose.rendered.txt` (warns about POSTGRES_PASSWORD unset)
- `rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" /tmp/codexify.compose.rendered.txt || true`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending finalize commit.

## Commits
- Commit A (implementation): `202c1aaf`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE -> [202c1aaf, ]
