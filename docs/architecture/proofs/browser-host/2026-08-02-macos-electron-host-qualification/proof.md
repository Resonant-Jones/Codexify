# macOS Electron host qualification

- Status: **next-proof-needed**
- Primary classification: `host_code_signing_subsystem_unavailable`
- Repository commit: `529cc38b145ce6e476fb4058d2a63a6c96fb6cd7`
- Prerequisite commits: de3924011, 529cc38b1
- Host: darwin/arm64; Electron: 43.2.0; Playwright: 1.62.1
- Apple control app passed: false
- Apple/current/clean same Code Signing subsystem error: true
- Current minimal Electron app: false
- Clean minimal Electron app: false
- Reinstall attempted: false
- Package lock changed: false
- Existing production-entry live proof: next-proof-needed
- System security modified: false
- Insecure flags used: false
- Cleanup: passed

The matrix compares an Apple-signed control app, the repository Electron bundle, and a clean isolated locked download before any repository-local repair. No Gatekeeper, SIP, quarantine, signing, trust-service, or security-database change is permitted. A `passed` status requires the existing bounded production-entrypoint live proof; static signing or Gatekeeper output alone cannot qualify the host.

This packet does not claim a real Guardian session, durable persistence, packaging, signing/notarization, updater, beta, or supported release.
