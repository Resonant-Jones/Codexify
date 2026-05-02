# Codexify Beta Authorization

This guide is for the public WebUI beta bundle.

Use it if the browser opens but the app shows authentication or degraded health warnings on first launch.

## What Runs Where

- WebUI: `http://localhost:3000`
- Backend: `http://localhost:8888`

## First Launch Authorization

The browser and the backend must use the same `GUARDIAN_API_KEY`.
For the localhost beta bundle, `VITE_GUARDIAN_API_KEY` should be set to the same value so the browser can authenticate too.

On first launch, the WebUI may show `Authentication required` until the browser picks up the same key that the backend is using.

If `Codexify-Beta/.env` still contains:

```env
GUARDIAN_API_KEY=replace-with-long-random-value
```

replace it before starting the bundle.

## Generate a Key

Run:

```sh
python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

## Set the Key in `.env`

Update `Codexify-Beta/.env` to include:

```env
GUARDIAN_API_KEY=<paste-generated-key-here>
VITE_GUARDIAN_API_KEY=<paste-generated-key-here>
LOCAL_API_KEY=local
```

## Restart After Editing `.env`

After saving `.env`, restart the bundle:

```sh
docker compose down
docker compose up -d
```

## Wait for Health

Give the worker layer time to start:

```sh
sleep 20
curl -sS http://localhost:8888/health/chat
```

## What Healthy Looks Like

- `GET /health` returns `status: ok`
- `GET /health/chat` returns `status: healthy`
- `GET /api/health/llm` returns `status: ok`
- `http://localhost:3000` opens Codexify

## Troubleshooting

### WebUI opens but says `Authentication required`

- Check `Codexify-Beta/.env` and confirm `GUARDIAN_API_KEY` is set to a real generated key.
- Confirm the backend and browser are using the same key.
- Restart the bundle after editing `.env`.

### Settings shows `apiKeyPresent=false`

- The browser has not picked up the same `GUARDIAN_API_KEY` as the backend.
- Update `.env`, restart the bundle, then refresh the page.

### Settings shows `failure: chat_unhealthy`

- Wait 20 to 30 seconds after `docker compose up -d` before deciding the worker is unhealthy.
- Then re-run:

```sh
curl -sS http://localhost:8888/health/chat
```

### `/health/chat` says worker heartbeat missing immediately after startup

- This can happen during the first worker startup window.
- Wait 20 to 30 seconds after `docker compose up -d`, then check again.

### `http://localhost:3000` returns `X-Powered-By: Next.js`

- Another local dev server is already using port `3000`.
- Stop the other server, then restart the beta bundle.

### Ports `3000` or `8888` are already in use

- Stop the process or container using the port.
- Then rerun:

```sh
docker compose down
docker compose up -d
```
