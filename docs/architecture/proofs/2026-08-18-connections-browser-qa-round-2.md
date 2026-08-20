# Connections Browser QA Round 2

## Result

`BLOCKED`

The fresh merged-mainline checkout reached the existing Settings → Connectors
bay, but the live Connections read API was not mounted on the tested supported
profile. The catalog shell rendered with no entries, while authenticated
`GET /api/connections` and detail requests returned `404 Not Found`. Provider,
category, detail, setup, and semantic-comparison passes therefore could not be
run without changing runtime/product configuration or using another checkout.

## Environment

- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/validate-connections-live-ui-round-2-fresh`
- Tested HEAD: `f0ed9b938c4094aa29b8fac911ec4b16975d899d`
- `origin/main` at test start: `f0ed9b938c4094aa29b8fac911ec4b16975d899d`
- Canonical lineage: `PASS`; `git merge-base --is-ancestor 7c270b943fa3d1e9d0e28e1c029723fcd7e7ff46 HEAD` exited `0`
- Required source identity: `PASS`; `guardian/connections/catalog.py`, `guardian/routes/connections.py`, `docs/architecture/connections-control-plane.md`, and `docs/architecture/adr/071-connections-control-plane-boundary.md` were present at the tested HEAD
- Browser URL: `http://127.0.0.1:5173/`
- Backend URL: `http://127.0.0.1:8888`
- Browser: Codex in-app Browser (`iab`)
- Viewports: default `1055×994`; narrower responsive pass `800×900`
- Themes: dark baseline/restored; light inspected and restored to dark
- Runtime: backend and frontend were started from this checkout with transient process-level QA overrides for the local supported profile and local authentication. No product configuration file was edited.

The application shell loaded before Connections-specific testing. The browser
showed the existing Settings tab list and the `Connectors` tab; no separate
Connections page was created or expected.

## Lineage reconciliation

Round 1 used stale HEAD `5df15d6...` and stopped before browser testing. The
obsolete pre-rebase implementation SHA `634ddeb...` is historical provenance
only and is not the current mainline proof anchor. PR #713 merged Connections at
`7c270b943fa3d1e9d0e28e1c029723fcd7e7ff46` with subject
`feat(connections): establish Connections control plane`. The current governing
decision is ADR-071, `Connections Control Plane Boundary`, not ADR-068.

Round 2 was created from the current `origin/main` and tested a descendant of
the canonical merged commit. The requested branch name already existed
locally, so the non-conflicting proof-only suffix `-fresh` was used; the
existing branch was not deleted, reset, or force-moved. The Round 1 artifact was
not present in this fresh checkout and was not modified.

## Coverage

Observed and exercised:

- `PASS` — fresh checkout, canonical lineage gate, required source-file gate,
  runtime startup, application load, Settings → Connectors navigation, and
  existing Connectors bay identity.
- `PASS` — Connections search control accepted exact (`slack`), partial,
  mixed-case (`SLaCk`), no-result, and clear interactions. Every query had no
  rows because the catalog response was unavailable; this does not prove
  filtering correctness against a populated catalog.
- `PASS` — navigation from Appearance to Connectors, reload, repeated tab
  return, and retained non-crashing empty bay state.
- `PASS` — light and dark theme controls were exercised; selected theme state
  was visible and dark was restored.
- `PASS` — default and narrower `800×900` viewport checks showed no document
  horizontal overflow or clipping in the rendered empty state.
- `BUG` — the live Connections catalog route was unavailable, so category
  controls, provider rows, selected-item detail, setup flows, adapter/setup/
  registry distinctions, and provider-specific truth could not be exercised.

Not reached because the catalog did not provide rows or categories:

- Messaging category and Slack, Discord, Telegram, Signal, WhatsApp, Matrix.
- Web category and Firecrawl, Tavily, Exa, Parallel, SearXNG, Brave Search,
  DDGS / DuckDuckGo, xAI / Grok.
- Inference category and DeepSeek, MiniMax OAuth, MiniMax API, OpenAI Codex,
  OpenAI API, Gemini OAuth, Groq, and Qwen OAuth.
- Detail selection, API-key setup, OAuth-oriented setup, unavailable-provider
  setup, local-endpoint setup, secret-input treatment, and stale-form reset.
- Category switching, scrolling through populated lists, and rapid switching
  between Messaging, Web, and Inference; only the `All` control was present.
