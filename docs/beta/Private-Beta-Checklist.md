# Private Beta Checklist

Use this before sharing the macOS DMG with trusted testers.

## Release Checklist

- [ ] Confirm the repo is clean.
- [ ] Confirm the current commit hash.
- [ ] Rebuild the final app and DMG.
- [ ] Confirm the `/Applications/Codexify.app` timestamp after install.
- [ ] Confirm the packaged runtime starts.
- [ ] Confirm one local `hello` response.
- [ ] Rotate or regenerate the local beta `GUARDIAN_API_KEY` before sharing if needed.
- [ ] Confirm no real API keys are present in the docs.
- [ ] Confirm the DMG is uploaded to Google Drive.
- [ ] Upload the docs in `docs/beta/` beside the DMG.
- [ ] Send testers the right track instructions.
- [ ] Ask testers for screenshots of failures.
- [ ] Record tester feedback.

## Do Not Share Yet

- [ ] Do not send this to public forums.
- [ ] Do not send it to users who expect a polished installer.
- [ ] Do not send cloud unlock instructions to testers who are not comfortable with API keys.
- [ ] Do not present advanced unlocks as the default path.

## Tester Packet Contents

Make sure the private Drive folder includes:

- The DMG
- `README-FIRST.md`
- `Known-Issues.md`
- `Tester-Tracks.md`
- `Cloud-Model-Unlock.md`
- `Power-User-Comparison.md`
- `Private-Beta-Checklist.md`

## Notes To Capture Before Sending

- Which testers are on Track A
- Which testers are on Track B
- Which testers are on Track C
- Which testers need follow-up
- Which testers should not receive cloud instructions

## Final Reminder

Keep the beta local-first by default.

Cloud unlock is optional and should stay explicit.
