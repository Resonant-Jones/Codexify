# Codexify Configuration and Settings Catalog

## Purpose

This is an evidence-backed directory of first-party values that can change Codexify behavior. It distinguishes settings a person may control from installation policy, development controls, compatibility inputs, and derived state. It supplies plain-language descriptions for a possible future All Settings directory.

## Status and interpretation rules

- Status: architecture-impact inventory at repository HEAD. Evidence classes are documented-contract and proven-code-path. No live process, effective environment, provider inventory, or release qualification was inspected.
- This Markdown is **not configuration authority** and must never be loaded as configuration. An entry does not create an API, editing permission, UI promise, installed capability, provider availability, or release claim.
- Current support and readiness are governed by docs/architecture/00-current-state.md. Accepted ADRs and actual consumer paths govern narrower semantics. The existing authority census is an inspection baseline, not a unified resolver.
- A declared field and an effective consumer are recorded separately. Unknown precedence, mutation ownership, effect timing, or reachability is marked unresolved. Similar names are grouped only where a common owner or alias transformation is evidenced.
- Identifiers of secrets are listed so operators can find their owning boundary. Values, tokens, private keys, session material, and copied environment contents are deliberately absent.
- The source path docs/CONFIGURATION.md named in the task is absent at this tip. docs/Codexify/CONFIGURATION.md exists and was inspected as a supporting reference; its older provider and route examples do not override current code, ADRs, or release truth.

## Audience and disposition model

Audience is one of application-user, installation-operator, developer-tester, no-human-control, or unresolved. The first audience is a person using the WebUI; the second operates an installation; the third configures development or test paths. Scope is recorded separately because an installation operator can also be a user.

Configuration class is deployment-config, runtime-setting, client-preference, derived-or-cache-state, or unresolved. Current status is active, compatibility, legacy, declared-no-consumer-found, internal, experimental, test-only, or unresolved. A status describes inspected source reachability, never beta support.

UI disposition is primary-settings, all-settings-directory, operator-surface, developer-tester-only, link-to-owning-control, read-only-information, do-not-surface, or unresolved. Primary Settings requires legitimate user mutation authority and an existing stable owner. All Settings may describe a value without editing it. Operator and developer settings require their own authority and must not be made mutable by the directory.

## Inventory method and record format

The inspection covers core and legacy settings models, direct environment resolvers, dotenv/bootstrap and supported-profile sources, specialized subsystem owners, client and desktop persistence, database-backed user/thread/profile settings, Connections, route gates, and selected first-party execution/worker controls. Generated files, vendored dependencies, lockfiles, and ordinary constants are outside the candidate set. Script-only proof inputs and one-shot data operations are recorded in exclusions.

Each numbered record supplies: exact identifiers and a behavioral description; class/audience/scope; declared source, effective owner and consumer; persistence, precedence and competing authority; mutation authority, access method and effect timing; constraints, secret status and effective-value inspection; current status, UI disposition, owning control; and evidence/census references. A semicolon-separated list in one record is a coherent family, not a claim that its members share a storage location or value. Where multiple stores exist, the record names them individually.

## Catalog: application, account, thread, and profile

### U01 — Theme and temporary theme override
- **Identifiers / purpose:** cfy.themeMode; cfy.sessionTheme; cfy.sessionThemeUntil. Choose the app color theme; a temporary override expires at the next local midnight.
- **Class / audience / scope / persistence:** client-preference; application-user; browser session/device; localStorage.
- **Declaration → owner → consumer:** frontend/src/components/persona/layout/AppShell.tsx theme initialization and theme effects → AppShell → rendered shell theme.
- **Precedence / conflict:** the temporary theme takes precedence until its expiry; browser-local state does not govern another device. No backend authority is evidenced.
- **Mutation / access / timing:** user via Settings Appearance theme control or temporary theme action; next render, with localStorage persistence across reload. Values are constrained by the theme control; non-secret. Effective theme is visible in the UI.
- **Status / UI / evidence:** active; primary-settings; Settings → Appearance. Evidence: AppShell.tsx:858-900,1116-1120,1305-1309 and frontend/src/features/settings/SettingsView.tsx:1136-1140. Census: none.

### U02 — Wallpaper, palette, and material appearance
- **Identifiers / purpose:** cfy.wallpaper; cfy.hasUserUpload; cfy.baseColor; cfy.extColors; cfy.depth; cfy.fade; cfy.surfaceDepth; cfy.surfaceWarmth. Change the personal background, file-type colors, and shared surface material.
- **Class / audience / scope / persistence:** client-preference, except cfy.hasUserUpload is derived-or-cache-state; application-user for the editable values and no-human-control for the marker; browser/device; localStorage.
- **Declaration → owner → consumer:** SettingsView.tsx controls and AppShell.tsx state/effects → frontend appearance state → rendered shell, gallery, and document colors.
- **Precedence / conflict:** user wallpaper replaces the base-color background; the upload marker records provenance and is not an independent preference. Browser-local values can diverge between devices; no backend sync is evidenced.
- **Mutation / access / timing:** user via Settings Appearance inputs; immediate next render and reload persistence. Color inputs and bounded sliders validate UI values; non-secret. The rendered appearance and control values are the effective inspection surface.
- **Status / UI / evidence:** active; primary-settings for editable values, do-not-surface for the upload marker; Settings → Appearance. Evidence: SettingsView.tsx:779-798,1117-1390 and AppShell.tsx:1488,1903-1958,2336-2343,2349-2408. Census: none. ADR-064 governs material semantics.

### U03 — Dashboard and workspace layout
- **Identifiers / purpose:** cfy.layoutMode; cfy.dashboard.threadRows; cfy.workspace.ui; cfy.workspace.layout; cfy.documentsSidebarOpen. Control how much workspace and thread content is shown and how panels are arranged.
- **Class / audience / scope / persistence:** client-preference; application-user; browser/device, with workspace layout optionally keyed by thread; localStorage.
- **Declaration → owner → consumer:** AppShell.tsx and frontend/src/features/workspace/state/useWorkspaceUiState.ts / useWorkspaceLayoutMode.ts → frontend view state → rendered dashboard and workspace.
- **Precedence / conflict:** thread-specific workspace layout key can differ from the general workspace key; current browser wins for that browser. No server-side layout authority is evidenced.
- **Mutation / access / timing:** user via dashboard/workspace controls; next render and reload. UI validates allowed layout modes and row bounds; non-secret. Inspect the current view/control state.
- **Status / UI / evidence:** active; all-settings-directory with link-to-owning-control in the Dashboard or Workspace, rather than a second editor. Evidence: AppShell.tsx:1132-1260,1919-1948,2662-2669 and useWorkspaceLayoutMode.ts:164-222. Census: none.

### U04 — Guardian report-offer preference
- **Identifiers / purpose:** cfy.guardian.feedback.optIn. Choose whether Guardian may offer report feedback; off is the client default.
- **Class / audience / scope / persistence:** client-preference; application-user; browser/device; localStorage.
- **Declaration → owner → consumer:** frontend/src/features/settings/feedbackPreference.ts → FeedbackSettingsPanel.tsx → Guardian report-offer presentation.
- **Precedence / conflict:** no backend/account setting is evidenced; per-browser choice can diverge. Mutation is through the existing Feedback switch, effective on next render.
- **Constraints / secret / inspection:** boolean; non-secret; inspect the Settings Feedback switch.
- **Status / UI / evidence:** active; primary-settings; Settings → Feedback. Evidence: feedbackPreference.ts:1-27 and FeedbackSettingsPanel.tsx:94-129. Census: none.

### U05 — User-global identity and memory policy
- **Identifiers / purpose:** memory_mode; diary_requires_unlock; allow_sensitive_modeling. Choose how identity memory is used, whether diary access needs unlocking, and whether sensitive modeling is allowed.
- **Class / audience / scope / persistence:** runtime-setting; application-user; account/user; Postgres user_settings.
- **Declaration → owner → consumer:** guardian/db/models.py:4000-4031 and guardian/services/iddb_settings_service.py → Guardian IDDB settings owner → guardian/routes/imprint.py:185-195 and identity-policy paths. frontend/src/imprint/settingsApi.ts projects GET/POST /api/iddb/settings.
- **Precedence / conflict:** a missing user row can read the legacy default row, but writes to default are forbidden; owner-scoped row wins. The in-memory guardian/cognition/user_settings/store.py is a separate legacy-looking surface with no proven canonical consumer in this path.
- **Mutation / access / timing:** authenticated user through the IDDB settings API/IdentityMemorySettings control; next read/request. memory_mode accepts none, light, deep; booleans are normalized; non-secret policy values, but privacy-sensitive. GET /api/iddb/settings is the effective-value read.
- **Status / UI / evidence:** active; primary-settings when the owning Identity Memory control is mounted, otherwise link-to-owning-control. Evidence: iddb_settings_service.py:18-176, guardian/routes/iddb.py:35-54, frontend/src/settings/IdentityMemorySettings.tsx:55-110. Census: none.

### U06 — Imprint local preview context
- **Identifiers / purpose:** cfy.assistantName; cfy.userName; cfy.role; cfy.notes; cfy.systemPrompt. Supply local preview names and notes for the existing Imprint Settings view.
- **Class / audience / scope / persistence:** client-preference; application-user; browser/device; localStorage.
- **Declaration → owner → consumer:** AppShell.tsx state → SettingsView.tsx preview form. The form explicitly calls these local preview values; backend proposal/acceptance is a separate Guardian-owned path.
- **Precedence / conflict:** browser preview does not override canonical Persona Profile, accepted Imprint state, or the composed system prompt. cfy.systemPrompt is persisted by AppShell but SettingsView's canonical inspector does not establish it as prompt authority.
- **Mutation / access / timing:** user via Settings → Imprint local preview; next render, reload persistence. Free text; non-secret as a configuration field, although entered content may be personal. Inspect the local preview form, not runtime prompt execution.
- **Status / UI / evidence:** compatibility; read-only-information for the directory, with link-to-owning-control for preview editing. Evidence: AppShell.tsx:1316-1327, SettingsView.tsx:1038-1114, ADR-058. Census: none. Canonical prompt effect is unresolved for the browser-only systemPrompt value.

### U07 — System-document participation
- **Identifiers / purpose:** per-document enabled/toggle state through system_docs routes. Decide whether an owned system document participates in configured prompt context.
- **Class / audience / scope / persistence:** runtime-setting; application-user; document/account; Guardian-owned document state, not browser localStorage.
- **Declaration → owner → consumer:** guardian/routes/imprint.py system_docs_router and mounted route posture → Guardian system-document owner → prompt assembly; Settings prompt inspector is observational.
- **Precedence / conflict:** route exposure under ADR-072 does not grant a parallel Settings authority or prove every document is used in an executed turn.
- **Mutation / access / timing:** authenticated owner via existing system-document toggle API/control; next prompt assembly where the document is selected. Bounded route/profile policy applies; non-secret, document contents remain sensitive. Inspect system-document read endpoint and prompt inspector for bounded projection.
- **Status / UI / evidence:** active; link-to-owning-control. Evidence: docs/architecture/adr/072-bounded-settings-and-connections-route-promotion.md:20-58 and guardian/routes/imprint.py:627-687. Census: none.

### U08 — Browser provider/model preference
- **Identifiers / purpose:** guardian.provider.v1; guardian.provider_model.v1. Remember a preferred provider and model for the local browser UI.
- **Class / audience / scope / persistence:** client-preference; application-user; browser/device; localStorage.
- **Declaration → owner → consumer:** frontend/src/lib/providerPref.ts → provider/model UI reconciliation → selected composer preference. Guardian catalog, supported profile, request validation, and runtime inventory still govern availability and execution.
- **Precedence / conflict:** stale selections are cleared or normalized against the current provider catalog; this preference does not override installation provider policy or explicit thread config.
- **Mutation / access / timing:** user through model selector; next selection/request if still allowed. String identifiers validated against available catalog items; non-secret. Inspect the model selector and provider catalog, not localStorage alone.
- **Status / UI / evidence:** active; all-settings-directory linking to the composer selector. Evidence: providerPref.ts:1-163 and frontend/src/features/chat/GuardianChat.tsx. Census: C1/C3 by dependency, not by authority.

### U09 — Durable thread inference and retrieval selection
- **Identifiers / purpose:** chat_threads.thread_config with providerId, modelId, inferenceMode, retrievalSource, personaId; accepted snake_case aliases in request input. Set the model, reasoning posture, retrieval source, and Persona for one thread.
- **Class / audience / scope / persistence:** runtime-setting; application-user; thread; Postgres JSONB thread_config.
- **Declaration → owner → consumer:** guardian/routes/chat.py snapshot/patch validation → chat thread record → chat completion/profile resolution and frontend GuardianChat projection.
- **Precedence / conflict:** thread snapshot defaults from configured provider/model when absent; explicit thread values are subject to supported-profile/provider validation. Persona revision selection and browser provider preference are separate inputs. The exact end-to-end precedence between these inputs is not flattened here.
- **Mutation / access / timing:** authenticated thread owner via thread create/PATCH config and composer controls; new request after save. Values normalized and policy checked; non-secret. Read thread config from the owned thread API and compare provider health for availability.
- **Status / UI / evidence:** active; all-settings-directory with link-to-owning-control in the thread/composer. Evidence: guardian/routes/chat.py:1616-1798,3489-3512; guardian/db/models.py:1250; frontend/src/features/chat/GuardianChat.tsx:602-714. Census: C1/C3, A7 only for the separate legacy revisionless profile branch.

