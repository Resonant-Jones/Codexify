# Guardian Browser Host attachment HTTP adapter proof

- Status: `passed`
- Baseline commit under test: `87fe3257c0d0c12ad00a749b631bfeb866ddaaaf`
- Route prefix: `/dev/browser-host/v1`
- The adapter is default-disabled, development-only, and local-safe only.
- Issuance uses existing Guardian authentication; attachment consumption uses only the one-use grant.
- Accepted attachments return a content-free `202` receipt with `not_persisted`.
- Replay and expiration return `409`; scope, version, retention, confirmation, and budget rejection return `403` receipts.
- Malformed bodies preserve the grant; concurrent consumption produced exactly one success and one replay rejection.
- No bearer, bearer digest, subject, credentials, raw content, database, Redis, or external network was included in this packet.
- Production Browser Host integration and release qualification remain false.
