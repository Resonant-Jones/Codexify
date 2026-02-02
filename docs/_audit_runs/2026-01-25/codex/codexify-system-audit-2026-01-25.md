# Codexify Senior Architect System Audit

## Metadata
- Repo: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Date: 2026-01-25
- Agent/Model: OpenAI Codex (GPT-5)
- Env/Runner: local Codex CLI (zsh)
- Git Branch: chore/post-skip-hook-fixes
- Git Commit: 392fc8ba

## Executive Summary
- [RISK] Hardcoded credentials and API keys are present in the repo .env file, risking disclosure if shared or deployed as-is (FINDING-2026-01-25-001).
- [RISK] API key verification falls back to predictable defaults ("changeme", "invalid-by-default") when no key is configured, risking unauthorized access in misconfigured deployments (FINDING-2026-01-25-002).
- [RISK] Frontend can exfiltrate uploaded file contents to a configurable ingestion endpoint via env/localStorage toggles (FINDING-2026-01-25-007).
- [WARN] Migration UI calls the legacy upload route without an API key while the backend requires auth on the canonical endpoint (FINDING-2026-01-25-003).
- [WARN] README claims local-first, multi-provider support including Anthropic/DeepSeek and "data never leaves" while code shows external egress paths and fewer providers wired (FINDING-2026-01-25-013).