- Legacy GitHub controls: the existing `Sync connectors` section remained
  visible and reported `No sync connectors configured`, but no GitHub control
  was reachable and no destructive sync/config action was attempted.

## Findings

| ID | Classification | Severity | Surface | Finding | Reproduction | Evidence | Likely owner |
|---|---|---|---|---|---|---|---|
| R2-001 | BUG | P1 | Supported-profile route posture / Settings → Connectors | The merged Connections control plane is not reachable on fresh current `origin/main`; the UI presents an empty catalog shell instead of a usable catalog or an explicit route-unavailable state. | Start the backend and frontend from the fresh branch using the local supported profile, open Settings → Connectors, then request the catalog and representative detail routes. | Browser showed `Connections`, `All`, `Search connections`, and `No connections match`, with no Messaging/Web/Inference controls or rows. Authenticated `GET /api/connections`, `/api/connections/slack`, `/api/connections/telegram`, `/api/connections/firecrawl`, `/api/connections/searxng`, `/api/connections/deepseek`, `/api/connections/minimax-oauth`, and `/api/connections/openai-codex` each returned `404`; OpenAPI exposed no `connections` or `connectors` paths. `GET /health` was `200` with supported profile `v1-local-core-web-mcp`, `valid: true`, and no mismatches. | Connections API |

The finding is a live route/readiness failure, not a reinterpretation of the
Round 1 stale-checkout block. The checked-out source and canonical merge are
present; the tested runtime simply does not expose the read route under the
active supported profile.

## Expected-unavailable sample

No provider-level `EXPECTED-UNAVAILABLE` sample was reached. The catalog was
unavailable before unsupported integrations could be selected, so no fake
OAuth flow or unavailable-provider setup action was launched. The legacy
`/api/connectors` route also returned `404` under this profile, but that is part
of the route/readiness finding rather than a successful provider-unavailable
behavior sample.

## Console / Network summary

Console inspection found no React error, uncaught exception, rejected promise,
Connections-specific error, missing Connections asset, or repeated Connections
request error. The browser emitted one unrelated warning that `/codex/entries`
was not found and returned an empty list, plus normal Vite/React development
messages. The existing `Provider degraded / failure: chat_unhealthy` banner was
not treated as a Connections defect.

The available browser diagnostics exposed console logs but not a network-panel
API. Network evidence was therefore captured from the same local frontend and
backend URLs with authenticated request inspection; the API key and all
headers were omitted from this artifact.

- `GET /health`: `200`; supported profile `v1-local-core-web-mcp`, valid, with
  no reported mismatches.
- `GET /api/connections`: `404`, body shape only `{"detail":"Not Found"}`.
- `GET /api/connections/{id}` for representative requested IDs: `404`.
- `GET /api/connectors`: `404`.
- OpenAPI contained no `connections` or `connectors` paths.
- No token, API key, secret, or credential material appeared in the observed
  ordinary response bodies.
- No request loop or retry storm was observed.

## API/UI consistency

Live semantic comparison was blocked for all requested samples. The following
entries could not be compared because neither the list route nor detail route
returned a catalog object:

| Integration | Category / state / auth / capability comparison |
|---|---|
| Slack | Not sampleable; `/api/connections/slack` returned `404`; no UI row |
| Telegram | Not sampleable; `/api/connections/telegram` returned `404`; no UI row |
| Firecrawl | Not sampleable; `/api/connections/firecrawl` returned `404`; no UI row |
| SearXNG | Not sampleable; `/api/connections/searxng` returned `404`; no UI row |
| DeepSeek | Not sampleable; `/api/connections/deepseek` returned `404`; API-key labeling not live-verifiable |
| MiniMax OAuth | Not sampleable; `/api/connections/minimax-oauth` returned `404`; OAuth dead-flow prevention not live-verifiable |
| OpenAI Codex | Not sampleable; `/api/connections/openai-codex` returned `404`; auth/registry semantics not live-verifiable |

The empty UI is consistent with receiving no catalog rows, but it is not a
semantically sufficient projection of the route-unavailable condition. No
claim is made here about the provider metadata that the source catalog would
return once the route is exposed.

## Recommendation

`repair-connections-first`

Restore an explicitly supported, live `GET /api/connections` projection path
for the existing Settings Connectors bay, while preserving the separate legacy
connector authority and the adapter/setup/registry distinctions. Then rerun
the full provider, setup, API/UI, console/network, responsive, and theme matrix
from a fresh descendant of the repaired mainline. No product or runtime fix was
made in this proof task.
