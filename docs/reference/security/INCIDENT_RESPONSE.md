# Secret Incident Response Playbook

This playbook defines the Codexify response flow when credentials are exposed in source control, logs, or artifacts.

## 1) Identify Compromised Credentials
Treat credentials as compromised if they appear in any commit, PR diff, CI artifact, screenshots, or shared logs.

High-risk examples:
- OAuth client secrets (`client_secret*.json`)
- OAuth refresh/access tokens (`token.json`)
- API keys (`GUARDIAN_API_KEY`, provider keys)

## 2) Rotation Checklist (Operational)
Perform these actions manually in provider consoles and secret managers:
1. Revoke compromised tokens (refresh + access).
2. Rotate client secrets and API keys.
3. Update environment/secret manager values.
4. Restart services that consume rotated values.
5. Confirm old credentials are invalid.

Important:
- Do not automate real credential rotation in repository scripts.
- Assume any historical leaked value is permanently exposed.

## 3) Rewrite Git History (Destructive)
Preferred method: `git filter-repo`

Example removal command:
```bash
git filter-repo \
  --path guardian/secrets/client_secret_oauth.json \
  --path guardian/secrets/token.json \
  --invert-paths
```

After rewrite:
1. Force-push rewritten branches/tags.
2. Invalidate old clones and CI caches.
3. Require teammates to reclone or hard-reset to rewritten history.

## 4) Post-Incident Verification Checklist
Run these checks after rotation and rewrite:
1. Repo grep scan for known secrets/paths.
2. Pre-commit full scan (`pre-commit run --all-files`).
3. Hosted secret scanning dashboard (for example GitHub secret scanning) shows no active alerts.
4. Confirm no live credentials remain in docs/reference/operator/examples.

## 5) Forbidden Paths
Never commit these paths. If committed, treat associated credentials as compromised immediately.
Never commit these paths; they must be treated as compromised if committed.

- `guardian/secrets/`
- `**/token.json`
- `**/client_secret*.json`
- `.env` and downloaded OAuth client credential files