## Runner-Ready Findings Manifest (authoritative)
```yaml
- finding_id: FINDING-2026-01-25-001
  area: security
  severity: RISK
  title: Repo .env contains hardcoded credentials and API keys
  description: |
    The repo includes an .env file with literal credentials (PGPASSWORD, NEO4J_PASS)
    and long-lived API keys (GUARDIAN_API_KEY, VITE_GUARDIAN_API_KEY). If this
    file is distributed or committed, these values are effectively exposed.
  evidence:
    - file: .env
      lines: "L24-L66"
  relates_to_core_loop: none
  suggested_task_outcome: Replace literal secrets with placeholders and keep real secrets out of the repo.
  suggested_commands:
    - "nl -ba .env | sed -n '24,70p'"
  dependencies: []
  notes: Verify .gitignore and history to ensure no secret values are published.

- finding_id: FINDING-2026-01-25-002
  area: security
  severity: RISK
  title: API key verification allows "changeme"/"invalid-by-default" fallbacks
  description: |
    verify_api_key falls back to accepting "invalid-by-default" and "changeme"
    when no configured key is present, which can allow access in misconfigured
    deployments.
  evidence:
    - file: guardian/core/dependencies.py
      lines: "L77-L174"
  relates_to_core_loop: none
  suggested_task_outcome: Fail closed when GUARDIAN_API_KEY(S) are not set, or gate dev defaults behind an explicit flag.
  suggested_commands:
    - "nl -ba guardian/core/dependencies.py | sed -n '77,174p'"
  dependencies: []
  notes: This is most risky in production/staging if env is missing.

- finding_id: FINDING-2026-01-25-003
  area: core-loop
  severity: WARN
  title: Migration UI calls legacy upload endpoint without API key
  description: |
    The frontend posts to /upload-chatgpt-export with only X-User-Id, while the
    backend requires API key auth on the canonical /api/upload-chatgpt-export endpoint.
  evidence:
    - file: frontend/src/components/settings/SettingsView.tsx
      lines: "L146-L161"
    - file: frontend/src/components/modals/ChatGPTImportModal.tsx
      lines: "L47-L63"
    - file: guardian/routes/migration.py
      lines: "L28-L34"
  relates_to_core_loop: migration
  suggested_task_outcome: Use /api/upload-chatgpt-export and attach X-API-Key/Authorization in the UI.
  suggested_commands:
    - "rg -n \"upload-chatgpt-export\" frontend/src/components"
    - "nl -ba guardian/routes/migration.py | sed -n '28,40p'"
  dependencies: ["GUARDIAN_API_KEY"]
  notes: Playwright currently stubs to the canonical path; align UI + tests.

- finding_id: FINDING-2026-01-25-004
  area: core-loop
  severity: WARN
  title: Document uploads do not attach API key headers
  description: |
    useUploader posts to /api/media/upload/document without X-API-Key, but the
    media router enforces API key auth for all /api/media routes.
  evidence:
    - file: frontend/src/hooks/useUploader.ts
      lines: "L109-L120"
    - file: guardian/routes/media.py
      lines: "L63-L72"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Centralize API calls and include X-API-Key in document upload requests.
  suggested_commands:
    - "nl -ba frontend/src/hooks/useUploader.ts | sed -n '100,130p'"
    - "nl -ba guardian/routes/media.py | sed -n '63,72p'"
  dependencies: ["GUARDIAN_API_KEY", "VITE_GUARDIAN_API_KEY"]
  notes: Dev mode injects headers via Vite proxy; production clients will not.

- finding_id: FINDING-2026-01-25-005
  area: core-loop
  severity: WARN
  title: Image gallery/generation calls lack API key headers
  description: |
    Gallery list, image uploads, and image generation requests do not set X-API-Key
    headers, while /api/media is protected by API key auth.
  evidence:
    - file: frontend/src/components/gallery/GalleryView.tsx
      lines: "L50-L57"
    - file: frontend/src/hooks/useUploader.ts
      lines: "L70-L86"
    - file: frontend/src/components/modals/ImageGenModal.tsx
      lines: "L62-L69"
    - file: frontend/src/lib/api.ts
      lines: "L7-L25"
    - file: guardian/routes/media.py
      lines: "L63-L72"
  relates_to_core_loop: image-gallery
  suggested_task_outcome: Ensure all /api/media requests include API keys outside the dev proxy.
  suggested_commands:
    - "nl -ba frontend/src/components/gallery/GalleryView.tsx | sed -n '50,80p'"
    - "nl -ba frontend/src/components/modals/ImageGenModal.tsx | sed -n '60,75p'"
  dependencies: ["GUARDIAN_API_KEY", "VITE_GUARDIAN_API_KEY"]
  notes: Vite dev proxy injects headers only in development.

- finding_id: FINDING-2026-01-25-006
  area: core-loop
  severity: WARN
  title: Upload failure counter uses totalFailed before initialization
  description: |
    totalFailed is incremented in error handlers before it is declared,
    which throws a runtime error when an upload fails.
  evidence:
    - file: frontend/src/hooks/useUploader.ts
      lines: "L88-L166"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Define and initialize totalFailed before any increments; add a regression test.
  suggested_commands:
    - "nl -ba frontend/src/hooks/useUploader.ts | sed -n '80,170p'"
  dependencies: []
  notes: This affects both document and image uploads.

- finding_id: FINDING-2026-01-25-007
  area: sovereignty
  severity: RISK
  title: Optional ingestion endpoint can exfiltrate uploaded file contents
  description: |
    useUploader can POST base64-encoded file bytes to a configurable ingestion
    endpoint (env var or localStorage override), which enables data egress.
  evidence:
    - file: frontend/src/hooks/useUploader.ts
      lines: "L179-L193"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Gate ingestion behind explicit config and remove localStorage override or require user consent.
  suggested_commands:
    - "nl -ba frontend/src/hooks/useUploader.ts | sed -n '176,196p'"
  dependencies: ["VITE_INGESTION_ENDPOINT"]
  notes: Document the behavior if this is intended for telemetry.

- finding_id: FINDING-2026-01-25-008
  area: core-loop
  severity: WARN
  title: Document embedding defaults to OpenAI and fails without OPENAI_API_KEY
  description: |
    Document embed worker instantiates CodexifyEmbedder with default use_openai=True,
    which requires OPENAI_API_KEY and can egress to OpenAI or fail in local-only setups.
  evidence:
    - file: guardian/workers/document_embed_worker.py
      lines: "L145-L158"
    - file: guardian/runtime/embed/embedder.py
      lines: "L53-L103"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Make embedder backend explicit and default to local embeddings when configured.
  suggested_commands:
    - "nl -ba guardian/workers/document_embed_worker.py | sed -n '142,160p'"
    - "nl -ba guardian/runtime/embed/embedder.py | sed -n '53,103p'"
  dependencies: ["OPENAI_API_KEY", "CODEXIFY_USE_OPENAI"]
  notes: Align with local-first claims if OpenAI is optional.

- finding_id: FINDING-2026-01-25-009
  area: core-loop
  severity: WARN
  title: Documents UI is localStorage-backed, not using backend document list
  description: |
    AppShell seeds and persists documents in localStorage and never calls the backend
    /api/media/documents list endpoint, so persisted docs may not appear across sessions
    or clients.
  evidence:
    - file: frontend/src/components/persona/layout/AppShell.tsx
      lines: "L433-L459"
    - file: guardian/routes/media.py
      lines: "L692-L744"
  relates_to_core_loop: doc-gen
  suggested_task_outcome: Fetch documents from backend and reconcile local mock data.
  suggested_commands:
    - "nl -ba frontend/src/components/persona/layout/AppShell.tsx | sed -n '433,459p'"
    - "nl -ba guardian/routes/media.py | sed -n '692,744p'"
  dependencies: []
  notes: This affects both uploaded documents and generated documents.

- finding_id: FINDING-2026-01-25-010
  area: core-loop
  severity: WARN
  title: Local and Stability image generation providers return placeholders
  description: |
    The local and stability image providers return a 1x1 placeholder PNG and
    require a model parameter, indicating stubbed functionality.
  evidence:
    - file: guardian/image_gen/providers/local.py
      lines: "L8-L27"
    - file: guardian/image_gen/providers/stability.py
      lines: "L8-L27"
  relates_to_core_loop: image-gen
  suggested_task_outcome: Implement real provider calls or hide these options in the UI until ready.
  suggested_commands:
    - "nl -ba guardian/image_gen/providers/local.py | sed -n '8,27p'"
    - "nl -ba guardian/image_gen/providers/stability.py | sed -n '8,27p'"
  dependencies: []
  notes: OpenAI provider is implemented separately.

- finding_id: FINDING-2026-01-25-011
  area: core-loop
  severity: WARN
  title: UI expects RAG context in completion response, but backend returns only task_id
  description: |
    chat_complete returns only task_id, while the UI tries to read response.data.context.
    RAG trace is available only via a debug endpoint, not wired into the main flow.
  evidence:
    - file: guardian/routes/chat.py
      lines: "L586-L665"
    - file: guardian/routes/chat.py
      lines: "L995-L1038"
    - file: frontend/src/features/chat/GuardianChat.tsx
      lines: "L105-L128"
  relates_to_core_loop: rag
  suggested_task_outcome: Provide a supported trace retrieval path (API or event) and update UI to use it.
  suggested_commands:
    - "nl -ba guardian/routes/chat.py | sed -n '586,665p'"
    - "nl -ba frontend/src/features/chat/GuardianChat.tsx | sed -n '105,128p'"
  dependencies: []
  notes: Trace is emitted in task.completed events by chat_worker.

- finding_id: FINDING-2026-01-25-012
  area: testing
  severity: WARN
  title: Pytest ignores guardian/tests by default
  description: |
    pytest.ini excludes guardian/tests from collection and only uses testpaths=tests,
    so backend unit tests in guardian/tests are skipped by default.
  evidence:
    - file: pytest.ini
      lines: "L1-L3"
  relates_to_core_loop: none
  suggested_task_outcome: Remove the ignore or adjust testpaths to include guardian/tests.
  suggested_commands:
    - "nl -ba pytest.ini"
  dependencies: []
  notes: This can mask regressions in backend components.

- finding_id: FINDING-2026-01-25-013
  area: docs-drift
  severity: WARN
  title: README claims provider-agnostic local-first system but code shows external egress and fewer providers
  description: |
    README asserts local-first operation and provider-agnostic support (Anthropic/DeepSeek),
    but provider registry only wires OpenAI/Groq/Gemini and ai_router calls external APIs.
  evidence:
    - file: README.md
      lines: "L22-L33"
    - file: README.md
      lines: "L55-L56"
    - file: guardian/providers/registry.py
      lines: "L17-L43"
    - file: guardian/core/ai_router.py
      lines: "L12-L65"
    - file: guardian/core/ai_router.py
      lines: "L194-L231"
  relates_to_core_loop: none
  suggested_task_outcome: Align README with actual providers and data egress behavior.
  suggested_commands:
    - "nl -ba README.md | sed -n '22,60p'"
    - "nl -ba guardian/providers/registry.py | sed -n '17,43p'"
  dependencies: []
  notes: Use the data egress map to describe real behavior.

- finding_id: FINDING-2026-01-25-014
  area: security
  severity: WARN
  title: User identity is hardcoded to "default" after API key validation
  description: |
    get_current_user returns "default" regardless of API key, indicating no
    user-level isolation on authenticated requests.
  evidence:
    - file: guardian/core/dependencies.py
      lines: "L194-L199"
  relates_to_core_loop: none
  suggested_task_outcome: Map API keys to user identities or make user_id explicit in requests and enforce it.
  suggested_commands:
    - "nl -ba guardian/core/dependencies.py | sed -n '184,199p'"
  dependencies: []
  notes: Multi-user isolation is not enforced in current code paths.

- finding_id: FINDING-2026-01-25-015
  area: security
  severity: WARN
  title: Document generation endpoints lack API key enforcement
  description: |
    documents router is defined without API key dependencies, and /api/documents/generate
    accepts requests without auth, making document generation publicly accessible.
  evidence:
    - file: guardian/routes/documents.py
      lines: "L9-L20"
    - file: guardian/routes/documents.py
      lines: "L249-L254"
  relates_to_core_loop: doc-gen
  suggested_task_outcome: Require API key or auth dependency on documents routes.
  suggested_commands:
    - "nl -ba guardian/routes/documents.py | sed -n '1,30p'"
    - "nl -ba guardian/routes/documents.py | sed -n '249,270p'"
  dependencies: ["GUARDIAN_API_KEY"]
  notes: Align with other protected endpoints such as /api/media and /api/chat.
```