### U10 — Canonical Persona identity, prompt, and model
- **Identifiers / purpose:** PersonaProfileManifest.profileIdentity, identity.name/description, prompt.systemPrompt/styleNotes/directives, model.provider/model/temperature/topK/topP/maxTokens, revision. Author a reusable Persona and choose its requested model behavior.
- **Class / audience / scope / persistence:** runtime-setting; application-user; account-owned profile/persona, with server-assigned immutable revision; Postgres Persona Profile records.
- **Declaration → owner → consumer:** guardian/cognition/system_profiles/manifest.py and store.py → canonical Persona Profile owner → resolver reads the five-field seam of identity, prompt, provider, model, temperature for chat; the remaining authored fields persist but their execution effect is not established by this resolver.
- **Precedence / conflict:** account ownership and revision are server-owned; browser-local Persona Studio state is a draft only. A selected immutable revision and thread binding must be distinguished from live provider availability. Legacy revisionless fallback is cataloged separately under L07.
- **Mutation / access / timing:** account owner through Persona Studio/Persona Profile API; new immutable revision and subsequent bound thread/task resolution. Typed manifest validates lengths and sampling bounds; non-secret authored content may be sensitive. Inspect saved manifest and effective-resolution preview, not draft state alone.
- **Status / UI / evidence:** active for the five-field seam; all-settings-directory linking to Persona Studio. Extended authored fields have unresolved runtime effect. Evidence: manifest.py:24-150, guardian/cognition/system_profiles/resolver.py:200-224, guardian/routes/persona_profiles.py; ADR-082. Census: A7 is explicitly separate.

### U11 — Extended Persona voice, capabilities, and retrieval intent
- **Identifiers / purpose:** PersonaProfileManifest.voice.enabled/provider/voicePreset/speed/wakeWord/interruptible; capabilities.pinnedTools/allowedTools/skills/permissions.web/email/calendar/cli/filesystem; retrieval.enabled/mode/topK/rerank. Describe requested voice, tools, permissions, and retrieval posture for a Persona.
- **Class / audience / scope / persistence:** runtime-setting candidate; application-user; account-owned profile revision; Postgres Persona manifest.
- **Declaration → owner → consumer:** manifest.py typed write/persistence → Persona Profile owner. The inspected five-field chat resolver consumes model/prompt fields, not these extended fields as execution authority.
- **Precedence / conflict:** authored capability requests do not grant runtime authorization, connection credentials, or installed tools. Voice and retrieval execution remain with their own subsystems and policy gates.
- **Mutation / access / timing:** account owner via Persona Studio API; persisted at revision creation, runtime effect unresolved. Manifest validation is typed; non-secret configuration that may contain personal text. Saved manifest/effective preview can be inspected, while execution effect cannot be inferred.
- **Status / UI / evidence:** declared-no-consumer-found for the inspected chat-resolution seam; read-only-information in a future directory, link-to-owning-control for authored edits. Evidence: manifest.py:51-137, resolver.py:200-224, ADR-082. Census: none.

### U12 — Persona binding and selected revision
- **Identifiers / purpose:** account/profile binding, pinned profile ID/revision, and thread/task selection references. Choose which authored Persona revision applies to a particular work context.
- **Class / audience / scope / persistence:** runtime-setting; application-user; account, thread, or task binding as defined by Persona Profile service; server-owned DB state.
- **Declaration → owner → consumer:** guardian/routes/persona_profiles.py, guardian/cognition/system_profiles/store.py and guardian/cognition/system_profiles/resolver.py → server-owned bindings → chat completion resolution.
- **Precedence / conflict:** immutable authored manifest and mutable binding are distinct; local Persona Studio drafts do not own binding. Legacy profile defaults remain a separate fallback.
- **Mutation / access / timing:** authenticated account owner through Persona selection/binding API; next resolved task/thread. Owner and revision checks apply; non-secret. Effective-resolution preview and thread readback are inspection surfaces.
- **Status / UI / evidence:** active where binding API is used; link-to-owning-control in Persona Studio/thread selection. Evidence: guardian/cognition/system_profiles/resolver.py, guardian/routes/persona_profiles.py, ADR-082. Census: A7 kept separate.

### U13 — TTS voice profiles
- **Identifiers / purpose:** tts_voice_profiles.id/name/backend_id/is_default/description/voice_mode/speaker/voice_prompt/style_instructions/language/speed/temperature/top_k/top_p/repetition_penalty/max_new_tokens/do_sample/backend_params/reference_audio_asset_id/reference_text/x_vector_only_mode/sample_rate/output_format/loudness_normalization/pause_profile. Configure a reusable local speech voice and its synthesis options.
- **Class / audience / scope / persistence:** runtime-setting; application-user or installation-operator depending on the mounted TTS console; profile record in Postgres.
- **Declaration → owner → consumer:** guardian/db/models.py TTSVoiceProfile and voice-profile routes → Guardian TTS profile owner → TTS adapter/renderer; frontend TtsConsole edits the profile.
- **Precedence / conflict:** profile selection is distinct from installation TTS backend/provider configuration and from Persona voice intent. A saved profile does not prove a backend is available.
- **Mutation / access / timing:** authorized profile editor via TTS Console API; next render/synthesis after save. Database checks bound speed/temperature/sampling and output format; reference assets/content can be sensitive, while identifiers are non-secret. Inspect the profile API and TTS health separately.
- **Status / UI / evidence:** internal/bounded; link-to-owning-control in TTS Console when available. Evidence: guardian/db/models.py:3828-3915 and frontend/src/features/ttsConsole/TtsProfileEditor.tsx. Census: A5/A6 are separate installation owners.

### U14 — Connection setup and user-scoped authorization
- **Identifiers / purpose:** connector-specific setup fields, channel configuration, oauth_connections records, and server-side per-user credentials. Connect an owned external account or channel to supported adapters.
- **Class / audience / scope / persistence:** runtime-setting; application-user; user and connector/channel; server-side DB/credential storage.
- **Declaration → owner → consumer:** guardian/routes/connectors.py and channel/OAuth routes own mutation/execution; guardian/connections/catalog.py projects setup metadata through GET /api/connections.
- **Precedence / conflict:** catalog presence, setup configuration, authorization, runtime health, and execution are five distinct states. No credential content belongs in the read-only catalog or this document; a frontend setup card cannot create an adapter.
- **Mutation / access / timing:** authenticated owner through an existing adapter-specific setup path only; next request/sync where implemented. Validation and provider consent depend on the adapter; secret status mixed. Inspect sanitized catalog setup state plus owning adapter health, never raw credentials.
- **Status / UI / evidence:** active only for proven backing handlers; link-to-owning-control in Settings → Connectors. Unimplemented catalog entries are read-only-information. Evidence: guardian/connections/catalog.py, guardian/routes/connections.py, guardian/routes/connectors.py:210-246; ADR-071/072. Census: S7 for application OAuth setup, not all user grants.

### U15 — Desktop connection bootstrap and API key
- **Identifiers / purpose:** cfy.desktop.backendBaseUrl; cfy.desktop.sharePublicBaseUrl; desktop runtime API key stored through the native bridge. Choose the desktop app's backend/share origin and authenticate its local connection.
- **Class / audience / scope / persistence:** deployment-config for URLs and secret connection input; installation-operator; desktop installation; browser localStorage URL overrides plus native keychain for the API key.
- **Declaration → owner → consumer:** frontend/src/lib/runtimeConfig.ts and frontend/src/features/settings/SettingsView.tsx → desktop bootstrap/native bridge → API/SSE/share URL resolution and API authentication.
- **Precedence / conflict:** launcher handoff, desktop overrides, Tauri config, and Vite env each participate in ordered resolution; URL overrides can shadow bootstrap values. Browser web mode does not expose desktop Connection tab.
- **Mutation / access / timing:** desktop installation owner via Settings → Connection; refresh/reinitialize runtime config on save. URLs are bounded by runtime normalization; API key is secret and never recorded here. Inspect resolved runtime connection snapshot and connection test; key presence only.
- **Status / UI / evidence:** active in desktop mode; operator-surface, link-to-owning-control in desktop Settings → Connection. Evidence: runtimeConfig.ts:64-69,331-417,547-580,696-719 and SettingsView.tsx:1733-1836. Census: none.

### U16 — Client provider/feature and navigation caches
- **Identifiers / purpose:** cfy.settingsTab; cfy.lastView; cfy.documents.sidebarTab; cfy.generalProjectId; cfy.defaultProjectId; cfy.generalProjectIdTrusted; codexify.chatgpt_import_task; cfy.documents; cfy.gallery; cfy.personaStudio.localState.v1. Preserve navigation, pending import presentation, cached document/gallery state, and unsaved Persona Studio draft state.
- **Class / audience / scope / persistence:** derived-or-cache-state; no-human-control; browser/session; localStorage or sessionStorage.
- **Declaration → owner → consumer:** frontend SettingsView/AppShell/Persona Studio → frontend restoration and presentation; server-owned documents, projects, import jobs, and Persona revisions remain separate.
- **Precedence / conflict:** canonical backend readback controls durable entities; browser cache may be stale or absent. Persona Studio local state must not serialize saved manifests/revisions.
- **Mutation / access / timing:** automatic frontend writes and dismissal/navigation; next render/reload. Data formats are internally validated; secret status unknown for cached user content, so do not expose raw values. Inspect the owning UI and backend entity readback.
- **Status / UI / evidence:** internal; do-not-surface as settings. Evidence: SettingsView.tsx:116-160,478-529; AppShell.tsx:1347-1453,1506-1750,2349-2377; personaStudioStore.ts:98,778-842. Census: none.

### U17 — Other client-local interaction preferences
- **Identifiers / purpose:** cfy.ingest.enabled; cfy.flowBuilder.mode; cfy.workspace.scratchpad. The first two remember a local ingestion presentation toggle and Flow Builder mode; scratchpad stores authored workspace content.
- **Class / audience / scope / persistence:** client-preference for the first two; derived-or-cache-state/content for scratchpad; application-user or no-human-control; browser/workspace; localStorage.
- **Declaration → owner → consumer:** AppShell.tsx and Flow Builder/Workspace state hooks → frontend presentation and local working state. Backend ingestion authority is not established by the local toggle.
- **Precedence / conflict:** local UI state cannot authorize server ingest or Flow execution. Scratchpad is content, not a behavior setting.
- **Mutation / access / timing:** user via owning UI for visible toggles/modes; next render. Values bounded by UI state; non-secret identifiers but scratchpad content may be private. Inspect the owning UI.
- **Status / UI / evidence:** active client state; all-settings-directory as read-only information for the two toggles, do-not-surface for scratchpad content. Evidence: AppShell.tsx:2385-2390,328; frontend/src/features/workspace/state/useWorkspaceScratchpadState.ts. Census: none.

## Catalog: installation, provider, and runtime operation

### O01 — Dotenv loading and core/legacy coherence
- **Identifiers / purpose:** GUARDIAN_ENV; CODEXIFY_DISABLE_DOTENV; CODEXIFY_CONFIG_SOURCE. Select dotenv layers and the strict/core/legacy coherence check between two backend settings models.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/installation; process environment and .env layers.
- **Declaration → owner → consumer:** guardian/core/dependencies.py dotenv loader and guardian/core/config.py Settings/assert_config_coherence → canonical ASGI startup. guardian/config/core.py remains an independently constructed legacy settings surface.
- **Precedence / conflict:** existing process environment wins; .env, .env.backend.{environment}, then .env.local load without override; core Settings may already be imported before the explicit loader. Coherence compares selected fields but does not unify authority.
- **Mutation / access / timing:** operator environment/file edit before process start; restart for import/startup effects. Accepted modes are strict/core/legacy; non-secret selector. Startup/coherence logs and effective health can reveal mismatch, not a full field-by-field effective-value view.
- **Status / UI / evidence:** active plus compatibility; operator-surface for deployment guidance, do-not-surface as ordinary Settings. Evidence: guardian/core/dependencies.py, guardian/core/config.py:84-125, guardian/config/core.py:38-203, docs/architecture/config-and-ops.md:637-654. Census: C1/C2/K2/A1.

