# Persona Studio Backend Authority Browser Proof — BLOCKED

Date: 2026-09-06

## Scope and source state

- Repository: `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`
- Branch: `feature/persona-studio`
- Implementation HEAD: `718288b5d9d913ec862848540b39f02ac2205e33`
- Initial worktree: clean; ahead 14 / behind 0 against the local upstream ref.
- Governing contract: [ADR-082](../../adr/082-persona-profile-manifest-and-binding-authority.md).
- This attempt is a read-only runtime preflight, not authenticated browser proof.

## Runtime and authentication posture

The documented default local Compose backend at `http://127.0.0.1:8888`
was unreachable. An existing private-preview Compose stack was available
through `http://127.0.0.1:8081`. Its `/health` response identified:

- supported profile: `v1-whooshd-deepseek-web`, version 1;
- profile validation: valid, no mismatches;
- selected provider: local;
- release hold: true;
- `auth` route label: enabled;
- `persona_profiles`: absent from both declared and mounted route labels.

`config-and-ops.md` assigns normal user login/session operation to this
private-preview profile; static API keys cannot substitute for remote user
identity. No credentials were read, copied, persisted, or supplied in this
attempt. No authenticated account or proof Persona was selected.

The live backend container's Compose working-directory label was
`/Volumes/Dev_SSD/Codexify-main`, not this task's worktree. No equivalence of
its deployed code with the implementation HEAD is claimed.

## Commands and observations

Repository precondition commands:

```bash
git branch --show-current
git rev-parse HEAD
git status --short --branch --untracked-files=all
git rev-list --left-right --count '@{upstream}...HEAD'
```

Runtime inventory:

```bash
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect --format '{{.Name}} {{index .Config.Labels "com.docker.compose.project.working_dir"}} {{range .Mounts}}{{if eq .Destination "/app"}}{{.Source}} -> {{.Destination}}{{end}}{{end}}' codexify_private_preview-backend-1
```

The existing backend, database, Redis, and chat worker were running; Docker
reported backend/database/Redis healthy. The coding and account-import workers
were restarting. Those unrelated workers were not repaired or used as the
blocking evidence for this Persona proof.

The documented startup command is `docker compose up --build`. It was not
run: an existing runtime was inspected first, and route preflight reached an
explicit task stop condition before any runtime change.

The documented health endpoints were probed with this command (responses
were filtered to non-secret status/profile fields):

```bash
python3 - <<'PY'
import urllib.request, urllib.error, json
for base in ['http://127.0.0.1:8888','http://127.0.0.1:8081']:
 for path in ['/ping','/health','/health/chat','/health/llm']:
  try:
   with urllib.request.urlopen(base+path,timeout=8) as r:
    data=r.read(); out={'url':base+path,'status':r.status}
    try:
     d=json.loads(data)
     out['health']={k:d[k] for k in ['ok','status','supported_profile','supported_profile_id','auth_mode'] if k in d}
    except (ValueError,TypeError):out['json']=False
    print(json.dumps(out))
  except Exception as e:print(json.dumps({'url':base+path,'error_type':type(e).__name__,'status':getattr(e,'code',None)}))
PY
```

| Endpoint | Port 8888 | Port 8081 |
| --- | --- | --- |
| `/ping` | URLError; no HTTP response | HTTP 200, non-JSON; not counted as backend proof |
| `/health` | URLError; no HTTP response | HTTP 200, status ok; profile as above |
| `/health/chat` | URLError; no HTTP response | HTTP 200, ok true, status healthy |
| `/health/llm` | URLError; no HTTP response | HTTP 200, status ok |

Persona route preflight:

```bash
python3 - <<'PY'
import json,urllib.request,urllib.error
base='http://127.0.0.1:8081'
for path in ['/api/persona-profiles','/openapi.json']:
 try:
  with urllib.request.urlopen(base+path,timeout=8) as r:
   d=json.load(r)
   print(json.dumps({'path':path,'status':r.status,'persona_paths':[p for p in d.get('paths',{}) if 'persona-profiles' in p]}))
 except urllib.error.HTTPError as e: print(json.dumps({'path':path,'status':e.code}))
 except Exception as e: print(json.dumps({'path':path,'error_type':type(e).__name__}))
PY
```

Results:

- `GET /api/persona-profiles`: HTTP 404.
- `GET /openapi.json`: HTTP 200; zero paths containing `persona-profiles`.
- Together with the live mounted-label inventory, this establishes that the
  required Persona route surface is unavailable in this runtime. A successful
  health response does not qualify the requested save/readback path.

Read-only source inspection found registration under `persona_profiles` and
`CODEXIFY_ENABLE_PERSONA_PROFILE_ROUTES` in `guardian/guardian_api.py`.
`guardian/core/supported_profile.py` and `config-and-ops.md` define unlisted
route labels as quarantined. This is source context, not authorization to
change a live profile, enable a flag, or restart services.

## Proof result

**BLOCKED:** the available authenticated-profile runtime does not expose the
required Persona Profile route surface. The brief explicitly requires stopping
at that boundary without repairing product or runtime/harness configuration.

| Required evidence | Result |
| --- | --- |
| Authenticated Playwright reaches Persona Studio | Not attempted after route preflight stop |
| Reusable account-owned proof profile ID | Not established; no profile created or modified |
| Real POST/PATCH acknowledgement | Not attempted |
| Initial/final canonical revision | Not observed; none fabricated |
| Manifest readback equality | Not proven |
| Fresh-browser hydration | Not proven |
| Offline cached startup / no pre-hydration PATCH | Not exercised; absence of traffic in preflight is not this proof |
| Recovery after hydration | Not proven |
| Focused Playwright result | Not run; 0 executed, no PASS or skip-based closure claimed |

The focused spec was not added because the required runtime stop condition
was reached before browser execution. `00-current-state.md` remains unchanged
and continues to describe mocked state/component proof only. Pi inference was
not used: no independent delegated work was needed after the preflight stop.

## Validation and boundaries

- `python3 scripts/validate_docs.py`: PASS.
- `git diff --check`: PASS.
- `git diff --cached --check`: PASS before commit.
- Only this receipt changed. No production source, runtime configuration,
  authentication behavior, Persona profile, binding, thread pin, capability
  enforcement, or backend semantics changed.
- ADR-082 invariants remain intact; no new ADR or release/support expansion.
- Warnings: unrelated restarting coding/account-import workers; different
  deployed checkout lineage. Neither was repaired or claimed qualified.
- Blocking failure: Persona routes absent on the available live runtime.

## Smallest prerequisite

Provide an explicitly authorized runtime/profile deployment that exposes
`persona_profiles` under its existing account-authentication boundary, with
backend and frontend lineage verified for the intended implementation. Any
route-profile/configuration change and restart belongs to that prerequisite,
not this proof task. Then resume the single focused browser save/readback,
offline-startup, and recovery proof using an authenticated operator account.
