# Browser Host Guardian attachment integration proof

Status: **passed**

This sanitized packet proves explicit local Browser Host configuration, trusted-main-process one-use grant consumption through the development Guardian adapter, no reusable Guardian credential in Electron, preview before separate attachment, accepted non-durable receipt, local replay rejection, wrong-instance and expired-grant rejection, disabled-adapter failure without stub fallback, transport failure without retry, deterministic-stub regression, and cleanup.

Guardian negotiation remains deterministic-stub-backed. This packet does not claim supported release, production authentication, durable persistence, packaging, signing, updater, or release behavior.

- Repository commit under test: 191e04bd21e0b677e77442c0cf8b95014626a253
- Adapter prerequisite: 191e04bd21e0b677e77442c0cf8b95014626a253
- Accepted request count: 1
- Accepted HTTP status: 202
- Persistence outcome: not_persisted
- Second attempt: local rejection, network requests 0
- Wrong-instance / expired / disabled-adapter results: 403 / 409 / 404
- Transport failure result: no HTTP status, no retry, no fallback
- Cleanup: passed
