# Personal Facts Route Runtime Proof

Artifact date: 2026-04-07
Branch: `main`
HEAD commit: `3a11a881dc9115081fe712532186024f061b87ab`

## Scope

This proof covers route/runtime exposure truth for `personal_facts`.

It does not claim context injection works.
It does not claim live chat extraction works.
It does not claim frontend inbox UI exists.

## Environment

| Item | Value |
|---|---|
| Supported runtime path used | Local Docker Compose stack with `backend`, `db`, `redis`, `frontend`, `worker-chat`, `worker-document-embed`, `worker-chat-embed`, `worker-voice`, `worker-warmup`, and `neo4j` running |
| Active supported-profile state in the running backend | `null` (`app.state.supported_profile_manifest` and `app.state.supported_profile` were both null in a fresh backend process) |
| Observed runtime flags in the backend container | `CODEXIFY_SUPPORTED_PROFILE` unset, `GUARDIAN_EXPOSURE_MODE` unset, `GUARDIAN_PUBLIC_PROFILE` unset, `GUARDIAN_PUBLIC_ROUTES_FILE` unset |
| Public exposure defaults observed in backend startup logs | `mode=local_safe`, `profile=minimal_health`, `routes_file=config/public_routes.yaml` |

The health surface also returned `200` with no `supported_profile` block in `/health`, which is consistent with no active supported profile being loaded in this runtime.

## Exact Commands

Commands used to establish the proof:

```sh
git branch --show-current
git rev-parse HEAD
docker compose ps
sed -n '1,260p' guardian/routes/personal_facts.py
sed -n '1,220p' guardian/core/chatlog_postgres.py
sed -n '1,220p' guardian/core/db.py
sed -n '460,520p' guardian/core/dependencies.py
sed -n '1,220p' config/supported_profiles/v1-local-core-web-mcp.yaml
sed -n '1,220p' config/public_routes.yaml
sed -n '220,520p' guardian/guardian_api.py
docker compose exec -T backend python -c "from guardian.guardian_api import app; import json; routes=[getattr(r,'path',None) for r in app.routes if getattr(r,'path',None)]; print(json.dumps({'supported_profile_manifest': getattr(app.state,'supported_profile_manifest',None).name if getattr(app.state,'supported_profile_manifest',None) else None, 'supported_profile_state': getattr(app.state,'supported_profile',None), 'has_personal_facts_route': '/personal-facts' in routes, 'has_confirm_route': '/personal-facts/{fact_id}/confirm' in routes, 'has_dispute_route': '/personal-facts/{fact_id}/dispute' in routes, 'has_evidence_route': '/personal-facts/{fact_id}/evidence' in routes, 'has_revisions_route': '/personal-facts/{fact_id}/revisions' in routes, 'route_count': len(routes)}, sort_keys=True, default=str))"
docker compose exec -T backend python -c "from guardian.guardian_api import app; import json; schema=app.openapi(); paths=schema.get('paths',{}); result={p:list(paths[p].keys()) for p in sorted(paths) if p.startswith('/personal-facts')}; print(json.dumps({'openapi_personal_facts_paths': result, 'openapi_has_personal_facts': bool(result)}, sort_keys=True))"
docker compose exec -T backend python - <<'PY'
import json
import os
import urllib.error
import urllib.request

base = 'http://127.0.0.1:8888'
api_key = os.environ.get('GUARDIAN_API_KEY', '')
headers = {
    'X-API-Key': api_key,
    'X-User-Id': 'local_user',
    'Content-Type': 'application/json',
}

def req(method, path, headers=None, body=None):
    data = None if body is None else body.encode()
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return {
                'status': resp.status,
                'body': resp.read().decode(),
            }
    except urllib.error.HTTPError as exc:
        return {
            'status': exc.code,
            'body': exc.read().decode(),
        }
    except Exception as exc:
        return {
            'status': 'ERR',
            'error': f'{type(exc).__name__}: {exc}',
        }

out = {
    'GET /personal-facts no auth': req('GET', '/personal-facts'),
    'GET /personal-facts with auth': req('GET', '/personal-facts', headers=headers),
    'GET /personal-facts/1 with auth': req('GET', '/personal-facts/1', headers=headers),
    'POST /personal-facts/1/confirm with auth': req('POST', '/personal-facts/1/confirm', headers=headers, body='{}'),
    'POST /personal-facts/1/dispute with auth': req('POST', '/personal-facts/1/dispute', headers=headers, body='{}'),
}
print(json.dumps(out, sort_keys=True))
PY
docker compose exec -T backend python - <<'PY'
import json
import urllib.request
import os

base='http://127.0.0.1:8888'
api_key=os.environ.get('GUARDIAN_API_KEY','')
req=urllib.request.Request(base+'/health', headers={'X-API-Key': api_key})
with urllib.request.urlopen(req, timeout=10) as resp:
    payload=json.loads(resp.read().decode())
print(json.dumps(payload, sort_keys=True))
PY
docker compose logs --tail=200 backend | sed -n '1,30p'
docker compose logs --tail=200 backend | sed -n '95,120p'
docker compose logs --tail=200 backend | sed -n '185,210p'
```