### O02 — Supported profile and route/provider policy manifest
- **Identifiers / purpose:** CODEXIFY_SUPPORTED_PROFILE; CODEXIFY_SUPPORTED_PROFILE_DIR; config/supported_profiles/*.yaml provider, auth, route and runtime posture. Choose a named deployment profile and its allowed capability boundary.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env plus versioned YAML manifest.
- **Declaration → owner → consumer:** guardian/core/supported_profile.py → Guardian startup/provider policy and route mounting; Compose transports the selected profile.
- **Precedence / conflict:** profile policy is an allowed/default posture, not a user model preference or physical Whoosh'd selection. An unlisted route is quarantined; operator env and runtime inventory have distinct roles under ADR-074.
- **Mutation / access / timing:** operator changes the selected profile or reviewed manifest; backend restart. Manifest schema/profile validation applies; non-secret metadata, though associated env may be secret. Inspect GET /health route inventory and provider posture, plus the selected manifest.
- **Status / UI / evidence:** active; operator-surface. Evidence: guardian/core/supported_profile.py, guardian/guardian_api.py, config/supported_profiles/v1-local-core-web-mcp.yaml; ADR-072/074. Census: C3.

### O03 — HTTP authentication, identity, and public exposure
- **Identifiers / purpose:** GUARDIAN_API_KEY; GUARDIAN_API_KEYS; GUARDIAN_ADMIN_TOKEN; GUARDIAN_AUTH_MODE; GUARDIAN_EXPOSURE_MODE; CODEXIFY_MULTI_USER_ENABLED; CODEXIFY_SINGLE_USER_ID; GUARDIAN_SESSION_SECRET; GUARDIAN_JWT_SECRET; GUARDIAN_ALLOWED_ORIGINS; GUARDIAN_PUBLIC_PROFILE; GUARDIAN_PUBLIC_ROUTES_FILE; CODEXIFY_PUBLIC_BASE_URL. Set the trust boundary for API callers, accounts, CORS, and public exposure.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env and optional public-routes file.
- **Declaration → owner → consumer:** core and legacy settings, direct guardian/guardian_api.py startup reads, guardian/core/auth.py, guardian/core/dependencies.py, and public-exposure helpers → route authentication and request identity.
- **Precedence / conflict:** A1 legacy settings and A2 raw startup/request reads resolve overlapping API keys at different times; supported-profile auth-route posture constrains GUARDIAN_AUTH_MODE. CORS/public profile does not grant authorization.
- **Mutation / access / timing:** installation operator via secret manager/env and reviewed public policy file; startup/restart for route/auth posture, some request-time raw key reads. API keys/session secrets are secret; origin/profile names are non-secret. Verify selected auth mode, mounted routes and an authorized request; never inspect key content through a UI.
- **Status / UI / evidence:** active with competing authority for API keys; operator-surface for posture, do-not-surface for secret values. Evidence: guardian/core/config.py:112,486-490, guardian/config/core.py:83-100, guardian/core/dependencies.py, guardian/core/auth.py, guardian/guardian_api.py; docs/Codexify/CONFIGURATION.md:9-26. Census: C1/C3/A1/A2.

### O04 — Database endpoint and migration/worker bootstrap
- **Identifiers / purpose:** DATABASE_URL; GUARDIAN_DATABASE_URL; GUARDIAN_DB_URL; GUARDIAN_DB_DSN; PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD; POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD; ALEMBIC_CONFIG; MIGRATOR_DB_TIMEOUT_SECONDS. Connect API, workers, and migrations to their intended Postgres instance.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env/Compose.
- **Declaration → owner → consumer:** guardian/core/dependencies.py init_database, guardian/core/db.py, guardian/config/db_defaults.py, migration and backend launcher code → DB adapters, workers, migration process.
- **Precedence / conflict:** A3 API/core raw resolution and A4 worker/migration import-time fallback use non-identical alias order/defaults; A1 parses GUARDIAN_DATABASE_URL independently. No single precedence contract covers all processes.
- **Mutation / access / timing:** operator supplies DSN/credentials and restarts affected services; import-time default and process startup matter. DSNs/passwords are secret or mixed. Inspect redacted connection target/health and migration results; do not render credentials.
- **Status / UI / evidence:** active / unresolved authority conflict; operator-surface, with connection status read-only. Evidence: guardian/core/dependencies.py, guardian/core/db.py, guardian/config/db_defaults.py, backend/compiled_runtime_entry.py; census A1/A3/A4.

### O05 — Redis transport, queue names, worker capacity, and timing
- **Identifiers / purpose:** REDIS_URL; REDIS_OPERATION_TIMEOUT_SECONDS; CHAT_QUEUE_NAME; CHAT_EMBED_QUEUE_NAME; CHAT_IMPORT_EMBED_QUEUE_NAME; DOCUMENT_EMBED_QUEUE_NAME; ACCOUNT_IMPORT_QUEUE_NAME; CRON_QUEUE_NAME; DELEGATION_QUEUE_NAME; VOICE_QUEUE_NAME; WARMUP_QUEUE_NAME; GITHUB_WATCHDOG_REVIEW_QUEUE_NAME; AGENT_TASK_QUEUE; AGENT_RESULT_STORE; CHAT_WORKER_CONCURRENCY; VOICE_WORKER_CONCURRENCY; CHAT_WORKER_AUDIO_AUTOGENERATE_CONCURRENCY; CHAT_WORKER_HEARTBEAT_KEY/TTL_SECONDS; VOICE_HEARTBEAT_KEY/INTERVAL_SECONDS/TTL_SECONDS; CHAT_TURN_LOCK_TTL_SECONDS; CODEXIFY_TURN_LOCK_TTL_SECONDS; CHAT_TURN_COMPLETION_ANCHOR_TTL_SECONDS; TASK_EVENT_BLOCK_MS; REDIS_OPERATION_TIMEOUT_SECONDS. Size and route asynchronous work and lifecycle leases.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; service/process; env/Compose and Redis runtime state.
- **Declaration → owner → consumer:** guardian/queue/redis_queue.py plus queue modules, guardian/workers/*, guardian/voice/runtime.py, guardian/guardian_api.py → enqueue, dequeue, heartbeat, lock and event consumers.
- **Precedence / conflict:** producer and worker must share queue names; some defaults are import-time. Redis transport acceptance does not prove dequeue or completion. Chat lock and turn-lock variables are separate resolvers until proven aliases.
- **Mutation / access / timing:** operator adjusts env/Compose before worker/backend restart; numeric bounds vary by owner. REDIS_URL may contain a secret, other names/budgets are non-secret. Inspect queue/worker health and bounded logs, not configuration presence alone.
- **Status / UI / evidence:** active; operator-surface, with health read-only. Evidence: guardian/queue/redis_queue.py:20-53, guardian/workers/chat_worker.py, guardian/workers/voice_worker.py, guardian/voice/runtime.py. Census: S4.

### O06 — Event outbox, WebSocket, UI session, and request limits
- **Identifiers / purpose:** OUTBOX_POLL_INTERVAL; OUTBOX_BATCH_SIZE; OUTBOX_TENANT_ID; ENABLE_OUTBOX; TASK_EVENT_BLOCK_MS; WS_RPC_RATE_LIMIT_CAPACITY/REFILL_PER_SECOND/NAMESPACE/IDLE_TIMEOUT_SECONDS/MAX_CONNECTIONS; GUARDIAN_WS_MAX_PAYLOAD_BYTES; UI_SESSION_MIN_TTL_SECONDS/MAX_TTL_SECONDS/TTL_SECONDS; EMBEDDER_PREFLIGHT_CACHE_TTL_SECONDS; HEALTH_LLM_CACHE_TTL_SECONDS; HEALTH_LLM_REQUEST_TIMEOUT_SECONDS; LLM_CATALOG_REQUEST_TIMEOUT_SECONDS; CANDIDATE_TRACE_TTL_SECONDS. Bound streaming, sessions, rate limits, diagnostics and preflight caches.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/service; env and ephemeral Redis/process state.
- **Declaration → owner → consumer:** guardian/guardian_api.py, guardian/core/config.py, guardian/ws, guardian/routes/ui_session.py, guardian/routes/health.py and outbox helpers → corresponding event/WS/session/health paths.
- **Precedence / conflict:** per-module direct reads and core typed WS settings have different evaluation timing; no universal live-reload contract is established. Cache/trace entries are derived state.
- **Mutation / access / timing:** operator env and service restart for stable change; owner-specific bounds apply. Secret status non-secret except tenant/session-associated content never recorded. Inspect health/metrics and endpoint responses; current effective numeric values are not uniformly exposed.
- **Status / UI / evidence:** active/internal; operator-surface for limits, do-not-surface for transport/cache identifiers. Evidence: guardian/core/config.py:793-810, guardian/guardian_api.py, guardian/ws/protocol.py, guardian/routes/ui_session.py. Census: C1 plus specialized direct owners.

### O07 — Provider posture, egress, and fallback policy
- **Identifiers / purpose:** LLM_PROVIDER; ALLOW_CLOUD_PROVIDERS; CODEXIFY_LOCAL_ONLY_MODE; CODEXIFY_EGRESS_ALLOWLIST; LLM_FALLBACK_ORDER; PROVIDER_MAX_RETRIES; PROVIDER_RETRY_BASE_SECONDS/MAX_SECONDS/JITTER_SECONDS. Determine permitted inference/egress and bounded retry policy.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env/typed core Settings and supported profile.
- **Declaration → owner → consumer:** guardian/core/config.py → guardian/core/egress.py, guardian/core/provider_registry.py and guardian/core/ai_router.py; supported profile further constrains allowed posture.
- **Precedence / conflict:** supported profile authorizes provider classes; operator env may select within that posture; egress is a separate fail-closed gateway. LLM_FALLBACK_ORDER is a configured list, not evidence that an unavailable explicit model may be substituted.
- **Mutation / access / timing:** operator env and backend/worker restart; provider allowlist/egress validation applies. Non-secret policy fields. Inspect GET /health and /api/llm/catalog alongside live provider health; no single config field proves availability.
- **Status / UI / evidence:** active; operator-surface, read-only-information in an All Settings directory at most. Evidence: guardian/core/config.py:84-124,210-216,637-653; guardian/core/egress.py; guardian/core/provider_registry.py. Census: C1/C3/C5.

### O08 — Local inference endpoint, exact model, and Whoosh'd management
- **Identifiers / purpose:** LOCAL_BASE_URL; LOCAL_DOCKER_FALLBACK_BASE_URL; CODEXIFY_LOCAL_DOCKER_FALLBACK_ENABLED; CODEXIFY_LOCAL_ENDPOINT_CHAIN; LOCAL_API_KEY; LOCAL_PROVIDER_DISPLAY_NAME; LOCAL_PROVIDER_VENDOR; LOCAL_RUNTIME_PRESET; LOCAL_COMPAT_FIRST; LOCAL_PREFER_OPENAI_COMPAT; LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK; LOCAL_CHAT_MODEL; LOCAL_LLM_MODEL; DEFAULT_LOCAL_MODEL; LLM_MODEL; LOCAL_VISION_MODEL; LOCAL_GGUF_MODEL; LOCAL_EMBEDDING_MODEL; WHOOSHD_MANAGED/HOST/PORT/COMMAND/WORKING_DIR/MODEL_REGISTRY_PATH/STARTUP_TIMEOUT_SECONDS/HEALTH_POLL_INTERVAL_SECONDS/STOP_ON_EXIT; CODEXIFY_WHOOSHD_THREADWAKE_SEGMENTS_ENABLED/MODE/SCOPE. Configure the local inference route, endpoint and optional managed runtime.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env, supported profile and Whoosh'd registry.
- **Declaration → owner → consumer:** guardian/core/config.py and local runtime presets → provider registry, ai_router, health and optional Whoosh'd manager. Whoosh'd's registry maps logical local-chat to physical model.
- **Precedence / conflict:** ADR-074 makes the supported profile posture authoritative, Whoosh'd registry authoritative for normal physical model, explicit LOCAL_CHAT_MODEL an operator exact override, Compose transport only, live inventory availability truth. Legacy model aliases normalize within core Settings; revisionless system-profile defaults are separate L07.
- **Mutation / access / timing:** operator configures Whoosh'd mapping or exact model/env and restarts affected processes; a model inventory mismatch fails closed. LOCAL_API_KEY is secret; paths/URLs are mixed; model/display fields non-secret. Inspect Guardian catalog/health and live Whoosh'd /v1/models plus served-model provenance.
- **Status / UI / evidence:** active with compatibility aliases; operator-surface, no general user editor. Evidence: guardian/core/config.py:125-139,220-377, guardian/core/provider_registry.py, guardian/core/supported_profile.py, ADR-074. Census: C1/C3/K1/A7 for separate legacy fallback.

### O09 — Cloud provider transport, credentials, models, and discovery
- **Identifiers / purpose:** OPENAI_API_KEY/BASE_URL/MODEL/DEFAULT_OPENAI_MODEL; GROQ_API_KEY/BASE_URL/MODEL/DEFAULT_GROQ_MODEL/MODEL_DISCOVERY_URL/MODEL_DISCOVERY_TIMEOUT_SECONDS; DEEPSEEK_API_KEY/BASE_URL/CHAT_MODEL/MODEL_DISCOVERY_URL/MODEL_DISCOVERY_TIMEOUT_SECONDS; ALIBABA_API_KEY/API_BASE/MODEL/TIMEOUT_SECONDS/MODEL_DISCOVERY_URL/MODEL_DISCOVERY_TIMEOUT_SECONDS; MINIMAX_API_KEY/API_BASE/API_FLAVOR/ANTHROPIC_VERSION/MODEL/TIMEOUT_SECONDS/MODEL_DISCOVERY_URL/MODEL_DISCOVERY_TIMEOUT_SECONDS. Select configured cloud endpoints and model identities when policy admits them.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env/core Settings and provider adapter configuration.
- **Declaration → owner → consumer:** guardian/core/config.py → guardian/core/provider_registry.py and ai_router/provider adapters; live discovery calls supply availability observations.
- **Precedence / conflict:** credentials authorize only their own provider lane; profile and egress policy still gate use. Legacy provider adapters Q2 and guardian/config/core.py have overlapping model/key declarations with potentially different defaults. Configuration does not prove health.
- **Mutation / access / timing:** operator via secret management/env and restart where core Settings is import-time; discovery timeout/endpoint validation applies. API keys secret, endpoint/model fields non-secret or mixed. Inspect redacted catalog and health, then live provider inventory where available.
- **Status / UI / evidence:** active for canonical routed paths, compatibility/uncertain for legacy adapters; operator-surface for endpoints/models, do-not-surface for credentials. Evidence: guardian/core/config.py:136-175,379-485; guardian/core/provider_registry.py:630-760,1374-1468; guardian/config/core.py:105-139. Census: C1/C3/Q2.

### O10 — Provider execution budgets and local reasoning directives
- **Identifiers / purpose:** LLM_REQUEST_TIMEOUT_SECONDS; LOCAL_REQUEST_CONNECT_TIMEOUT_SECONDS; LOCAL_EXTENDED_THINKING_TIMEOUT_SECONDS/MODEL_PATTERNS; LOCAL_DEFAULT_NO_THINK_ENABLED; LOCAL_NO_THINK_MODEL_PATTERNS/SKIP_MODEL_PATTERNS/INSTRUCTION; EMBEDDING_REQUEST_TIMEOUT_SECONDS; GROQ_TIMEOUT; OPENAI_TIMEOUT; MINIMAX_ANTHROPIC_MAX_TOKENS. Bound calls and select locally configured thinking behavior.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env/core Settings or specialized provider adapter.
- **Declaration → owner → consumer:** guardian/core/config.py and provider adapters → ai_router/local reasoning and provider transports.
- **Precedence / conflict:** thread inferenceMode is a separate per-thread selection; installed model capabilities and provider limits remain authoritative. Adapter-local timeout aliases may not share the core request budget.
- **Mutation / access / timing:** operator env, generally next process start; numeric/pattern validation is owner-specific. Non-secret. Inspect config/diagnostic logs and actual request results; no universal effective-value endpoint.
- **Status / UI / evidence:** active/internal; operator-surface. Evidence: guardian/core/config.py:637-708, guardian/core/ai_router.py, guardian/providers/openai_adapter.py, guardian/providers/groq_adapter.py. Census: C1/Q2 for legacy adapters.

### O11 — Embedding, vector store, and retrieval backend
- **Identifiers / purpose:** EMBEDDER_PROVIDER; EMBEDDING_MODEL; LOCAL_EMBEDDING_MODEL; CODEXIFY_VECTOR_STORE; CODEXIFY_CHROMA_PATH; CODEXIFY_COLLECTION; EMBEDDING_BACKEND; EMBED_BACKEND; LOCAL_EMBED_MODEL; CODEXIFY_EMBEDDINGS_BACKEND; VECTOR_STORE; CHROMA_PERSIST_DIRECTORY; STORAGE_BASE_PATH; EMBEDDING_DIM; CODEXIFY_MAX_EMBED_CHARS; CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK. Select embedding provider/model, derived index backend, and vector persistence.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env, filesystem/derived vector store.
- **Declaration → owner → consumer:** guardian/core/config.py resolve_vector_store_runtime → guardian/vector/store.py → chat retrieval/document embedding; backend/rag and CLI/MemoryOS embedding modules are distinct optional paths.
- **Precedence / conflict:** active VectorStore uses raw vector variables before typed core settings; Q1 embedder fallback and S10 CLI embed path have their own resolution, and optional backend/MemoryOS paths are not proven to own canonical chat retrieval. Postgres remains canonical data; vector store is derived.
- **Mutation / access / timing:** operator env and backend/worker restart, with index compatibility/rebuild consequences. Paths/models non-secret; cloud embedding credential is secret under O09. Inspect vector health, path/backend diagnostics and retrieval provenance; config alone is insufficient.
- **Status / UI / evidence:** active canonical vector path plus uncertain optional paths; operator-surface. Evidence: guardian/core/config.py:177-210 and resolve_vector_store_runtime, guardian/vector/store.py, guardian/runtime/embed/embedder.py, backend/rag/embedder.py. Census: C4/S10/Q1/Q2.

### O12 — Storage, media, and signing
- **Identifiers / purpose:** DATA_STORAGE_PATH; STORAGE_BASE_PATH; STORAGE_URL_PREFIX; IMPORT_STAGING_BASE_PATH; GUARDIAN_MEDIA_ROOT; GUARDIAN_MEDIA_URL_SECRET; GUARDIAN_SESSION_SECRET and GUARDIAN_API_KEY as signing fallbacks; storage-provider-specific S3/GCS keys; MEDIA_TITLE_MODE. Place and sign media and import staging artifacts.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env, local filesystem or external storage.
- **Declaration → owner → consumer:** guardian/core/storage.py storage factory and guardian/core/media_signing.py → media upload/read and signed URL verification; import staging service uses storage path.
- **Precedence / conflict:** signing secret resolves media-specific secret, then session secret, then API key; the fallback shares secret material without making HTTP auth the media owner. Storage provider selection remains specialized.
- **Mutation / access / timing:** operator secret/env/path configuration and service restart; filesystem and provider validation apply. Storage credentials/signing secrets are secret; paths are mixed. Inspect media route health and redacted storage diagnostics, not secret values.
- **Status / UI / evidence:** active; operator-surface for storage choice, do-not-surface for secret values and signed URL internals. Evidence: guardian/core/storage.py, guardian/core/media_signing.py, guardian/services/openai_account_import.py. Census: S6/S8.

### O13 — Graph context, graph writes, and Neo4j transport
- **Identifiers / purpose:** GUARDIAN_ENABLE_GRAPH_LOGGING; GUARDIAN_GRAPH_LOGGING_MODE; GUARDIAN_ENABLE_GRAPH_CONTEXT; CODEXIFY_ENABLE_GRAPH_WRITES; CODEXIFY_GRAPH_BACKEND; NEO4J_URI; NEO4J_USER; NEO4J_PASSWORD; NEO4J_DATABASE; NEO4J_BOLT_URL; NEO4J_USERNAME; NEO4J_PASS; BOLT_URL. Enable graph-derived context, diagnostic logging, and separately gated graph-write persistence.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/worker; env and graph service.
- **Declaration → owner → consumer:** guardian/core/config.py typed declarations; guardian/memory_graph/graph_backend_factory.py direct graph-write resolver → graph_write_worker; context broker and graph connection modules own other uses.
- **Precedence / conflict:** CODEXIFY_ENABLE_GRAPH_WRITES=false forces noop regardless of backend or Neo4j presence. The legacy compatibility graph factory U4 and graph connection aliases do not prove a second active write selector.
- **Mutation / access / timing:** operator env/service config and worker/backend restart; allowed backends noop/neo4j and fail-closed checks apply. Neo4j password secret, other identifiers mixed/non-secret. Inspect graph worker/health and provenance; configured Neo4j alone does not prove writes.
- **Status / UI / evidence:** active plus compatibility aliases; operator-surface for posture, do-not-surface for credentials. Evidence: guardian/core/config.py:713-756, guardian/memory_graph/graph_backend_factory.py, guardian/workers/graph_write_worker.py. Census: C6/U4.

### O14 — Federation trust policy and peer gating
- **Identifiers / purpose:** GUARDIAN_FEDERATION_ENABLED; GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY; GUARDIAN_FEDERATION_TRUST_POLICY_JSON; GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE; GUARDIAN_FEDERATION_POLICY_SIGNING_KEY; CODEXIFY_ENABLE_FEDERATION_ROUTES. Define whether federation routes exist and how peer trust is verified.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/network; env and signed policy data.
- **Declaration → owner → consumer:** guardian/core/config.py, guardian/core/auth.py and guardian/routes/federation.py → federation route and policy checks.
- **Precedence / conflict:** route mount, signed trust policy, identity, and egress allowance are separate gates; a peer name or policy file is not authorization by itself.
- **Mutation / access / timing:** operator-reviewed policy/key and backend restart; signatures and allowed peers must validate. Signing key and raw policy/signature material are secret or mixed. Inspect redacted federation readiness and authenticated peer behavior, not key content.
- **Status / UI / evidence:** internal/experimental relative to current release; operator-surface for policy, do-not-surface for key material. Evidence: guardian/core/config.py:773-790, guardian/routes/federation.py, docs/Codexify/CONFIGURATION.md:58-70. Census: C1/C5.

### O15 — Route mounting and optional capability gates
- **Identifiers / purpose:** CODEXIFY_BETA_CORE_ONLY; CODEXIFY_ENABLE_ACCOUNT_OBSERVABILITY_ROUTES; CODEXIFY_ENABLE_ADMIN_ROUTES; CODEXIFY_ENABLE_AGENT_ORCHESTRATION_ROUTES; CODEXIFY_ENABLE_AGENT_ROUTES; CODEXIFY_ENABLE_AUTH_ROUTES; CODEXIFY_ENABLE_BACKFILL_ROUTES; CODEXIFY_ENABLE_CHAT_ROUTES; CODEXIFY_ENABLE_CODEXIFY_ROUTES; CODEXIFY_ENABLE_CODEX_ROUTES; CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES; CODEXIFY_ENABLE_COLLABORATION_ROUTES; CODEXIFY_ENABLE_COMMAND_BUS_ROUTES; CODEXIFY_ENABLE_CONNECTIONS_ROUTES; CODEXIFY_ENABLE_CONNECTOR_ROUTES; CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES; CODEXIFY_ENABLE_CRON_ROUTES; CODEXIFY_ENABLE_DELEGATION_ROUTES; CODEXIFY_ENABLE_DEVTOOLS_ROUTES; CODEXIFY_ENABLE_DIRECT_MESSAGES_ROUTES; CODEXIFY_ENABLE_DOCUMENT_ROUTES; CODEXIFY_ENABLE_EMBEDDINGS_ROUTES; CODEXIFY_ENABLE_EXPORT_ROUTES; CODEXIFY_ENABLE_FEDERATION_ROUTES; CODEXIFY_ENABLE_FLOW_ROUTES; CODEXIFY_ENABLE_GOOGLE_CONNECT_ROUTES; CODEXIFY_ENABLE_GOOGLE_DRIVE_KNOWLEDGE_ROUTES; CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES; CODEXIFY_ENABLE_HEALTH_ROUTES; CODEXIFY_ENABLE_HEARTBEAT_ROUTES; CODEXIFY_ENABLE_HOSTED_ROOMS_ROUTES; CODEXIFY_ENABLE_HOSTED_ROOM_GUEST_ROUTES; CODEXIFY_ENABLE_IDDB_ROUTES; CODEXIFY_ENABLE_IMPRINT_ROUTES; CODEXIFY_ENABLE_INTENT_ROUTES; CODEXIFY_ENABLE_MEDIA_GENERATION_ROUTES; CODEXIFY_ENABLE_MEDIA_ROUTES; CODEXIFY_ENABLE_MEDIA_TTS_ROUTES; CODEXIFY_ENABLE_MEMORY_ROUTES; CODEXIFY_ENABLE_MIGRATION_ROUTES; CODEXIFY_ENABLE_MINIMAX_OAUTH_ROUTES; CODEXIFY_ENABLE_NEO_ROUTES; CODEXIFY_ENABLE_NOTION_KNOWLEDGE_ROUTES; CODEXIFY_ENABLE_OBSIDIAN_ROUTES; CODEXIFY_ENABLE_PERSONAL_FACTS_ROUTES; CODEXIFY_ENABLE_PERSONA_PROFILE_ROUTES; CODEXIFY_ENABLE_PROJECT_ROUTES; CODEXIFY_ENABLE_RESEARCH_ROUTES; CODEXIFY_ENABLE_SHARE_ROUTES; CODEXIFY_ENABLE_SYSTEM_DOCS_ROUTES; CODEXIFY_ENABLE_SYSTEM_PROMPT_ROUTES; CODEXIFY_ENABLE_THREADS_ROUTES; CODEXIFY_ENABLE_UI_SESSION_ROUTES; CODEXIFY_ENABLE_USER_PROFILE_ROUTES; CODEXIFY_ENABLE_WEBSOCKET_ROUTES; CODEXIFY_ENABLE_WORKTREE_ROUTES. Select which optional Guardian route families are mounted.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; backend process; supported-profile YAML and env flags.
- **Declaration → owner → consumer:** guardian/guardian_api.py route registration and guardian/core/supported_profile.py → mounted ASGI route inventory.
- **Precedence / conflict:** supported-profile route posture and core-only quarantine constrain per-route flags. Mounting is not authentication, adapter implementation, worker execution, or release support.
- **Mutation / access / timing:** operator selects profile/flags before backend startup; restart required. Boolean/label validation; non-secret. Inspect effective GET /health mounted-route inventory and OpenAPI visibility where permitted.
- **Status / UI / evidence:** active/internal according to each selected profile; operator-surface for route posture, do-not-surface as ordinary user toggles. Evidence: guardian/guardian_api.py route registration, guardian/core/supported_profile.py, ADR-072. Census: C3.

### O16 — GitHub Watchdog credential, review policy, and dispatch transport
- **Identifiers / purpose:** CODEXIFY_GITHUB_WATCHDOG_WEBHOOK_SECRET; CODEXIFY_GITHUB_WATCHDOG_APP_ID; CODEXIFY_GITHUB_WATCHDOG_APP_PRIVATE_KEY; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_INFERENCE_MODE; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODE; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_PROVIDER; CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODEL; GITHUB_WATCHDOG_REVIEW_QUEUE_NAME. Supply Watchdog's server credential boundary and inert/default review-policy snapshot; dispatch uses a separate Redis queue.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/worker; env plus durable attempt snapshot and Redis transport.
- **Declaration → owner → consumer:** guardian/core/config.py → guardian/watchdog/security.py, github_app.py and policy.py; queue module and review worker consume the dispatch queue name.
- **Precedence / conflict:** Watchdog selection does not inherit ambient chat provider/model; missing provider/model blocks policy, explicit escalation is required, and provider/egress rules remain authoritative. Queue acceptance is not execution.
- **Mutation / access / timing:** operator secret management and reviewed env before backend/worker startup; paired escalation fields and provider gates validate. Webhook secret/private key are secret; App ID/model identifiers non-secret. Inspect redacted attempt/policy receipts and worker state, never credentials.
- **Status / UI / evidence:** internal; operator-surface for policy and read-only diagnostics, do-not-surface for credentials. Evidence: guardian/core/config.py:494-563, guardian/watchdog/policy.py, guardian/queue/redis_queue.py:44-52, docs/architecture/config-and-ops.md:52-97. Census: C1/S4.

### O17 — Codex delegation and coding-agent loop controls
- **Identifiers / purpose:** CODEXIFY_CODEX_BIN; CODEXIFY_CODEX_TIMEOUT_SECONDS; CODEXIFY_GUARDIAN_PROJECTS_DIR; AGENT_TIMEOUT_SECONDS; AGENT_MAX_ATTEMPTS; AGENT_MIN_ATTEMPTS_BEFORE_ABORT; AGENT_NO_PROGRESS_WINDOW; AGENT_MAX_SAME_SIGNATURE_REPEATS; AGENT_REGRESSION_LIMIT; AGENT_AUTO_ROLLBACK_ON_FAIL; AGENT_VALIDATOR_MODEL_ENABLED; AGENT_REQUIRE_TWO_COMMITS; AGENT_VALIDATION_COMMIT_ALLOW_EMPTY; CODING_WORKER_MAX_VALIDATION_ATTEMPTS; CODING_WORKER_PATCH_ARTIFACT_ROOT; CODING_WORKER_POLL_INTERVAL_SECONDS; CODING_WORKER_WORKTREE_ROOT; PI_PROVIDER; PI_MODEL; ANTHROPIC_API_KEY. Bound coding/delegation execution and choose a separate Pi worker provider/model.
- **Class / audience / scope / persistence:** deployment-config; installation-operator for execution policy, developer-tester for local worker setup; worker/process and repository workspace; env/Compose.
- **Declaration → owner → consumer:** guardian/core/config.py agent fields → delegation/coding services; guardian/workers/coding_worker.py and Pi adapter/Compose worker → coding execution.
- **Precedence / conflict:** Pi worker model is distinct from ordinary chat provider/model. An accepted work order or queued task does not prove execution or approval. Worker auth store and API keys remain separate credential boundaries.
- **Mutation / access / timing:** operator/developer via env, image/worker configuration, then worker restart; attempt limits and path safety rules apply. ANTHROPIC_API_KEY and Pi auth material are secret; paths/model IDs non-secret. Inspect readiness command and durable coding-run readback, not key presence.
- **Status / UI / evidence:** internal/experimental; operator-surface for execution policy, developer-tester-only for local Pi setup. Evidence: guardian/core/config.py:246-255,567-636; guardian/workers/coding_worker.py; docs/architecture/config-and-ops.md:134-166. Census: C1.

### O18 — Remote Recall and provider web search
- **Identifiers / purpose:** REMOTE_RECALL_ENABLED; REMOTE_RECALL_PROVIDER; REMOTE_RECALL_MAX_RESULTS; REMOTE_RECALL_TIMEOUT_SECONDS; GROQ_WEB_SEARCH_ENABLED; GROQ_WEB_SEARCH_MODEL. Enable bounded provider search as external evidence during a turn.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env/core Settings.
- **Declaration → owner → consumer:** guardian/core/config.py → guardian/web/remote_recall.py and guardian/web/groq_search_adapter.py.
- **Precedence / conflict:** local-only, cloud-provider, egress and key gates are all required; web evidence is not user memory or authority. Turning a flag on does not prove live search availability.
- **Mutation / access / timing:** operator env and backend/worker restart; max-results/timeout bounds and provider validation apply. Non-secret fields; inspect gated health/trace and live provider response if qualified.
- **Status / UI / evidence:** experimental; operator-surface, with future user opt-in requiring separate policy/authority. Evidence: guardian/core/config.py:813-859, guardian/web/remote_recall.py. Census: C1/C5.

### O19 — Voice/STT route and turn runtime
- **Identifiers / purpose:** CODEXIFY_VOICE_MODE; CODEXIFY_VOICE_ROUTES_ENABLED; CODEXIFY_ENABLE_VOICE_TURNS; CODEXIFY_VOICE_TURNS_ENABLED; CODEXIFY_VOICE_STREAM_PROXY_ENABLED; CODEXIFY_STT_PROVIDER; CODEXIFY_STT_BASE_URL; CODEXIFY_LOCAL_STT_BASE_URL; CODEXIFY_LOCAL_VOICE_BASE_URL; CODEXIFY_VOICE_SERVICE_URL; CODEXIFY_VOICE_DELIVERY_FORMATS; CODEXIFY_VOICE_INTERNAL_FORMAT; CODEXIFY_STT_TIMEOUT_SECONDS; CODEXIFY_VOICE_COMPLETION_TIMEOUT_SECONDS; CODEXIFY_VOICE_INPUT_MAX_BYTES; CODEXIFY_VOICE_OUTPUT_MAX_BYTES; CODEXIFY_VOICE_MAX_DURATION_SECONDS; CODEXIFY_VOICE_TURN_DEDUPE_TTL_SECONDS; CODEXIFY_VOICE_BAKE_MODELS; CODEXIFY_DEFAULT_VOICE. Configure voice capture, STT transport, turn limits and formats.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env.
- **Declaration → owner → consumer:** guardian/voice/config.py and guardian/voice/runtime.py → voice routes, voice worker and STT service. Default voice selection is separately read in voice route/worker.
- **Precedence / conflict:** old CODEXIFY_VOICE_MODE, CODEXIFY_ENABLE_VOICE_TURNS, and STT/TTS URL aliases warn and map to current voice fields. Voice route/turn flags do not establish a speech backend. TTS provider resolution is separately cataloged as O20/O21.
- **Mutation / access / timing:** operator env and service restart; bounded byte/time/format validation. Endpoint URLs can carry sensitive topology; no credential value is listed. Inspect voice route/worker health and effective config diagnostics where available.
- **Status / UI / evidence:** internal with compatibility aliases; operator-surface. Evidence: guardian/voice/config.py:1-207, guardian/voice/runtime.py. Census: K3/A5.

### O20 — Guardian voice TTS-provider resolution
- **Identifiers / purpose:** CODEXIFY_TTS_PROVIDER; CODEXIFY_TTS_BACKEND; CODEXIFY_LOCAL_VOICE_BASE_URL; CODEXIFY_LOCAL_TTS_BASE_URL; CODEXIFY_TTS_SERVICE_PROVIDER; CODEXIFY_TTS_PRELOAD_ON_STARTUP; TTS_DEFAULT_PROVIDER; ELEVENLABS_API_KEY; MINIMAX_API_KEY; MINIMAX_TTS_URL; COQUI_TTS_MODEL; CODEXIFY_ENABLE_COQUI. Select a voice/TTS execution adapter and its optional external credentials.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/process; env.
- **Declaration → owner → consumer:** guardian/voice/config.py, guardian/tts/tts_manager.py and provider modules → mounted voice routes/services.
- **Precedence / conflict:** voice runtime prefers CODEXIFY_TTS_PROVIDER then CODEXIFY_TTS_BACKEND; the local TTS adapter reverses that order (O21). Same values can therefore select different backends on active paths. TTS profile selection U13 is separate.
- **Mutation / access / timing:** operator env/secret management and service restart; provider-specific validation. API keys secret; provider/URL/model identifiers mixed. Inspect voice/TTS health and one bounded synthesis result, not configured presence.
- **Status / UI / evidence:** active alternate live authority; operator-surface for adapter choice, do-not-surface for credentials. Evidence: guardian/voice/config.py:120-180, guardian/tts/tts_manager.py, guardian/tts/providers. Census: A5/K3.

### O21 — Local TTS adapter and service tuning
- **Identifiers / purpose:** CODEXIFY_TTS_LOCAL_ONLY; CODEXIFY_TTS_QWEN3_MODEL_PATH; CODEXIFY_TTS_QWEN3_PYTHON; CODEXIFY_TTS_QWEN3_RENDER_SCRIPT; CODEXIFY_TTS_OUTPUT_DIR; CODEXIFY_TTS_DEFAULT_VOICE; CODEXIFY_TTS_CHUNK_MAX_CHARS; CODEXIFY_TTS_SHORT_PAUSE_MS; CODEXIFY_TTS_LONG_PAUSE_MS; CODEXIFY_TTS_SERVICE_PROVIDER; CODEXIFY_TTS_TIMEOUT_SECONDS; CODEXIFY_TTS_INVOKE_TIMEOUT_SECONDS; CODEXIFY_VOICE_OUTPUT_MAX_BYTES; CODEXIFY_LOCAL_TTS_MODEL; CODEXIFY_LOCAL_TTS_VOICES; LOCAL_TTS_MODEL; QWEN_TTS_DEFAULT_SPEAKER; HF_HOME; HF_HUB_OFFLINE; TRANSFORMERS_OFFLINE. Configure local speech model paths, output, chunking and adapter budgets.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/service; env, .env.local/.env for standalone TTS CLI, model files.
- **Declaration → owner → consumer:** guardian/tts/config.py → local TTS routes/renderers; backend/tts_service/config.py and backend TTS scripts own a separate service registry/loader.
- **Precedence / conflict:** local TTS resolver prefers CODEXIFY_TTS_BACKEND then CODEXIFY_TTS_PROVIDER, opposite O20. Standalone CLI loads .env.local before .env only for absent process values; ASGI uses its own chain.
- **Mutation / access / timing:** operator env/model installation and service restart; chunk/pause and backend checks apply. Path/URL values may expose topology; no secret contents. Inspect TTS configuration/health and renderer result.
- **Status / UI / evidence:** active alternate live authority for backend selection; operator-surface. Evidence: guardian/tts/config.py:1-115, guardian/tts/providers/local_openai_compatible_provider.py, backend/tts_service/config.py. Census: A6.

### O22 — System JSON defaults and plugin CLI YAML
- **Identifiers / purpose:** guardian/config/system_config.py DEFAULT_CONFIG keys system.name/version/debug_mode/log_level; paths.base_dir/plugins_dir/memory_dir/logs_dir/temp_dir; threads.health_check_interval/heartbeat_timeout/shutdown_timeout; memory.max_artifacts/cleanup_threshold/min_confidence; agents.required/optional/startup_timeout; plugins.auto_discover/allow_remote/max_retries; security.require_authentication/token_expiry/max_failed_attempts. guardian/config_loader.py keys core.plugins_dir/conversation_token_limit, plugins.enabled, tts.default_provider/output_dir/providers, database.url; GUARDIAN_TOKEN_LIMIT; ELEVENLABS_API_KEY; GOOGLE_APPLICATION_CREDENTIALS; BOLT_URL. Configure process-local system directories/defaults and a separate plugin CLI.
- **Class / audience / scope / persistence:** deployment-config; installation-operator or developer-tester for CLI; process/installation; JSON config file, YAML and env.
- **Declaration → owner → consumer:** SystemConfig loads config.json and ensure_system_dirs is called in Guardian lifespan; ConfigLoader is constructed by guardian/chat/cli/plugin_cli.py. Neither is the general ASGI provider settings owner.
- **Precedence / conflict:** custom JSON recursively overlays defaults; CLI YAML overlays its defaults, then selected env values overlay YAML. The two stores remain specialized rather than aliases of core Settings.
- **Mutation / access / timing:** operator/developer edits files/env and reruns/restarts relevant process; directory/positive timeout checks apply. TTS/API credential members secret, remaining values mixed. Inspect resolved owner object and directories/CLI behavior; no universal UI view.
- **Status / UI / evidence:** active specialized SystemConfig; specialized CLI path; operator-surface for system directories, developer-tester-only for plugin CLI. Evidence: guardian/config/system_config.py:20-84, guardian/config_loader.py:18-117, guardian/guardian_api.py. Census: S1/S2.

### O23 — OAuth application registration and connector service endpoints
- **Identifiers / purpose:** GOOGLE_DRIVE_OAUTH_CLIENT_ID; GOOGLE_DRIVE_OAUTH_CLIENT_SECRET; GOOGLE_DRIVE_OAUTH_REDIRECT_URI; GOOGLE_OAUTH_CLIENT_ID; GOOGLE_OAUTH_CLIENT_SECRET; GOOGLE_OAUTH_REDIRECT; GOOGLE_RELAY_AUDIENCE; GOOGLE_RELAY_BROKER_URL; GOOGLE_CONNECTOR_MODE; MINIMAX_OAUTH_CLIENT_ID; MINIMAX_OAUTH_AUTHORIZE_URL; MINIMAX_OAUTH_TOKEN_URL; MINIMAX_OAUTH_ALLOWED_HOSTS; GDRIVE_OAUTH_TOKEN; GOOGLE_APPLICATION_CREDENTIALS; NOTION_API_KEY; NOTION_DATABASE_ID; GUARDIAN_SLACK_BOT_TOKEN; GUARDIAN_DISCORD_WEBHOOK_URL; GUARDIAN_TELEGRAM_BOT_TOKEN; CRON_WEBHOOK_ALLOWLIST. Configure application-side adapter registration, redirect/relay policy and channel credentials.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; installation/connector; env and server-side secret storage.
- **Declaration → owner → consumer:** guardian/connections/google_drive/oauth.py, guardian/connectors/google.py, guardian/connectors/minimax.py, guardian/connectors/notion.py, guardian/channels/adapters and guardian/routes/cron.py → connector-specific registration and transport.
- **Precedence / conflict:** application OAuth registration is not a user's connected-account grant. ADR-071 keeps user credentials server-owned and user-scoped, and the Connections catalog projection cannot become a second mutation route.
- **Mutation / access / timing:** operator via env/secret manager and service restart; redirect host/state/PKCE checks vary by adapter. Client secrets/tokens/bot credentials secret, URLs/IDs mixed. Inspect sanitized setup metadata and adapter-specific status.
- **Status / UI / evidence:** active only on mounted/proven adapters, otherwise internal; operator-surface for registration, do-not-surface for secrets. Evidence: guardian/connections/google_drive/oauth.py, guardian/connectors/minimax.py, guardian/channels/adapters, ADR-071/072. Census: S7.

### O24 — Command-bus loopback and guarded control paths
- **Identifiers / purpose:** GUARDIAN_COMMAND_BUS_LOOPBACK_BASE; CODEXIFY_ENABLE_COMMAND_BUS_ROUTES; CODEXIFY_ENABLE_TOOL_ROUTES; GUARDIAN_DEV_MODE. Select bounded Guardian loopback transport and whether command/tool routes mount.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/installation; env and supported profile.
- **Declaration → owner → consumer:** guardian/command_bus/loopback_http_adapter.py → command execution; guardian/guardian_api.py and supported profile → route registration.
- **Precedence / conflict:** route mounting does not grant tool/command permission; loopback URL is transport, not user action authority. A constrained non-Docker fallback exists.
- **Mutation / access / timing:** operator env and backend restart; loopback/policy validation applies. URL may reveal topology; non-secret identifier. Inspect route health and durable command receipts, not enqueue alone.
- **Status / UI / evidence:** internal; operator-surface for transport, do-not-surface in user settings. Evidence: guardian/command_bus/loopback_http_adapter.py and guardian/guardian_api.py. Census: S5/C3.

### O25 — Browser Host development transports
- **Identifiers / purpose:** GUARDIAN_DEV_MODE; GUARDIAN_EXPOSURE_MODE; GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED; GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED; CODEXIFY_BROWSER_HOST_PROOF_MODE; CODEXIFY_BROWSER_HOST_PROOF_TOKEN; CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN; CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN; CODEXIFY_BROWSER_HOST_NEGOTIATION_TIMEOUT_MS; CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_DEV_ENABLED; CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN; CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_TIMEOUT_MS; CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT; CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED; CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN; CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT; CODEXIFY_BROWSER_HOST_INSTANCE_ID; CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_TIMEOUT_MS. Enable bounded, local development negotiation and one-use attachment transport.
- **Class / audience / scope / persistence:** deployment-config; developer-tester; development process/session; env and one-use process-memory grant.
- **Declaration → owner → consumer:** guardian/browser_host/http_adapter.py and guardian/guardian_api.py; browser_host/src/runtime/config.js → trusted Browser Host main process, no renderer credential exposure.
- **Precedence / conflict:** Guardian and Browser Host gates must both be enabled with local_safe/proof mode; negotiated compatibility does not grant attachment authority. Grant is one-use and not persistent.
- **Mutation / access / timing:** developer test harness and bounded broker before process start; numeric-loopback origins, timeouts and instance ID validated. Proof token and attachment grant are secret/capability material; never inspect their contents. Inspect sanitized proof receipts.
- **Status / UI / evidence:** experimental/developer-only; developer-tester-only, do-not-surface grant/token. Evidence: browser_host/src/runtime/config.js:9-22, guardian/browser_host/http_adapter.py, docs/architecture/config-and-ops.md:202-295. Census: C1/C3.

### O26 — Web and desktop frontend bootstrap
- **Identifiers / purpose:** VITE_WEBUI_COMPOSE_BUNDLE; VITE_GUARDIAN_API_BASE; GUARDIAN_API_BASE; VITE_API_BASE_URL; VITE_API_BASE; VITE_SSE_PATH; VITE_SHARE_PUBLIC_BASE_URL; VITE_GUARDIAN_AUTH_MODE; VITE_PROXY_TARGET. Route the browser or desktop shell to its Guardian API, event stream, share origin, and authentication mode.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; browser build/desktop installation; Vite/build env, server-injected runtime env, Tauri launcher handoff and optional desktop overrides U15.
- **Declaration → owner → consumer:** frontend/src/lib/runtimeConfig.ts resolution → API client, SSE client and share links; Vite proxy target is development/Compose transport only.
- **Precedence / conflict:** launcher handoff or desktop override, Tauri config, explicit Vite values and origin-derived defaults form an ordered bootstrap chain; the exact winning source depends on runtime mode. U15 is a deliberate desktop override, not an account setting.
- **Mutation / access / timing:** installer/build operator or desktop Connection control; rebuild/reload/reinitialization as appropriate. URL/auth-mode normalization applies; non-secret URLs may reveal topology. Inspect the resolved RuntimeConfig snapshot and connectivity test.
- **Status / UI / evidence:** active; operator-surface, with U15 as the owning desktop control. Evidence: frontend/src/lib/runtimeConfig.ts:331-417,547-580, frontend/src/vite.config.ts and docker-compose.yml. Census: none.

### O27 — Browser session service and navigation limits
- **Identifiers / purpose:** BROWSER_MAX_SESSIONS; BROWSER_SESSION_TTL_SECONDS; BROWSER_URL_ALLOWLIST; STORAGE_BASE_PATH. Bound server-side browser sessions and permitted navigation targets.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/session; env and temporary session storage.
- **Declaration → owner → consumer:** guardian/browser/session_manager.py → browser session creation, expiry and URL checks.
- **Precedence / conflict:** allowlist policy is server-owned and is separate from client Browser Host development transport O25. Browser capture/episode history is governed by separate contracts and not established by these fields.
- **Mutation / access / timing:** operator env and service restart; count/TTL/URL validation is subsystem-specific. Non-secret policy with topology-sensitive URLs. Inspect bounded browser session diagnostics, not a UI preference.
- **Status / UI / evidence:** internal; operator-surface. Evidence: guardian/browser/session_manager.py. Census: specialized direct owner, not C1.

### O28 — Import, export, sharing, and data lifecycle budgets
- **Identifiers / purpose:** CODEXIFY_CHATGPT_IMPORT_EMBEDDINGS; CODEXIFY_CHATGPT_IMPORT_EMBED_ISOLATED; CODEXIFY_CHATGPT_IMPORT_EMBED_TIMEOUT_SECONDS; CODEXIFY_CHATGPT_IMPORT_MAX_EMBED_TEXT_CHARS; CODEXIFY_FILENAME_TEMPLATE; CODEXIFY_SHARE_ANYONE; CHATGPT_EXPORT_FILE; IMPORT_STAGING_BASE_PATH; MEDIA_TITLE_MODE; MEMORY_RETENTION_DAYS. Control import embedding work, export/share behavior, staging and retention.
- **Class / audience / scope / persistence:** deployment-config; installation-operator for runtime policy, developer-tester for import CLI input; process/installation; env, DB job records and filesystem.
- **Declaration → owner → consumer:** backend/rag/chatgpt_migration.py and guardian/services/openai_account_import.py; guardian/export_engine.py; guardian/routes/memory.py; import CLI scripts. User import/export buttons are one-shot actions, not these policy settings.
- **Precedence / conflict:** canonical Postgres materialization and vector derivation are distinct; an upload or embed flag does not prove recall. The share-anyone value does not bypass authentication/ownership policy. CLI path values do not become API runtime authority.
- **Mutation / access / timing:** operator env/restart, developer CLI flags; text/time bounds and owner checks vary by path. Export files and imported content are sensitive; identifiers are non-secret. Inspect durable import job/readback and share/export result, not staging alone.
- **Status / UI / evidence:** active/bounded or CLI-only by path; operator-surface for policy, developer-tester-only for CLI input. Evidence: backend/rag/chatgpt_migration.py, guardian/services/openai_account_import.py, guardian/export_engine.py, guardian/routes/memory.py. Census: specialized direct owners.

### O29 — Cron, webhook and automation runtime
- **Identifiers / purpose:** CRON_QUEUE_NAME; CRON_SCHEDULER_POLL_SECONDS; CRON_WEBHOOK_ALLOWLIST; CONNECTOR_SYNC_INTERVAL; GUARDIAN_CONNECTOR_SYNC_INTERVAL; ENABLE_CONNECTOR_WORKER; DELEGATION_WORKER_POLL_INTERVAL_SECONDS. Schedule existing jobs, bound polling, and restrict webhook destinations.
- **Class / audience / scope / persistence:** deployment-config; installation-operator; process/worker; env and durable job configuration.
- **Declaration → owner → consumer:** guardian/cron/scheduler.py, guardian/routes/cron.py, guardian/routes/connectors.py, guardian/workers/delegation_worker.py → schedulers and workers.
- **Precedence / conflict:** connector sync interval accepts the GUARDIAN-prefixed value before its compatibility alias; schedule definitions and connector authorization are separate durable owners. Polling configuration does not prove a job executed.
- **Mutation / access / timing:** operator env/worker restart; allowed destinations and positive intervals validate. Webhook destinations may expose private topology; non-secret identifiers. Inspect job record and worker events.
- **Status / UI / evidence:** active/internal by route profile; operator-surface. Evidence: guardian/cron/scheduler.py, guardian/routes/cron.py, guardian/routes/connectors.py:85-120. Census: S4 and specialized owners.

### O30 — Image generation, research adapters, and optional provider paths
- **Identifiers / purpose:** IMAGE_GEN_PROVIDER; IMAGE_GEN_MODEL; DEEPSEEK_API; GEMINI_API; GEMINI_API_KEY; XAI_API_KEY; OPENAI_EMBEDDING_MODEL; OPENAI_EMBED_MODEL; OLLAMA_EMBED_MODEL; GUARDIAN_PROVIDER; GUARDIAN_CHAT_PROVIDER; GUARDIAN_DEFAULT_MODEL; DEFAULT_CLOUD_MODEL; CLOUD_BACKEND. Configure optional image/research/provider adapters that are distinct from canonical chat routing.
- **Class / audience / scope / persistence:** deployment-config; installation-operator or developer-tester; process/adapter; env.
- **Declaration → owner → consumer:** guardian/image_gen/router.py, guardian/core/research/Modules, guardian/providers, guardian/core/dependencies.py → their respective optional routes or helpers.
- **Precedence / conflict:** Q2 says reachability of every optional legacy/MemoryOS provider path was not proven. A shared API key name does not make these adapters the canonical chat provider owner.
- **Mutation / access / timing:** operator/developer env and process restart; provider-specific validation. API keys secret; model/selector fields non-secret. Inspect mounted route and executed adapter evidence where needed.
- **Status / UI / evidence:** unresolved/experimental or legacy by path; unresolved for broad UI exposure. Evidence: guardian/image_gen/router.py, guardian/providers/registry.py, guardian/core/dependencies.py, guardian/core/research/Modules. Census: Q2.

### O31 — Logging, debug, auth fallback, and startup switches
- **Identifiers / purpose:** LOG_LEVEL; GUARDIAN_LOG_LEVEL; GUARDIAN_LOG_FILE; GUARDIAN_LOG_MAX_MB; GUARDIAN_LOG_BACKUPS; GUARDIAN_SCRUB_LOGS; GUARDIAN_SCRUB_EXTRA_EXTS; GUARDIAN_SCRUB_EXTRA_NAMES; GUARDIAN_SCRUB_PLAINTEXT_SECRETS; GUARDIAN_SCRUB_SECRET_KEYWORDS; GUARDIAN_SCRUB_SECRET_WINDOW; CODEXIFY_REQUEST_TIMING_LOG; CODEXIFY_DEBUG_UNREDACTED_TOOL_INTENTS; DEBUG; LOCAL_DEV; DEV_MODE; GUARDIAN_DEV_MODE; GUARDIAN_ENABLE_RATE_LIMITING; GUARDIAN_ENABLE_SECURITY_HEADERS; GUARDIAN_CSP_POLICY; GUARDIAN_CORS_ORIGINS; GUARDIAN_CORS_METHODS; GUARDIAN_CORS_HEADERS; GUARDIAN_CORS_ALLOW_CREDENTIALS. Control process observability and development-only safeguards.
- **Class / audience / scope / persistence:** deployment-config; installation-operator or developer-tester; process/installation; env.
- **Declaration → owner → consumer:** guardian/server/app.py alternate server surface, guardian/guardian_api.py canonical startup, guardian/core/auth.py, guardian/context/broker.py and logging helpers → diagnostics/request policy.
- **Precedence / conflict:** U1 alternate ASGI app is not proven active; its GUARDIAN_* logging/CORS fields do not automatically govern canonical ASGI. DEBUG/LOCAL_DEV can change local override behavior and must not be presented as harmless cosmetics.
- **Mutation / access / timing:** operator/developer env and process restart; exposure/auth mode constrain debug settings. Log scrub lists are policy-sensitive, and unredacted tool intent logging can expose data; no values recorded. Inspect redacted logs and effective response headers, not variable presence.
- **Status / UI / evidence:** internal/experimental, with U1 reachability unresolved; developer-tester-only for debug and operator-surface for production logging/security policy. Evidence: guardian/server/app.py, guardian/guardian_api.py, guardian/core/auth.py, guardian/context/broker.py. Census: U1/C2/A2.

## Catalog: legacy, compatibility, and uncertain resolvers

### L01 — Independent legacy Settings model
- **Identifiers / purpose:** guardian.config.core.Settings: DEFAULT_RATE_LIMIT, MEMORY_BATCH_SIZE, MEMORY_FLUSH_INTERVAL, MAX_MEMORY_BUFFER, LOG_DIR, SAFE_MODE, SAFE_MODE_RATE_LIMIT, CACHE_ENABLED, PLUGIN_DIR, GENAI_API_KEY, NOTION_API_KEY, GOOGLE_API_KEY, GUARDIAN_API_KEY, GUARDIAN_API_KEYS, GUARDIAN_DATABASE_URL, OPENAI_API_KEY, OPENAI_API_ENDPOINT, OPENAI_MODEL, GROQ_API_KEY, GROQ_API_ENDPOINT, GROQ_MODEL, GROQ_VISION_MODEL, ANTHROPIC_API_KEY, ANTHROPIC_API_ENDPOINT, ANTHROPIC_MODEL, VECTOR_STORE, AI_BACKEND, ENV, OLLAMA_MODEL, OLLAMA_HOST, CLOUD_ONLY, HYBRID_ENABLED, LOCAL_MODEL_NAME, LOCAL_API_HOST, CLOUD_MODEL_NAME, CLOUD_API_HOST, CODEXIFY_SECRET_STORE, CODEXIFY_REQUIRE_SECRET_STORE. This is the older independent loader for auth, database and provider defaults; these names are not one unified user preference.
- **Class / audience / scope / persistence:** deployment-config; installation-operator for active auth/DB fields, developer-tester or unresolved for other legacy fields; process; environment and Pydantic .env read on each getter call.
- **Declaration → owner → consumer:** guardian/config/core.py declares and validates the model; guardian/config/__init__.py exports its getter; guardian/core/dependencies.py uses it for active authentication and database initialization. Consumers of individual remaining fields require separate proof before UI exposure.
- **Precedence / conflict:** this model uses extra=allow and a fresh construction per call, unlike the imported singleton in guardian/core/config.py. A1 is an alternate live authority for shared auth/DB fields; K2 compares selected overlaps without replacing either owner. Provider and storage defaults here may differ from C1.
- **Mutation / access / timing:** installation operator supplies env/dotenv before relevant call or startup; production provider-key and secret-store validation are model-specific. API keys, database URL and secret-store material are secret/mixed; inspect redacted auth/DB behavior, not values. Other fields have unresolved effective-value inspection and mutation ownership.
- **Status / UI / evidence:** active for verified auth/DB consumers, legacy/unresolved for remaining declarations; operator-surface for active controls, do-not-surface or unresolved for unproven fields. Evidence: guardian/config/core.py:38-203, guardian/config/__init__.py, guardian/core/dependencies.py. Census: A1/K2.

### L02 — Revisionless system-profile fallback
- **Identifiers / purpose:** LOCAL_LLM_MODEL; DEFAULT_LOCAL_MODEL; LLM_MODEL; LLM_PROVIDER; CHAT_PROVIDER; GUARDIAN_SYSTEM_PROFILES_JSON; profile_id, mode, provider_override, model_override, temperature_override and system_prompt_blocks in the fallback catalog. These select legacy default/cloud/local profile behavior when a thread has no selected Persona revision.
- **Class / audience / scope / persistence:** deployment-config for environment catalog/defaults, runtime-setting for a persisted thread profile override; installation-operator or application-user through the owning thread/profile control; process and thread; env JSON, thread metadata and profile records.
- **Declaration → owner → consumer:** guardian/cognition/system_profiles/resolver.py builds the fallback catalog and resolves a thread profile; guardian/core/chat_completion_service.py calls the resolver during completion assembly.
- **Precedence / conflict:** selected Persona revision, thread profile and legacy fallback are separate branches. A7 directly reads local model aliases and provider variables before core global fallback; its relationship to ADR-074's explicit operator model exception is not fully specified. An env catalog entry does not prove selection or availability.
- **Mutation / access / timing:** operator edits env/restarts for fallback defaults; user changes an authorized thread/profile selection through its owner for subsequent turns. Prompt blocks may contain private material; provider/model identifiers are non-secret. Inspect resolved profile and thread metadata, with availability checked separately.
- **Status / UI / evidence:** legacy alternate live authority for revisionless branch; unresolved as general All Settings editor, link-to-owning-control for a durable selected profile. Evidence: guardian/cognition/system_profiles/resolver.py:225-350,540-617; guardian/core/chat_completion_service.py. Census: A7.

### L03 — Alternate historical ASGI application
- **Identifiers / purpose:** guardian.server.app.app, its own lifespan and direct GUARDIAN_* logging/CORS/security settings noted in O31. This is an alternate bootstrap definition, not a confirmed active installation setting.
- **Class / audience / scope / persistence:** deployment-config; developer-tester; process; environment.
- **Declaration → owner → consumer:** guardian/server/app.py declares the app; the checked-in launcher guardian/server/run.py targets guardian.guardian_api:app. The bounded census found test imports but no runtime caller for this alternate app.
- **Precedence / conflict:** if an external launcher selects it, its own startup path would apply; current deployment reachability is unresolved. Do not combine its effective settings with the canonical ASGI path.
- **Mutation / access / timing:** developer selects an entrypoint and env before process start; validation and secret status vary by referenced O31/O03 fields. Inspect selected ASGI command and actual mounted app. No supported application-user control.
- **Status / UI / evidence:** declared-no-consumer-found in bounded runtime scan; developer-tester-only. Evidence: guardian/server/app.py, guardian/server/run.py, config-authority-path-census.md:164. Census: U1.

### L04 — Mutable dict runtime settings singleton
- **Identifiers / purpose:** guardian.config.settings.RuntimeConfig, _RuntimeConfig_SINGLETON and get_settings(). Hold arbitrary dynamic process-local keys; no fixed setting field or environment binding is declared.
- **Class / audience / scope / persistence:** unresolved; no-human-control; process memory.
- **Declaration → owner → consumer:** guardian/config/settings.py declares the singleton; no runtime caller was found in the bounded census.
- **Precedence / conflict:** independent from both Pydantic Settings classes; no merge or persistence contract. Any future caller would need its own ownership and validation proof.
- **Mutation / access / timing:** programmatic assignment only; immediate within that singleton, with no known durable effect or inspection endpoint. Secret status unknown because arbitrary keys are accepted.
- **Status / UI / evidence:** declared-no-consumer-found; do-not-surface. Evidence: guardian/config/settings.py:5-22; config-authority-path-census.md:165. Census: U2.

### L05 — Flow tuner settings
- **Identifiers / purpose:** FLOW_CONTEXT_WINDOW, FLOW_INJECTION_RATIO, FLOW_LOCAL_MAX_TOKENS, FLOW_CLOUD_MAX_TOKENS and FLOW-prefixed key/backend/path fields generated from FlowConfig fields. Bound a prospective narrative-context tuner; the additional key fields may contain secrets.
- **Class / audience / scope / persistence:** deployment-config; developer-tester; process; .env and FLOW_-prefixed environment.
- **Declaration → owner → consumer:** guardian/modules/flow_tuner.py FlowConfig declares the fields; only its example and focused test were found by the bounded census.
- **Precedence / conflict:** independent BaseSettings resolver; no proven integration with current chat context/retrieval ownership. Field naming follows Pydantic env-prefix behavior rather than a documented runtime contract.
- **Mutation / access / timing:** developer env before FlowConfig construction; positive/bounded numeric checks are not fully established. Secret status mixed; no current effective-value inspector or user control.
- **Status / UI / evidence:** declared-no-consumer-found for runtime; developer-tester-only. Evidence: guardian/modules/flow_tuner.py:31-68; config-authority-path-census.md:166. Census: U3.

### L06 — Legacy graph compatibility factory
- **Identifiers / purpose:** get_graph_backend(); GUARDIAN_ENABLE_GRAPH_WRITES; GUARDIAN_GRAPH_BACKEND; NEO4J_URI; NEO4J_USER; NEO4J_USERNAME; NEO4J_PASSWORD; NEO4J_PASS; NEO4J_DATABASE. Choose a graph adapter in the older compatibility factory.
- **Class / audience / scope / persistence:** deployment-config; developer-tester/installation-operator if externally selected; process; environment and core settings.
- **Declaration → owner → consumer:** guardian/memory_graph/graph_backend_factory.py defines this older factory; maintained graph worker calls get_graph_backend_adapter() in O13 instead. No runtime caller for get_graph_backend() was found in the bounded census.
- **Precedence / conflict:** the older factory combines raw and typed inputs; the active C6 factory directly parses write/backend flags and fails closed. Shared names do not prove a live conflicting selection.
- **Mutation / access / timing:** operator/developer env before construction; write flag/backend allowlist and Neo4j credentials constrain use. Password secret; rest mixed. Inspect selected worker adapter metadata, not this unused-looking method.
- **Status / UI / evidence:** declared-no-consumer-found for the compatibility factory; do-not-surface. Evidence: guardian/memory_graph/graph_backend_factory.py:46-109,145-204; config-authority-path-census.md:167. Census: U4.

### L07 — Scoped embedder fallback and optional provider adapters
- **Identifiers / purpose:** CODEXIFY_EMBEDDINGS_BACKEND; EMBEDDING_BACKEND; CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK; LOCAL_EMBED_MODEL; backend.rag.embedder.Embedder fallback; guardian.providers adapter keys/models; local MemoryOS environment reads. These control optional or diagnostic paths when those paths are actually selected.
- **Class / audience / scope / persistence:** deployment-config; installation-operator or developer-tester; process/CLI; environment.
- **Declaration → owner → consumer:** backend/rag/embedder.py defines fallback reads, with scoped health diagnostic use; guardian.vector.store.VectorStore normally passes C4's explicit values. Legacy guardian.providers and MemoryOS consumers are path-dependent.
- **Precedence / conflict:** C4 owns active VectorStore selection; an unparameterized Embedder invocation or optional adapter could resolve independently. Reachability of every optional path is unproven and must not be called an active competing authority.
- **Mutation / access / timing:** operator/developer env and process restart; fallback must respect provider/egress and derived-index constraints. Credential names secret where present, other identifiers non-secret. Inspect actual selected caller and retrieval provenance.
- **Status / UI / evidence:** unresolved; unresolved for UI exposure. Evidence: backend/rag/embedder.py:59-102,651-695, guardian/vector/store.py, guardian/providers, config-authority-path-census.md:168-169. Census: Q1/Q2.

## Exact-identifier supplement for compressed operator families

The O-family descriptions above use a slash to save space for related keys. The following expands those spellings from guardian/core/config.py Settings so searches for exact identifiers remain possible. These are members of the named O family, not new settings or an additional resolver.

| Family | Exact identifiers not spelled in full above |
|---|---|
| O06 | WS_RPC_IDLE_TIMEOUT_SECONDS; WS_RPC_MAX_CONNECTIONS; WS_RPC_RATE_LIMIT_NAMESPACE; WS_RPC_RATE_LIMIT_REFILL_PER_SECOND |
| O07 | PROVIDER_RETRY_JITTER_SECONDS; PROVIDER_RETRY_MAX_SECONDS |
| O08 | CODEXIFY_WHOOSHD_THREADWAKE_MODE; CODEXIFY_WHOOSHD_THREADWAKE_SCOPE; WHOOSHD_COMMAND; WHOOSHD_HEALTH_POLL_INTERVAL_SECONDS; WHOOSHD_HOST; WHOOSHD_MODEL_REGISTRY_PATH; WHOOSHD_PORT; WHOOSHD_STARTUP_TIMEOUT_SECONDS; WHOOSHD_STOP_ON_EXIT; WHOOSHD_WORKING_DIR |
| O09 | ALIBABA_API_BASE; ALIBABA_MODEL; ALIBABA_MODEL_DISCOVERY_TIMEOUT_SECONDS; ALIBABA_MODEL_DISCOVERY_URL; ALIBABA_TIMEOUT_SECONDS; DEEPSEEK_BASE_URL; DEEPSEEK_CHAT_MODEL; DEEPSEEK_MODEL_DISCOVERY_TIMEOUT_SECONDS; DEEPSEEK_MODEL_DISCOVERY_URL; GROQ_BASE_URL; GROQ_MODEL_DISCOVERY_TIMEOUT_SECONDS; GROQ_MODEL_DISCOVERY_URL; MINIMAX_ANTHROPIC_VERSION; MINIMAX_API_BASE; MINIMAX_API_FLAVOR; MINIMAX_MODEL; MINIMAX_MODEL_DISCOVERY_TIMEOUT_SECONDS; MINIMAX_MODEL_DISCOVERY_URL; MINIMAX_TIMEOUT_SECONDS; OPENAI_BASE_URL |
| O10 | LOCAL_EXTENDED_THINKING_MODEL_PATTERNS; LOCAL_NO_THINK_INSTRUCTION; LOCAL_NO_THINK_SKIP_MODEL_PATTERNS |
| O12 | PROMPT_DIR_PATH |

Direct literal environment reads outside the two Settings models were also checked. These additional exact identifiers belong to the existing families; their source-specific precedence remains as stated in those records and is not implied to be unified:

| Family | Additional direct-read identifiers and effect |
|---|---|
| O03 | GUARDIAN_ALLOW_DUMMY_SETTINGS (legacy test/CI fallback only); GUARDIAN_RATE_LIMITS (alternate historical ASGI rate-limit input); CODEXIFY_IDENTITY_DIR (identity file location) |
| O04 | DB_WAIT_INTERVAL; DB_WAIT_SECONDS; GUARDIAN_DB_PATH (legacy/local DB path) |
| O05 | CHAT_WORKER_HEARTBEAT_TTL_SECONDS; VOICE_HEARTBEAT_INTERVAL_SECONDS; VOICE_HEARTBEAT_TTL_SECONDS; WARMUP_BACKOFF_BASE_SECONDS; WARMUP_BACKOFF_MAX_SECONDS; WARMUP_MAX_RETRIES; WARMUP_READINESS_BACKOFF_BASE_SECONDS; WARMUP_READINESS_BACKOFF_MAX_SECONDS; WARMUP_READINESS_REQUEST_TIMEOUT_SECONDS; WARMUP_READINESS_TIMEOUT_SECONDS (worker heartbeat and bounded warmup retry policy) |
| O06 | UI_SESSION_MAX_TTL_SECONDS; UI_SESSION_TTL_SECONDS (session expiry) |
| O08 | LOCAL_PORT; LOCAL_WARMUP_TIMEOUT_SECONDS; DOCKER_CONTAINER; VAULTNODE_ALLOW_LOCALHOST; VAULTNODE_BASE_URL; VAULTNODE_FORCE_OPENAI_COMPAT; VAULTNODE_HEALTH_ENDPOINTS; VAULTNODE_PORT (warmup target and health probing; separate from ADR-074 model authority) |
| O09 | GEMINI_CHAT_MODEL; GROQ_CHAT_MODEL; OPENAI_CHAT_MODEL; OPENAI_MODEL_CHAT; GROQ_FALLBACK_MODEL; OPENAI_API_BASE (legacy/optional adapter model and base URL reads, subject to Q2) |
| O10 | FORESIGHT_TIMEOUT; SYSTEM_PROMPT_HARD_TOKENS; SYSTEM_PROMPT_WARN_TOKENS (specialized orchestration/prompt budgets) |
| O11 | EMBEDDER; GUARDIAN_EMBEDDER; LOCAL_EMBEDDINGS_REQUIRED (embedding route/compiled-runtime choices; path dependent) |
| O12 | CODEXIFY_DEFAULT_FOLDER; IMPRINT_PROMPT_DIR (alternate API/import onboarding storage paths) |
| O13 | GUARDIAN_ENABLE_GRAPH_INGEST_QUERY_DEBUG (diagnostic graph query flag) |
| O15 | ENABLE_BLIP_MODEL (optional model enablement) |
| O17 | CODEX_ROOT; OLLAMA_PROXY_BIND_HOST; OLLAMA_PROXY_BIND_PORT; OLLAMA_PROXY_TARGET_HOST; OLLAMA_PROXY_TARGET_PORT (coding-worker filesystem and launcher proxy transport) |
| O19 | CODEXIFY_STT_MOCK_TEXT; CODEXIFY_STT_MODEL (voice test input/model) |
| O21 | HF_TOKEN (optional model download credential; secret) |
| O23 | GITHUB_TOKEN (GitHub connector credential; secret) |
| O26 | GUARDIAN_API_HOST; GUARDIAN_API_PORT; GUARDIAN_API_RELOAD; GUARDIAN_API_WORKERS (ASGI launcher binding and development reload/worker count) |

The direct-read supplement is a locator, not proof that every optional consumer is mounted or executed. Its worker, prompt, alternate-ASGI and launcher entries remain installation or developer controls, not application-user preferences.

## Explicit exclusions after first-party inspection

These candidates were inspected but are not independent editable setting families in this catalog. An excluded first-party mechanism may still be an action, fact, cache or sensitive value elsewhere in the product.

| Candidate / source | Reason for exclusion | Owning record or control |
|---|---|---|
| cfy.hasUserUpload in SettingsView.tsx | Marker derived from an upload; it is not a preference and should not be manually set. | U02 derived member |
| SettingsView.tsx and AppShell.tsx provider catalog, feature and navigation localStorage/sessionStorage records | Cached projections or navigation continuity; clearing/rebuilding them is not a change to provider, route or feature authority. | U16 |
| personaStudioStore.ts drafts and pending editor state | Draft data and editing workflow, not independent configuration authority; a saved revision is U10/U11. | U10/U11 and Persona Studio |
| Workspace scratchpad text in useWorkspaceScratchpadState.ts | User content, not a configuration choice; its presentation toggles are U17. | U17 |
| Imported files, staged ChatGPT/Claude export payloads, upload previews and import job IDs | Data inputs and workflow records. An upload or staging event does not configure canonical persistence or prove materialization. | O28 policy; import workflow |
| Connector credentials, OAuth tokens, PKCE state, one-use attachment grants and API key contents | Secret/capability values whose identifiers and owner are cataloged, but whose values must not appear in a settings directory. | U14, U15, O03, O23, O25 |
| Provider health, live model inventory, route inventory, queue depth, job receipts and task events | Observations/derived runtime state, not configuration. They may be read-only status alongside an owning setting. | O02, O05, O07–O09, O15, O29 |
| Compose service/container names, Docker networking and dependency wiring | Assembly and transport; no additional provider/model selection authority under ADR-074. Material environment inputs passed through Compose are cataloged. | O02/O04/O05/O08/O26 |
| Test fixture literals, test-only monkeypatch values and proof-script one-shot arguments under tests/ and scripts/ | They exercise or observe settings but do not establish persistent product controls. A first-party runtime key used by a script is cataloged under its runtime owner. | Developer/test runner |
| Lockfiles, generated diagrams, vendored configuration, ordinary hardcoded constants and package-manager settings | Outside first-party behavioral configuration declarations; no user/operator setting authority established by the inspected paths. | None |
| User messages, Personal Facts, documents, conversation titles and prompt output | Domain content or derived text, not a configuration setting. Their policy and inclusion controls are U05/U07/U09/U10. | Corresponding data owner |
| ALLOW_NET_TESTS, MINIMAX_SMOKE_TEST, MINIMAX_SMOKE_TIMEOUT_SECONDS, TEST_DATABASE_URL, GUARDIAN_MEMORY_DB_PATH, MEMORY_DB_PATH | Test harness/test data inputs found under test trees; they do not define a production setting. | Test runner |
| GITHUB_ACTIONS, PYTEST_CURRENT_TEST, PATH | External execution-context indicators consumed by first-party code; Codexify does not own their values as product settings. | CI, test runner, operating system |
| CFY_EMBED_MODEL_DIR, CFY_EMBED_MODEL_REPO, CFY_EMBED_MODEL_REVISION, HF_PREFETCH_MODELS | One-shot model prefetch/ensure script inputs; no separate app runtime setting is established. The installed model inventory is runtime observation. | Deployment scripts |

## Reconciliation with the 30-path authority census

The classification names below are carried from config-authority-path-census.md. They describe the inspected path, not the current release state. Each ID is accounted for; multiple IDs may lead to one family because that family explicitly describes their conflict.

| Census ID and inherited classification | Catalog destination | Boundary retained |
|---|---|---|
| C1 canonical authority | O01, O03, O06–O11, O13–O15 | Core typed Settings and import-time singleton |
| C2 canonical authority | O01, O31 | Primary ASGI dotenv chain and startup order |
| C3 canonical authority | O02, O07–O09, O15 | Supported-profile posture |
| C4 canonical authority | O11 | Active VectorStore resolver |
| C5 canonical authority | O07 | One egress policy gateway with two input modes |
| C6 canonical authority | O13, L06 | Active graph adapter, distinct from unused-looking compatibility factory |
| K1 compatibility path | O08, O09 | Legacy model aliases normalize into core fields |
| K2 compatibility path | O01, L01 | Coherence comparison does not merge the two models |
| K3 compatibility path | O19–O21 | Warning-backed voice aliases stay with voice owner |
| S1 specialized owner | O22 | SystemConfig JSON/directory defaults |
| S2 specialized owner | O22 | Plugin CLI YAML/env object |
| S4 specialized owner | O05 | Redis queue transport |
| S5 specialized owner | O24 | Command-bus loopback endpoint |
| S6 specialized owner | O12 | Storage provider selection |
| S7 specialized owner | O23, U14 | Application OAuth registration distinct from user grant |
| S8 specialized owner | O12 | Media-signing secret fallback |
| S10 specialized owner | O11 | CLI embedder distinct from API VectorStore |
| A1 alternate live authority | L01, O01, O03, O04 | Fresh legacy Settings for active auth/DB |
| A2 alternate live authority | O03, O31 | Direct startup/request authentication reads |
| A3 alternate live authority | O04 | API/core adapter DSN ordering |
| A4 alternate live authority | O04 | Worker/migration DSN alias/default ordering |
| A5 alternate live authority | O20 | Voice runtime TTS resolver |
| A6 alternate live authority | O21 | Local TTS resolver with opposite selector order |
| A7 alternate live authority | L02, O08, U09/U10 | Revisionless profile branch before global fallback |
| U1 apparently unreferenced | L03, O31 | Alternate historical ASGI app; no runtime caller found in bounded scan |
| U2 apparently unreferenced | L04 | Dict singleton; no runtime caller found |
| U3 apparently unreferenced | L05 | FlowConfig; only example/test callers found |
| U4 apparently unreferenced | L06, O13 | Legacy graph factory; maintained worker uses C6 |
| Q1 uncertain | L07, O11 | Unparameterized embedder fallback not proven to own normal VectorStore |
| Q2 uncertain | L07, O09/O30 | Optional legacy provider/MemoryOS reachability not fully established |

The classification-and-consolidation plan's Stage 0 distinction is retained: installation env, manifests, JSON and CLI YAML are deployment-config; durable account/thread/profile choices are runtime-setting candidates; browser-only choices are client-preference; caches remain derived-or-cache-state. This catalog performs inventory only. It does not consolidate deployment configuration, create a managed runtime-settings service, migrate browser state, or approve UI mutation. The older plan did not enumerate all of the frontend, Persona, Connections and specialized paths above; this deeper inventory records them without rewriting its stages.

## Unresolved authority questions

1. **Core/legacy startup timing:** Can the import-time core singleton and later dotenv chain observe different effective values in a supported launch? O01/L01 identify the ordering; no live divergence is claimed.
2. **Auth and DB precedence:** Which single resolver should own the overlapping A1–A4 key and DSN inputs if consolidation proceeds? O03/O04 retain the present ordering differences.
3. **Voice selector precedence:** A5 prefers CODEXIFY_TTS_PROVIDER and A6 prefers CODEXIFY_TTS_BACKEND. A later architecture task must decide whether these are intentionally separate scopes or should converge.
4. **Revisionless provider defaults:** A7 converts local to openai in one legacy cloud profile branch. Its relationship to the ADR-074 profile/operator/Whoosh'd authority model needs an explicit contract before any general model control is proposed.
5. **Optional path reachability:** Q1/Q2 and U1–U4 require selected-entrypoint or caller proof before deprecation, UI exposure or consolidation. No runtime caller found is weaker than dead code.
6. **Extended Persona fields:** U11 can be authored and stored, but the inspected five-field chat resolver seam does not consume every voice, capability or retrieval field. The effective consumers and any approval/binding rules need per-field proof.
7. **Browser state ownership:** U06 and U08/U17 are device-local. A cross-device managed preference would require an accepted owner, migration, conflict rule and consent boundary.
8. **Feature/route controls:** O15 contains route/profile/development flags with different consumers. Per-flag support and effective-value inspection must be proven before an operator editor is designed.
9. **Specialized configuration observability:** O05/O06/O22/O23/O29 lack a uniform safe effective-value readback. A future directory must show unknown rather than echo an env declaration as effective truth.
10. **Catalog exhaustiveness at runtime:** Direct env reads and optional plugin/provider entrypoints may be selected outside the checked-in launch. This is a first-party repository inventory, not a live deployment or exhaustive external extension inventory.

## Summary by audience, class, status, and UI disposition

There are **55 cataloged setting families** (U01–U17, O01–O31, L01–L07), **14 explicit exclusion rows**, **10 unresolved authority questions**, and **30 reconciled census pathways**. Counts below assign each family one primary bucket for navigation; mixed family members and secondary dispositions remain explicit in their records. In particular, a secret member remains do-not-surface even when its family is primarily operator-surface.

| Dimension | Primary bucket | Families |
|---|---|---:|
| Audience | application-user | 15 |
| Audience | installation-operator | 33 |
| Audience | developer-tester | 4 |
| Audience | no-human-control | 2 |
| Audience | unresolved | 1 |
| Class | deployment-config | 38 |
| Class | runtime-setting | 8 |
| Class | client-preference | 7 |
| Class | derived-or-cache-state | 1 |
| Class | unresolved | 1 |
| Status | active | 35 |
| Status | compatibility | 1 |
| Status | legacy | 1 |
| Status | declared-no-consumer-found | 5 |
| Status | internal | 9 |
| Status | experimental | 2 |
| Status | unresolved | 2 |
| UI | primary-settings | 4 |
| UI | all-settings-directory | 5 |
| UI | link-to-owning-control | 4 |
| UI | read-only-information | 2 |
| UI | operator-surface | 31 |
| UI | developer-tester-only | 3 |
| UI | do-not-surface | 3 |
| UI | unresolved | 3 |

The four primary-settings families are U01, U02, U04 and U05. The five primarily suitable for an All Settings directory are U03, U08–U10 and U17. U07, U12–U14 primarily link to their existing owner. U06/U11 are informational. The per-family record, not this single-bucket count, governs any later design review.

## Guidance for a later All Settings directory

Keep the existing Settings panel as the short path for common choices. A secondary directory can be a plain, searchable list of names and behavioral descriptions, grouped by scope and owner. Each entry may show a small information control with: what changes, who may change it, where it persists, when a change takes effect, and where to manage it. Show an effective value only when the owning subsystem can safely report the value that actually won; otherwise say that it is unavailable. Never display a credential value or treat a health observation as a configured value.

Directory rows may link to Settings, the composer, Persona Studio, Connections, a document control, or an operator guide. Links preserve the owning mutation surface. Read-only entries must be visibly read-only. A catalog row must not create a new backend API, generic connector mutation route, provider selection owner, profile binding authority or runtime settings store. ADR-071/072 govern Connections and Settings route projections; ADR-074 governs provider posture, operator model selection, Compose transport and live inventory.

## Source and evidence notes

- Current release truth: docs/architecture/00-current-state.md. Governance: ADR-071, ADR-072, ADR-074 and, for narrow rows, ADR-026, ADR-064 and ADR-082. No ADR or current-state file is changed here.
- Configuration baseline: docs/architecture/config-authority-path-census.md (all 30 pathways); docs/architecture/config-classification-and-consolidation-plan.md (Stage 0 doctrine); docs/architecture/config-and-ops.md; docs/Codexify/CONFIGURATION.md. The requested docs/CONFIGURATION.md does not exist at this checkout.
- Backend declaration and consumer search: guardian/core/config.py; guardian/config/core.py; guardian/core/dependencies.py; guardian/guardian_api.py; guardian/core/supported_profile.py; guardian/config_loader.py; guardian/config/settings.py; guardian/config/system_config.py; direct os.getenv/os.environ users in Guardian, backend and specialized workers; targeted route, resolver and persistence reads named in each family.
- Product and client search: frontend/src/features/settings, frontend/src/lib/runtimeConfig.ts, frontend/src/lib/providerPref.ts, frontend/src/components/persona/layout/AppShell.tsx, frontend/src/features/chat, Persona Studio state, guardian/routes/chat.py, guardian/routes/imprint.py, guardian/services/iddb_settings_service.py, guardian/connections and relevant DB models.
- Evidence is static repository inspection of declarations and reachable code paths plus accepted contracts. It does not verify a live installed environment, secret value, mounted route in a particular deployment, provider health, effective model inventory, or supported release.