## System Overview

### Subsystem Status
| Subsystem | Status | Evidence |
| --- | --- | --- |
| API router and core route wiring | Implemented | guardian/guardian_api.py:L366-L404 |
| Chat completion API | Implemented | guardian/routes/chat.py:L586-L665 |
| Context broker (RAG assembly) | Implemented | guardian/context/broker.py:L12-L208 |
| RAG trace exposure to UI | Partial | guardian/routes/chat.py:L995-L1038; frontend/src/features/chat/GuardianChat.tsx:L105-L128 |
| Migration import pipeline | Partial | guardian/routes/migration.py:L28-L44; backend/rag/chatgpt_migration.py:L42-L199; frontend/src/components/settings/SettingsView.tsx:L146-L161 |
| Document upload + parsing | Partial | guardian/routes/media.py:L287-L444; guardian/services/document_parsers/pdf_text_extractor.py:L15-L59; guardian/services/document_parsers/docx_text_extractor.py:L15-L57 |
| Document embedding worker | Partial | guardian/workers/document_embed_worker.py:L145-L183; guardian/runtime/embed/embedder.py:L53-L103 |
| Documents list UI | Partial | frontend/src/components/persona/layout/AppShell.tsx:L433-L459 |
| Image upload + list | Partial | guardian/routes/media.py:L648-L689; frontend/src/components/gallery/GalleryView.tsx:L50-L76 |
| Image generation providers | Stubbed | guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27 |
| Document generation | Partial | guardian/routes/documents.py:L249-L388; frontend/src/App.tsx:L116-L171 |
| Frontend E2E harness | Implemented | frontend/src/playwright.config.ts:L22-L47 |