## Observed Results

- `docker compose ps` showed the local stack up, including `backend`, `db`, `redis`, `frontend`, `neo4j`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, and `worker-warmup`.
- `app.routes` in a fresh backend process included `/personal-facts` and the subpaths `/personal-facts/{fact_id}`, `/personal-facts/{fact_id}/confirm`, `/personal-facts/{fact_id}/dispute`, `/personal-facts/{fact_id}/evidence`, and `/personal-facts/{fact_id}/revisions`.
- `app.openapi()` in that same backend process exposed the same `personal_facts` path set:

```json
{
  "/personal-facts": ["get", "post"],
  "/personal-facts/{fact_id}": ["get", "patch"],
  "/personal-facts/{fact_id}/confirm": ["post"],
  "/personal-facts/{fact_id}/dispute": ["post"],
  "/personal-facts/{fact_id}/evidence": ["get", "post"],
  "/personal-facts/{fact_id}/revisions": ["get"]
}
```

- No active supported profile was loaded in the running backend. The inspected backend process reported `supported_profile_manifest: null` and `supported_profile_state: null`.
- `/health` returned `200` with no `supported_profile` detail block.
- `GET /personal-facts` without auth returned `401` with body `{"detail":"Missing API key",...}`.
- `GET /personal-facts` with `X-API-Key` returned `500`.
- `GET /personal-facts/1` with `X-API-Key` returned `500`.
- `POST /personal-facts/1/confirm` with `X-API-Key` returned `500`.
- `POST /personal-facts/1/dispute` with `X-API-Key` returned `500`.
- Backend logs for the authenticated path showed:

```text
AttributeError: 'PostgresChatLogDB' object has no attribute 'get_fact'
```

- Source inspection confirmed the runtime wiring path:
  - `guardian/core/dependencies.py` initializes `chatlog_db` as `PostgresChatLogDB(db_url)` when `DATABASE_URL` is present.
  - `guardian/core/chatlog_postgres.py` is only a thin alias around `PgDB`.
  - The personal-facts methods live in `guardian/core/db.py`, while `guardian/core/pgdb.py` does not define `get_fact` / `list_facts` / the other personal-facts methods.

Observed consequence:

- The route is mounted.
- The API key guard is active.
- The endpoint is not usable in this runtime because the Postgres chatlog adapter does not implement the personal-facts methods the route calls.

## Verdict

`mounted but blocked by auth/config`

## Blocker Classification

`missing runtime dependency`

The concrete blocker is runtime wiring: authenticated requests reach `personal_facts`, but the live backend is using `PostgresChatLogDB`, which does not provide the personal-facts methods required by the route.

## Implementation Consequence

The next task must first expose or wire the personal-facts runtime path so the route can execute against a DB adapter that implements the personal-facts methods. Broker/prompt integration should wait until this runtime seam is fixed.
