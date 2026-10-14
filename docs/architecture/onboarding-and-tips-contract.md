# Account onboarding and Tips contract

Evidence posture: documented contract and focused code-path tests. This does not qualify a release or widen Beta/Private Preview claims. `00-current-state.md` remains release authority.

## Ownership and persistence

`user_onboarding_state` is account UX state, owned by `users.id` with cascading account deletion. Postgres is authoritative; the browser is a projection. This boundary is separate from `UserSettings`/IDDB identity-modeling policy, social Profile identity, direct messaging, runtime bootstrap, and workspace state. The authenticated account scope supplies ownership; API inputs cannot supply `user_id`. Missing/default accounts fail closed. GET returns V1 defaults without insertion; PATCH lazily upserts only specified fields, atomically preserving other fields under concurrent writes. Responses follow commit and fresh readback.

The V1 fields are `onboarding_version` (1), `status`, nullable `last_step_key`, device-tour completion flags, and `contextual_tips_enabled`. Database checks constrain status and V1 version. Account-purpose authentication uses the existing account dependencies; private-preview and remote account sessions retain their exact purpose gate. Generic local authentication behavior is unchanged.

`GET /api/onboarding` and `PATCH /api/onboarding` use dedicated `onboarding` route admission. This label is independent of `direct_messages`; only onboarding admission is added to the relevant application profiles. The payload rejects unknown fields, invalid status/version, invalid booleans, and step keys outside `welcome`, `identity`, `username`, `navigation`, `core_surfaces`, `help`.

## Status and device tours

`not_started` alone triggers the optional wizard after authenticated shell startup. Continue saves `in_progress` plus the semantic destination step. Skip/Close saves `skipped` at the current step, never completion. Explicit Resume uses a valid saved step, otherwise welcome. No skipped or interrupted state automatically reopens. Finish saves `completed` and the current device tour flag.

An explicit restart may run the introduction again. The optional current-device tour starts at navigation and preserves global onboarding status; its completion sets only the device flag. Closing a device tour or the messaging-only username card preserves global status. No navigation is commanded by the wizard.

## Identity and capability dependency

ADR-079/080 remain authoritative: account ownership → durable Profile_ID → optional mutable username → presentation. The wizard reuses `frontend/src/lib/direct-messages.ts` and the existing social-identity GET/PUT routes only when runtime route capability reports `direct_messages` available. It never enables that capability, changes addressing, derives username from email, or requires a username to finish. People remains separate from Guardian chat. Messaging copy is explicitly Private Preview and same-node.

Inspection found a pre-existing discrepancy: the direct-messaging contract describes `v1-whooshd-deepseek-web` admission, while the implementation baseline omits that label. This task preserves actual profile posture; omitted labels remain quarantined. Correcting messaging governance is deferred to a separate task.

Setup, username-unset state, and unread-message state are separate concepts. People has a nonnumeric optional setup action and contextual banner. Completed onboarding plus a server-returned unset username produces a distinct messaging prompt only when messaging is available. Successful claim refreshes the shared onboarding projection and removes that prompt.

## Tips and Settings

V1 Tips are static, versioned frontend content; no CMS or article persistence is introduced. Cards and Tips share one catalog. Desktop copy describes the current primary app surfaces and workspace/sidebar; phone copy uses AppShell's phone state and describes primary Guardian/Documents/Gallery, secondary Dashboard/Settings, and the mobile drawer. Capability-specific Tips are hidden when unavailable; explanatory cards label unavailable messaging.

Settings Help & Learning opens Tips, restarts onboarding or the current device tour, and persists contextual tips preference. Tips remains a passive reference, never a primary destination. The preference establishes future contextual-tip policy; this task does not retrofit tooltips across the app.

## Failure and trust boundaries

The browser and authenticated Guardian account API are separated by the existing account trust boundary. Caller-owned identifiers cannot cross it as authority. There are no peer writes or synchronization protocols in this feature. PostgreSQL upsert/commit gives transactional consistency; partial field updates avoid stale GET replacement. Repeated same-value PATCH is idempotent; failures are explicit rather than retried invisibly.

API load failure leaves AppShell usable and creates no fabricated completion. The client reuses authenticated fetch headers without the shared axios 401 logout/outage side effects. A bounded request timeout prevents an indefinitely pending optional enhancement. Save failures are shown without advancing the card; Close remains available and reports unsaved progress. Username errors use backend validation without changing onboarding authority.

No action writes Guardian memory, IDDB policy, Relationships, Conversations, Projects, Threads, or federation state. No realtime, cross-node discovery/delivery, Rooms, autonomous execution, import-to-recall, or release readiness is inferred.

## Baseline validation limitations

The implementation baseline also contains an orphan `=======` line in `config/supported_profiles/v1-whooshd-deepseek-web.yaml`, making that profile unparsable. Its existing profile tests fail before route evaluation; this task does not repair provider/profile history. A separate scoped repair is needed before that profile can be loaded. The local-core and friends/family onboarding label can be validated independently. The AppShell wallpaper assertion also fails with unchanged baseline AppShell (relative persisted URL versus expected absolute URL). Neither limitation is an onboarding release claim or permission to repair unrelated behavior.
