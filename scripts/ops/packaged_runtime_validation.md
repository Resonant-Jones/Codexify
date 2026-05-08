# Packaged Runtime Validation Script

This document describes the `reset_and_validate_packaged_runtime.py` script, which automates the "blank machine rehearsal" for the Codexify packaged macOS app (DMG).

## Purpose

When distributing a DMG to beta testers, you need to verify that:
1. First-run experience is clear on machines without Docker/Ollama
2. Dependencies are properly detected
3. Error states are legible and actionable
4. Recovery behavior works when dependencies become available

This script lets you test that repeatedly without manually cleaning up your development environment.

---

## What This Script Resets

The script manages these Codexify runtime resources:

| Resource | Action | Flag |
|----------|--------|------|
| Docker Compose services | Stops via `docker compose down` | Default |
| Docker containers | Removes with `docker rm -f` | Default |
| Docker volumes | Removes with `docker volume rm` | `--prune-volumes` |
| Docker images | Removes with `docker rmi` | `--prune-images` |
| Ollama (macOS) | Graceful quit via `osascript` | Default (unless `--skip-ollama`) |

---

## What This Script Does NOT Reset

For safety, this script deliberately **does not** touch:

| Protected Resource | Reason |
|--------------------|--------|
| Git repository | Source code must never be accidentally deleted |
| `.env` files | Environment configuration should persist |
| User files in home directory | Unrelated developer files are protected |
| Non-Codexify Docker resources | Only removes resources matching `codexify` or `guardian` patterns |
| System services | Only manages Ollama gracefully on macOS |

---

## Safety Features

1. **Requires explicit confirmation**: The `--confirm` flag must be provided before any destructive action
2. **Prints before execution**: Every action is printed before running (dry-run mode by default)
3. **Conservative resource matching**: Docker resources must match `codexify` or `guardian` patterns to be removed
4. **Graceful Ollama quit**: Uses `osascript` instead of force-killing processes
5. **No hard failures**: Missing Docker/Ollama are treated as expected validation states, not errors

---

## Quick Reference

### Dry Run (Recommended First)

```bash
python3 scripts/ops/reset_and_validate_packaged_runtime.py
```

This prints all planned actions without executing them.

### Full Clean Validation

```bash
python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --prune-images --prune-volumes
```

This performs the most aggressive cleanup.

### Skip Docker/Ollama, Just Launch App

```bash
python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --skip-docker --skip-ollama --launch-app
```

### Get Minimax Observation Prompt

```bash
python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --minimax-notes
```

---

## Flag Reference

| Flag | Description |
|------|-------------|
| `--confirm` | **Required** to execute destructive actions |
| `--prune-images` | Remove Codexify-related Docker images |
| `--prune-volumes` | Remove Codexify-related Docker volumes |
| `--skip-docker` | Skip all Docker Compose management |
| `--skip-ollama` | Skip Ollama management |
| `--launch-app` | Launch the packaged app after reset |
| `--app-path PATH` | Path to app bundle (default: `/Applications/Codexify.app`) |
| `--minimax-notes` | Print Minimax observation prompt |

---

## Usage Scenarios

### Scenario 1: Testing DMG First-Run on Clean Machine

1. Ensure you have Docker and Ollama installed on your machine
2. Run the full cleanup:
   ```bash
   python3 scripts/ops/reset_and_validate_packaged_runtime.py --confirm --prune-images --prune-volumes
   ```
3. Verify Docker/Ollama are in the desired test state (installed or removed)
4. Launch the packaged app:
   ```bash
   open /Applications/Codexify.app
   ```
5. Observe the first-run experience
6. Make Docker/Ollama available and verify recovery
7. Repeat as needed

### Scenario 2: Share DMG with Beta Testers

Before sharing the DMG:

1. Run the script with `--minimax-notes` to get observation prompts
2. Document expected behaviors using the validation checklist
3. Create a README for beta testers explaining:
   - What dependencies the app requires
   - How to install Docker and Ollama
   - What error states they might see
   - How to report issues

### Scenario 3: Verify Error States Are Clear

1. Run cleanup to reset state
2. Remove Docker (if testing "Docker missing" state)
3. Launch the app and verify error messages are actionable
4. Install Docker and verify the app detects and recovers
5. Repeat for Ollama

---

## Validation Checklist

After launching the app, verify these observations:

### Docker Status Handling
- [ ] If Docker is missing: Clear message about Docker requirement
- [ ] If Docker is offline: Legible offline/unreachable state
- [ ] If Docker is available: Runtime pull/startup begins automatically

### Ollama Status Handling
- [ ] If Ollama is missing: Clear message about Ollama requirement
- [ ] If Ollama is offline: Legible offline/unreachable state
- [ ] If Ollama is available: Model warming begins automatically

### Health Recovery
- [ ] Health surfaces eventually recover to ready/degraded states
- [ ] Check endpoints: `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`

### First Chat Experience
- [ ] First chat send completes OR reports clear blocked/degraded state
- [ ] Error messages are actionable for beta testers

---

## Common Issues and Solutions

### "Docker daemon is not running"
- Start Docker Desktop and wait for the whale icon to stabilize
- Run `docker info` to verify daemon is reachable

### "Ollama is not installed"
- Install from https://ollama.ai
- Run `ollama --version` to verify installation

### "App fails to launch"
- Verify the app bundle exists at the specified path
- Check Console app for crash logs
- Try launching from terminal: `open /Applications/Codexify.app`

### "Compose down fails"
- Check if Docker daemon is reachable: `docker info`
- Check for locked containers/volumes
- Manually remove stuck resources: `docker rm -f <container>`

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (planned or executed) |
| 1 | Error (script failure, not validation state) |

---

## Script Location

```
scripts/ops/reset_and_validate_packaged_runtime.py
```

This script uses only Python standard library (`argparse`, `subprocess`, `pathlib`, `shlex`, `platform`, `os`, `sys`).

---

## Related Documentation

- [Docker Compose Runtime Configuration](../docker-compose.runtime.yml)
- [Packaged App Architecture](../../docs/architecture/)
- [DMG Distribution Guide](../../docs/distribution/)
