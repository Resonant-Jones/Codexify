# Packaged macOS qualification namespace

This opt-in proof mode is subordinate to ADR-101 (Proposed). It is not a supported installation profile or a release-readiness claim. The supported local Compose path and overall HOLD remain governed by `docs/architecture/00-current-state.md`.

Launch the completed, structurally verified `.app` executable with one explicit identity:

```sh
CODEXIFY_DESKTOP_QUALIFICATION_ID=installed-proof-20261005 \
  /absolute/path/Codexify.app/Contents/MacOS/Codexify
```

Use 1–48 lowercase letters, digits, or hyphens, beginning and ending with a letter or digit. Reuse the same ID for persistence proof; use a new ID for a fresh qualification. This mode requires a packaged macOS application and macOS 14 or newer. Invalid IDs, symlinked namespace paths, and unrelated listeners on derived ports stop launch before WebKit creation or runtime probes. Hash-derived ports can collide; choose another ID when ownership cannot be established. Existing containers with the exact qualification Compose project may retain ports across relaunch.

| Surface | Qualification scope |
| --- | --- |
| Packaged runtime | `~/CodexifyQualifications/<id>/runtime` |
| Desktop data and logs | `~/Library/Application Support/CodexifyQualifications/<id>` |
| WebKit | Persistent UUID derived from the ID, explicitly selected before window creation; no default-store fallback |
| Framework application identifier | `com.codexify.desktop.qualification.<id>` |
| Compose | `codexify-qualification-<id>`, explicit project and isolated `.env`; named volumes and network inherit this project |
| Host ports | Stable derived loopback ports for backend, WebUI, PostgreSQL, and Neo4j HTTP/Bolt |
| Guardian Keychain | Service `com.codexify.desktop.qualification.<id>`, account `guardian_api_key`; no ordinary-service fallback |

The data directory contains a nonsecret `qualification.json` receipt with resolved paths, ports, project, datastore UUID bytes, and credential service. This records selected configuration; actual store and runtime isolation still require observation.

The normal application's paths, WebKit setup, Compose environment, URLs, and credential service are unchanged when the control is absent. Qualification uses the existing host Docker installation, daemon, and Docker client credentials. It does not isolate the daemon or provide a security sandbox. Application configuration and credentials inherited from the launching shell are excluded from qualification Compose commands; only host Docker access and process necessities are retained. Desktop URL and credential resolution uses the isolated configuration, never ambient application credentials.

First setup generates isolated credentials and fixes the namespace and published ports. Initial inference targets an unused derived port, so ordinary host inference is not automatically discovered. Configure inference explicitly in the qualification runtime's `.env` using existing mechanisms. Repeated setup preserves that inference choice and credentials. A configuration bound to another qualification ID is rejected. Do not copy normal credentials or attach normal volumes.

## Proof sequence

1. Snapshot ordinary runtime/data/WebKit/Keychain metadata and ordinary Docker project state without exposing credentials.
2. Build current source from clean generated bundle output. If needed, ad hoc sign the completed `.app` as a proof-only post-build operation; do not change repository signing configuration.
3. Require `codesign --verify --deep --strict` and `Contents/_CodeSignature/CodeResources`. Record `spctl` separately; ad hoc rejection is expected distribution-trust evidence.
4. Launch with a fresh qualification ID. Inspect the namespace receipt and actual WebKit datastore; verify ordinary state is unchanged.
5. Bootstrap through the packaged adapter, reach `core_ready`, enter the workspace, and observe inference unavailable.
6. Explicitly configure isolated inference using existing host mechanisms; prove successful chat and create a durable test conversation.
7. Quit and relaunch with the same ID. Prove conversation and configuration persistence, and recheck ordinary state.

Stop at any independent failure or host installation/model download consent boundary. Source tests, a successful build, structural signing, and the namespace receipt do not by themselves qualify installed-app runtime behavior. No normal data cleanup, signing/notarization changes, or support promotion is authorized by this mode.