## Security, Privacy, and Sovereignty

### Secrets Management
- .env includes literal credentials and API keys (PGPASSWORD, NEO4J_PASS, GUARDIAN_API_KEY, VITE_GUARDIAN_API_KEY). Evidence: .env:L24-L66.

### Access Control Boundaries
- API key verification uses verify_api_key/require_api_key with fallback defaults when no key is configured. Evidence: guardian/core/dependencies.py:L77-L174.
- Media endpoints require API key via APIRouter dependency. Evidence: guardian/routes/media.py:L63-L72.
- Migration upload requires API key. Evidence: guardian/routes/migration.py:L28-L34.
- Documents router does not apply API key dependencies (public endpoints). Evidence: guardian/routes/documents.py:L9-L20 and guardian/routes/documents.py:L249-L254.
- get_current_user always returns "default" (no user isolation). Evidence: guardian/core/dependencies.py:L194-L199.

### Data Egress Map (code-evidenced)
| Flow | Destination | Data | Trigger | Evidence |
| --- | --- | --- | --- | --- |
| LLM chat to external providers | https://api.openai.com, https://api.groq.com, or LOCAL_BASE_URL | chat messages | chat_with_ai routing | guardian/core/ai_router.py:L12-L65, guardian/core/ai_router.py:L72-L109, guardian/core/ai_router.py:L194-L231 |
| OpenAI embeddings | OpenAI API via OpenAI client | document chunk text | CodexifyEmbedder use_openai | guardian/runtime/embed/embedder.py:L53-L103 |
| OpenAI image generation | OpenAI images API | prompt + model | ImageGen provider | guardian/image_gen/providers/openai.py:L14-L61 |
| Optional ingestion POST (frontend) | VITE_INGESTION_ENDPOINT or localStorage override | base64 file bytes | useUploader ingestion loop | frontend/src/hooks/useUploader.ts:L179-L193 |
| GPT-OSS embedding HTTP | http://localhost:8000/embed | text | embedding_engine gpt_oss | guardian/embedding_engine.py:L61-L74 |

## Docs <-> Code Consistency
- README claims "data never leaves" and provider-agnostic support including Anthropic/DeepSeek. Evidence: README.md:L22-L33 and README.md:L55-L56.
- Provider registry only wires OpenAI/Groq/Gemini when API keys exist, and ai_router calls OpenAI/Groq over HTTPS. Evidence: guardian/providers/registry.py:L17-L43; guardian/core/ai_router.py:L12-L65 and guardian/core/ai_router.py:L194-L231.

