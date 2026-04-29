# Tester Tracks

Pick the track that matches your comfort level.

The default path is local-first and local-only.

## Track A: Gentle Local Beta

Best for:

- Non-technical testers
- Busy-life testers who want cognitive offload
- Anyone who just wants to see whether the app opens and chats

What to do:

1. Use the DMG as shipped.
2. Do not edit config unless we ask you to.
3. Open the app.
4. Send a simple message.
5. Reopen the app and check that the thread is still there.

What we are testing:

- Install
- Open
- Chat
- Reopen
- Thread persistence

Goal:

- Does Codexify reduce friction instead of adding it?

## Track B: Cloud Convenience Beta

Best for:

- Testers with limited hardware
- Testers who still want usable responses even if local inference is slow

What to do:

1. Follow the local install first.
2. Add the optional cloud env settings in `~/Codexify/.env`.
3. Use your own API key unless you were given a temporary key.
4. Test chat response quality and basic reliability.

Important:

- Cloud routing is opt-in.
- Cloud routing may send prompt or content data to the provider.
- Billing and rate limits may apply.
- Do not use this track unless you are comfortable with API keys and cloud data routing.

Goal:

- Does Codexify stay usable when inference is routed to a cloud model?

## Track C: Power User Comparison Beta

Best for:

- Technical testers
- Power users
- People willing to compare local and cloud paths directly

What to do:

1. Test the local path first.
2. Test one cloud path if you are comfortable doing so.
3. Compare speed, quality, reliability, privacy comfort, model selection, and failure modes.
4. Record what felt better and what felt worse.

Goal:

- Help us decide where local-first is enough and where cloud routing actually helps.

## If You Are Unsure

Choose Track A.

That is the safest and simplest path.
