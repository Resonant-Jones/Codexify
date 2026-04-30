# Private Beta Checklist

Use this before sharing either private beta bundle.

## macOS Desktop Path

- [ ] Confirm the repo is clean.
- [ ] Confirm the current commit hash.
- [ ] Rebuild the final app and DMG.
- [ ] Confirm the `/Applications/Codexify.app` timestamp after install.
- [ ] Confirm the packaged runtime starts.
- [ ] Confirm one local `hello` response.
- [ ] Rotate or regenerate the local beta `GUARDIAN_API_KEY` before sharing if needed.
- [ ] Confirm `~/Codexify/.env` is the editable config source for the desktop path.
- [ ] Confirm no real API keys are present in the docs.
- [ ] Confirm the DMG is uploaded to Google Drive.
- [ ] Upload the docs in `docs/beta/` beside the DMG.
- [ ] Send testers the macOS desktop track instructions.
- [ ] Ask testers for screenshots of failures.
- [ ] Record tester feedback.

## WebUI Docker Path

- [ ] Confirm the repo is clean.
- [ ] Confirm the current commit hash.
- [ ] Build the webUI Docker bundle.
- [ ] Confirm `docker compose -f docker-compose.webui-runtime.yml up -d` starts the stack.
- [ ] Confirm `http://localhost:3000` responds with HTML.
- [ ] Confirm the backend health endpoints pass.
- [ ] Confirm one local `hello` response through the browser bundle.
- [ ] Confirm document and image uploads work through the browser bundle.
- [ ] Confirm the repo root `.env` file is the editable config source for the Docker bundle.
- [ ] Confirm no real API keys are present in the docs.
- [ ] Upload the docs in `docs/beta/` beside the bundle instructions.
- [ ] Send testers the webUI track instructions.
- [ ] Ask testers for screenshots of failures.
- [ ] Record tester feedback.

## Do Not Share Yet

- [ ] Do not send this to public forums.
- [ ] Do not send it to users who expect a polished installer.
- [ ] Do not send cloud unlock instructions to testers who are not comfortable with API keys.
- [ ] Do not present advanced unlocks as the default path.

## Tester Packet Contents

Make sure the private Drive folder includes:

- The DMG or the webUI bundle instructions, depending on the tester path
- `README-FIRST.md`
- `Known-Issues.md`
- `Tester-Tracks.md`
- `Cloud-Model-Unlock.md`
- `Power-User-Comparison.md`
- `Private-Beta-Checklist.md`

## Notes To Capture Before Sending

- Which testers are on the macOS desktop path
- Which testers are on the webUI Docker path
- Which testers need follow-up
- Which testers should not receive cloud instructions

## Final Reminder

Keep the beta local-first by default.

Desktop and webUI both use the same local backend runtime.

Cloud unlock is optional and should stay explicit.