## Code Quality, Testing, and DX
- Frontend scripts for dev/test/lint are defined in frontend/src/package.json. Evidence: frontend/src/package.json:L5-L12.
- Playwright configuration exists for frontend E2E. Evidence: frontend/src/playwright.config.ts:L22-L47.
- Pytest ignores guardian/tests by default, reducing backend test coverage. Evidence: pytest.ini:L1-L3.

## Performance and Scalability
- Implemented: document chunking with overlap for embeddings. Evidence: guardian/services/document_chunking.py:L14-L44.
- Implemented: document embedding worker is queue-driven. Evidence: guardian/workers/document_embed_worker.py:L186-L193.
- Implemented: chat worker consumes a queue for completions. Evidence: guardian/workers/chat_worker.py:L416-L429.
- Implemented: CodexifyEmbedder includes batching helper for embeddings. Evidence: guardian/runtime/embed/embedder.py:L42-L50.
- Theoretical: embedding_engine includes dummy/gpt_oss placeholders that rely on external services or are not implemented. Evidence: guardian/embedding_engine.py:L30-L79.

## Risk Register
| ID | Severity | Risk | Evidence | Impact | Mitigation |
| --- | --- | --- | --- | --- | --- |
| FINDING-2026-01-25-001 | RISK | Secrets committed in .env | .env:L24-L66 | Credential leakage, unauthorized access | Remove secrets from repo; use env injection and placeholders |
| FINDING-2026-01-25-002 | RISK | API key fallback accepts predictable values | guardian/core/dependencies.py:L77-L174 | Unauthorized access in misconfigured envs | Fail closed without explicit keys |
| FINDING-2026-01-25-003 | WARN | Migration UI uses legacy route without auth | frontend/src/components/settings/SettingsView.tsx:L146-L161; guardian/routes/migration.py:L28-L34 | Migration fails in production or bypasses canonical auth path | Use /api endpoint and attach API key |
| FINDING-2026-01-25-004 | WARN | Document uploads missing API key headers | frontend/src/hooks/useUploader.ts:L109-L120; guardian/routes/media.py:L63-L72 | Uploads fail or are unauthenticated | Add API key headers in production client |
| FINDING-2026-01-25-005 | WARN | Image gallery/generation missing API key headers | frontend/src/components/gallery/GalleryView.tsx:L50-L57; frontend/src/components/modals/ImageGenModal.tsx:L62-L69; guardian/routes/media.py:L63-L72 | Gallery/image-gen breaks in production | Add API key headers to /api/media calls |
| FINDING-2026-01-25-006 | WARN | Upload failure counter uses uninitialized variable | frontend/src/hooks/useUploader.ts:L88-L166 | Runtime error on failed uploads | Initialize totalFailed before use |
| FINDING-2026-01-25-007 | RISK | Optional ingestion endpoint can exfiltrate data | frontend/src/hooks/useUploader.ts:L179-L193 | Unbounded data egress | Remove runtime override or require consent |
| FINDING-2026-01-25-008 | WARN | Embedding defaults to OpenAI, may egress or fail | guardian/workers/document_embed_worker.py:L145-L158; guardian/runtime/embed/embedder.py:L53-L103 | Unintended external calls or embed failures | Make embedder backend explicit and local by default |
| FINDING-2026-01-25-009 | WARN | Documents list is localStorage-backed | frontend/src/components/persona/layout/AppShell.tsx:L433-L459 | Persisted docs not visible across sessions | Fetch backend list and reconcile |
| FINDING-2026-01-25-010 | WARN | Image providers (local/stability) are placeholders | guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27 | Image-gen loop incomplete | Implement or hide stub providers |
| FINDING-2026-01-25-011 | WARN | RAG trace not available to UI | guardian/routes/chat.py:L586-L665; frontend/src/features/chat/GuardianChat.tsx:L105-L128 | No observable RAG transparency in UI | Provide trace API/event and wire UI |
| FINDING-2026-01-25-012 | WARN | Backend tests skipped by pytest config | pytest.ini:L1-L3 | Reduced backend regression coverage | Include guardian/tests in default runs |
| FINDING-2026-01-25-013 | WARN | README overstates provider support and local-first | README.md:L22-L56; guardian/providers/registry.py:L17-L43 | Misaligned expectations, sovereignty claims | Update docs to match code |
| FINDING-2026-01-25-014 | WARN | User identity hardcoded to "default" | guardian/core/dependencies.py:L194-L199 | No user isolation for auth | Map API keys to users |
| FINDING-2026-01-25-015 | WARN | Document generation endpoints lack API key auth | guardian/routes/documents.py:L9-L20; guardian/routes/documents.py:L249-L254 | Public access to doc generation | Require API key dependencies |
