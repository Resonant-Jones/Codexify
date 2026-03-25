# Codexify Audit — Active Remediation Targets

## Current Focus

### Durability & Recovery

- Define Redis outage behavior
- Define replay semantics for chat / ingestion / cron
- Ensure idempotency coverage across execution paths

### Tool Execution Consistency

- Reduce reliance on legacy /tools
- Move toward durable command-bus execution
- Eliminate process-local job state

## Frozen Domains (no expansion)

- Core Loop Integrity
- Primitive Stability
- Observability

No new features in these domains until weakest domains reach >= 2
