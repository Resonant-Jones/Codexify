# Private-preview live local origin proof

Date: 2026-08-11

## 1. Scope

This architecture-impact task was to recreate only the private-preview `frontend`
service from the repaired durable Compose source, prove that its running
container no longer receives server-only credentials, and prove the existing
loopback private-preview origin remains healthy.

## 2. Workflow classification

- Execution lane: architecture-impact
- Task kind: live runtime activation and credential-isolation proof
- Evidence posture: runtime container inspection, live reachability, contract tests

## 3. ADR impact

Classification: Aligned with existing ADR(s)

Governing ADRs:
- ADR-039 Operator / User Access Boundary
- ADR-040 Network Profile Topology Resolution Contract
- ADR-052 Whoosh'd Gemma and Approved DeepSeek Startup Profile
- ADR-061 Capability-Oriented Mesh Architecture

Reason: This task was to activate and prove the already-accepted frontend/server
credential boundary in the running private-preview runtime. It does not change
provider policy, identity authority, public topology, routing doctrine, or
account semantics.

## 4. Durable promotion commit

```
ad69d2108254bac5da945ce5f7d0eb43411fec5c
```

Confirmed: `git show --no-patch --oneline ad69d2108254bac5da945ce5f7d0eb43411fec5c`

Output:
```
ad69d2108 Promote private preview frontend isolation
```

## 5. Task branch and pre-task HEAD

- Task branch: `codex/stage2j-r5f-r2-live-replay`
- Pre-task HEAD: `ad69d2108254bac5da945ce5f7d0eb43411fec5c`
- `git diff --check`: clean (no merge conflicts)

## 6. Running Compose project ownership proof

Command:
```
docker ps --filter label=com.docker.compose.project=codexify_private_preview --format '{{.Names}}'
```

Result: **No output — no running `codexify_private_preview` containers.**

Command:
```
docker ps --filter label=com.docker.compose.project=codexify_private_preview --format '{{.Label "com.docker.compose.project.working_dir"}}' | sort -u
```

Result: **No output — no working directory label available.**

Broader inspection:
```
docker ps --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}' | grep -i codex
```

Found running `codexify_tester` project (11 containers) but zero `codexify_private_preview` containers.

A `codexify_tester` project exists but is not the target `codexify_private_preview` project. The task scope is strictly limited to frontend-only recreation of an already-running private-preview project.

## 7. Pre-activation service state

**Not reached.** A running `codexify_private_preview` project is a prerequisite for capturing service state. No pre-activation container IDs were captured.

## 8. Pre-activation backend/chat health

**Not reached.** Health checks require a running private-preview project.

## 9. Frontend recreation result

**Not performed.** No running `codexify_private_preview` project exists to mutate.

## 10. Frontend container identity change

**Not applicable.** No recreation was possible.

## 11. Running frontend DEEPSEEK_API_KEY isolation result

**Not reached.** Requires a running frontend container from the `codexify_private_preview` project.

## 12. Running frontend Guardian server-secret isolation result

**Not reached.**

## 13. Running frontend Vite Guardian-key isolation result

**Not reached.**

## 14. Backend non-recreation result

**Not reached.**

## 15. Worker-chat non-recreation result

**Not reached.**

## 16. Private-preview-origin recovery result

**Not reached.**

## 17. Whether origin recreation was required

**Not applicable.**

## 18. Live published-port isolation result

**Not reached.**

## 19. Canonical reachability validator result

**Not reached.**

## 20. Direct root/health/chat/LLM result

**Not reached.**

## 21. Focused preview test result

**Not reached.**

## 22. Warning summary

No warnings. The task halted cleanly at the first verifiable gate.

## 23. Durable environment preservation result

Confirmed before task halt:

- `.env.private-preview` exists: **PASS**
- `.env.private-preview` mode: **600** (PASS)
- `.env.private-preview` ignored by `.gitignore:13:.env.*`: **PASS**
- `.env.private-preview` not tracked: **PASS**
- Contents not inspected: **PASS**

## 24. Repository/source preservation result

Confirmed before task halt:

- `git status --short`: only untracked `.worktrees/render-relay-codexify/` (pre-existing, unrelated)
- No tracked source, Compose, test, or script files modified: **PASS**
- `docker-compose.private-preview.yml` contains the repaired `env_file: !reset []` under `frontend`: **PASS**
- `docker-compose.yml` unchanged: **PASS**
- `git diff --check`: clean: **PASS**

## 25. Cloudflare untouched confirmation

**Cloudflare: untouched.** No Cloudflare Tunnel, DNS, or Access changes were attempted or made.

## 26. DNS untouched confirmation

**DNS: untouched.**

## 27. Cloudflare Access untouched confirmation

**Cloudflare Access: untouched.**

## 28. Render untouched confirmation

**Render: untouched.**

## 29. Tailscale untouched confirmation

**Tailscale: untouched.**

## 30. cloudflared untouched confirmation

**cloudflared: untouched.** No cloudflared process was started, stopped, or modified.

## 31. Secret/exposure review

No secrets were printed, hashed, fingerprinted, or exposed. The `.env.private-preview` file was never read. No container environment variables were inspected. No credential values appear in this proof artifact.

## 32. What this proves

- The durable checkout at `/Volumes/Dev_SSD/Codexify-main` contains the promoted secret-isolation repair at commit `ad69d2108254bac5da945ce5f7d0eb43411fec5c`.
- The `codexify_private_preview` Compose project is **not currently running**.
- A distinct `codexify_tester` project is running but is not the target project.
- `.env.private-preview` remains mode 600, ignored, and untracked.
- No tracked files were modified.
- No infrastructure was touched.

## 33. What this does not prove

- Live frontend secret isolation in a running container.
- Live local origin reachability after frontend activation.
- Backend/worker-chat non-recreation after frontend replacement.
- Published-port isolation in the private-preview runtime.
- Cloudflare/public-preview publication health.
- Any runtime behavior of the `codexify_private_preview` project.

## 34. Final classification

**NEXT_PROOF_NEEDED**

## 35. Exact next gate

**Start the `codexify_private_preview` Compose project from the durable checkout at `/Volumes/Dev_SSD/Codexify-main` before resuming this live local origin proof.**

Exact blocker:

> "The private-preview runtime is not currently running; full runtime startup is outside this frontend-only activation task."

The failing live-runtime seam is: **Compose project `codexify_private_preview` is not running.**

Recommended next atomic task:

A new Architecture-Impact task that brings up the full `codexify_private_preview` Compose project from the durable checkout at `/Volumes/Dev_SSD/Codexify-main` using the repaired overlay sources. This includes:

1. Start all private-preview services using the existing `.env.private-preview`.
2. Prove backend, worker-chat, PostgreSQL, Redis, Neo4j, and Whoosh'd reach healthy state.
3. Prove `127.0.0.1:8081` is reachable.
4. Prove frontend, `/health`, `/health/chat`, and `/api/health/llm`.
5. Do not publish through Cloudflare.
6. Do not modify any source file, Compose file, `.env.private-preview`, ADR, test, or script.

After that startup task succeeds, this live local origin proof task (or its successor) can resume from Phase 3 with a running private-preview project.
