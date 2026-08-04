# Guardian-issued attachment grant contract proof

Status: **passed**

This sanitized packet proves the versioned request/response contract and pure Guardian-owned one-use issuer/consumer seam. It uses a synthetic authorized context, no network, no Guardian route, no production credential, and process-local digest-only storage. It does not claim live Guardian issuance, Browser Host transport, persistence, or release qualification.

- Commit: `fc7574246eb05259652daeffc65c22bc0d53d896`
- Contract package: `0.2.0`
- Authorization scheme: `browser_host_attachment_grant`
- TTL: `30`–`300` seconds
- Allowed uses: `1`
- Retention: `ephemeral`
- Bearer retained raw: `false`
- Reusable Guardian credential: `false`
- Route/network/persistence/release: `false`/`false`/`false`/`false`
