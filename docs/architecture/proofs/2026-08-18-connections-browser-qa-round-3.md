# Connections Browser QA Round 3

## Result

`PASS WITH FINDINGS`

The merged read-only Connections control plane rendered in the existing
Settings → Connectors bay under the supported local Web profile. Category
navigation, populated search, detail state, unsupported-provider truth,
adapter/setup/registry separation, legacy connector quarantine, responsive
behavior, theme behavior, and API/UI semantics were exercised. One localized
P3 visual defect was found: disabled Configure controls lose their label
contrast in light theme. No P0, P1, or P2 finding was observed.

## Environment

- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/validate-connections-live-ui-round-2-fresh`
- Tested HEAD: `6386231aa5b09566b7b7800391d4e1a2ed445f94`
- `origin/main` at test start: `f0ed9b938c4094aa29b8fac911ec4b16975d899d`
- Supported profile: `v1-local-core-web-mcp`
- Browser URL: `http://localhost:5173/`
- Backend URL: `http://localhost:8888`
- Browser: Codex In-app Browser (`iab`)
- Viewports: default desktop `1280×720`; narrower `768×900`
- Themes: system baseline/resolved light, explicit light, dark, then system
  restored
- Runtime: temporary local backend and frontend containers from this checkout;
  process-level QA environment overrides only; no product/runtime source or
  configuration files were edited

The application shell loaded before Connections-specific testing. The tested
surface was the existing Settings `Connectors` tab. No separate Connections
page was created or expected. The local `.env` emitted shell-source warnings
during one runtime setup attempt; the final containers used explicit
process-level values and the repository files remained unchanged.

## Prerequisite proof

- `git merge-base --is-ancestor 6386231aa5b09566b7b7800391d4e1a2ed445f94 HEAD`:
  exit `0`.
- `git merge-base --is-ancestor 7c270b943fa3d1e9d0e28e1c029723fcd7e7ff46 HEAD`:
  exit `0`.
- Required source identity was present at the tested HEAD:
  `guardian/connections/catalog.py`, `guardian/routes/connections.py`,
  `docs/architecture/connections-control-plane.md`, and
  `docs/architecture/adr/071-connections-control-plane-boundary.md`.
- Supported-profile health reported `v1-local-core-web-mcp` valid with no
  mismatches, `connections: enabled`, and `connectors: quarantined`.
- Authenticated live route probes returned:
  `GET /api/connections` = `200`,
  `GET /api/connections/deepseek` = `200`,
  `GET /api/connections/slack` = `200`,
  unknown connection = `404`, and
  `GET /api/connectors` = `404`.
- The catalog response contained `categories` and `items` with 57 items.
- OpenAPI exposed `/api/connections` and
  `/api/connections/{connection_id}`; it did not expose `/api/connectors`.

## Lineage reconciliation

Round 1 used stale HEAD `5df15d6...` and stopped before browser testing. The
obsolete pre-rebase implementation SHA `634ddeb...` is historical provenance
only and is not the current mainline proof anchor. PR #713 merged Connections
at `7c270b943fa3d1e9d0e28e1c029723fcd7e7ff46` with subject
`feat(connections): establish Connections control plane`. The current
governing decision is ADR-071, `Connections Control Plane Boundary`, not
ADR-068.

Round 3 tested a descendant of the canonical merged commit. The tested branch
was the existing non-conflicting proof branch created from current
`origin/main`; no stale Round 1 branch was reset, force-moved, or rewritten.
The Round 1 artifact was not modified.

## Executive summary

- PASS: the supported profile exposed the read-only Connections catalog while
  keeping the legacy sync connector route quarantined.
- PASS: 57 catalog items rendered in one existing Settings Connectors bay,
  split into 23 Messaging, 8 Web, and 26 Inference items.
- PASS: search, category filtering, detail state, scrolling, reload, and
  navigation behaved coherently without stale detail or duplicated bay state.
- PASS: catalog metadata kept adapter implementation, setup availability,
  registry authorization, and connection health distinguishable.
- PASS: unsupported messaging, web, and OAuth-oriented entries were visible
  as unavailable/discovery-only and did not launch fake setup flows.
- BUG P3: disabled Configure labels are visually unreadable in light theme
  because the disabled text and background resolve to the same gray.

Counts for the classified observations below: `PASS 15`, `BUG 1` (`P3 1`),
`CONFUSING 0`, and `EXPECTED-UNAVAILABLE 4`.

## Coverage

Exercised surfaces:

- Existing Settings → Connectors bay and the Connections catalog projection.
- Categories: All, Messaging, Web, and Inference; selected category styling;
  populated list counts; list scrolling; and detail selection.
- Search: exact `Slack`, partial `fire`, mixed-case `TaViLy`, no-result query,
  keyboard clearing, search while switching categories, and rapid sequential
  typing for `deepseek`.
- Messaging: Slack, Discord, Telegram, Signal, WhatsApp, and Matrix.
- Web: Firecrawl, Tavily, Exa, Parallel, SearXNG, Brave Search,
  DDGS / DuckDuckGo, and xAI / Grok.
- Inference: DeepSeek, MiniMax OAuth, MiniMax API, OpenAI Codex / ChatGPT,
  OpenAI API, Google Gemini OAuth, Groq, Qwen OAuth, and GitHub Copilot.
- Adapter / Setup / Registry separation on implemented, partial,
  unimplemented, registry-authorized, registry-unauthorized, and registry-not-
  listed samples.
- Setup/detail behavior for API-key, OAuth-oriented, unavailable, and local
  endpoint entries; no credentials were entered and no secret values were
  recorded.
- Reload, leave-and-return navigation, rapid category switching, repeated
  detail opening, and state reset after navigation.
- Console inspection, authenticated API/OpenAPI probes, and frontend proxy
  request inspection.
- Responsive desktop and `768×900` layout checks; light and dark theme checks;
  keyboard focus/input smoke.

## Findings

| ID | Classification | Severity | Surface | Finding | Reproduction | Evidence | Likely owner |
|---|---|---|---|---|---|---|---|
| R3-001 | PASS | — | Supported profile / route posture | The read-only Connections route is enabled independently of the legacy connector route. | Start the supported local profile and inspect health, OpenAPI, and authenticated endpoint responses. | Profile reported `connections: enabled`, `connectors: quarantined`; `/api/connections` and its detail routes returned `200`; `/api/connectors` returned `404`; OpenAPI contained only the Connections paths. | Connections API |
| R3-002 | PASS | — | Settings surface | The application loads into the existing Settings Connectors bay and renders the catalog without creating a separate page. | Open `http://localhost:5173/`, select Settings → Connectors, and wait for the catalog. | `connections-bay` rendered with the catalog explanation, category controls, search, rows, and the truthful sync-connector unavailable message. | frontend projection |
| R3-003 | PASS | — | Category navigation | All, Messaging, Web, and Inference switch the visible list and selected styling; changing category clears selected detail. | Select each category, select Slack, then switch to Web and Inference. | Counts were All `57`, Messaging `23`, Web `8`, Inference `26`; active category used the selected accent style; Slack detail disappeared on category switch. | frontend projection |
| R3-004 | PASS | — | Search and filtering | Exact, partial, mixed-case, no-result, clear, category-filtered, and rapid-typing searches produced the expected rows without category leakage. | Search `Slack`, `fire`, `TaViLy`, and `zzzz-no-connection`; clear with keyboard; search `slack` while switching Web/Messaging; type `deepseek` sequentially. | Results were respectively Slack, Firecrawl, Tavily, no rows, restored list, no Web rows, Slack in Messaging, and no Messaging rows for DeepSeek. | frontend projection |
| R3-005 | PASS | — | List scrolling / detail state | The populated list scrolls, representative detail panels are correct, and repeated selection does not duplicate or retain the prior provider. | Scroll the catalog by 800px, select representative rows repeatedly, and switch providers. | Scroll container reported `scrollHeight 2731` against `clientHeight 485`; visible rows changed; each sampled detail panel matched its selected provider; one `connection-detail` panel remained. | frontend projection |
| R3-006 | PASS | — | Messaging truth | Slack, Discord, and Telegram show partial adapter existence while keeping setup unavailable; Signal, WhatsApp, and Matrix clearly show no adapter and discovery-only behavior. | Open each requested Messaging detail panel and inspect Adapter, Setup, Authentication, and explanatory text. | Slack/Discord/Telegram showed `Adapter Partial`, `Setup Not available`, token auth, and no production runtime path; Signal/WhatsApp/Matrix showed `Adapter Not implemented`, `Setup Not available`, and no fake setup path. | channels subsystem |
| R3-007 | PASS | — | Web truth | Web catalog capabilities and authentication labels match the intended Search + Extract or Search-only split without implying live Codexify search execution. | Open Firecrawl, Tavily, Exa, Parallel, SearXNG, Brave Search, DDGS / DuckDuckGo, and xAI / Grok. | Firecrawl/Tavily/Exa/Parallel showed `Capabilities: extract, search`; SearXNG/Brave/DDGS/xAI-Grok showed `Capabilities: search`; each said catalog discovery only and had Configure disabled. | Connections API |
| R3-008 | PASS | — | Inference truth | DeepSeek is labeled API key, not OAuth; OAuth-oriented entries identify browser OAuth and unavailable handlers; implemented API lanes remain setup/registry-state distinct. | Inspect DeepSeek, MiniMax OAuth/API, OpenAI Codex/API, Gemini OAuth, Groq, Qwen OAuth, and GitHub Copilot. | DeepSeek showed `Authentication: API key`; MiniMax OAuth/OpenAI Codex/Gemini OAuth/Qwen OAuth/GitHub Copilot showed `OAuth (browser)` and no backend authorization handler; API lanes showed API-key metadata. | provider registry |
| R3-009 | PASS | — | Adapter / Setup / Registry | The catalog does not collapse adapter existence, setup, registry authorization, and health into one connected state. | Compare Slack, DeepSeek, MiniMax OAuth, OpenAI Codex, and API providers. | Slack was `Partial`/`Not available`; DeepSeek was `Implemented`/`Needs setup`/`Registry not authorized`; MiniMax OAuth was `Not implemented`/`Not available`/`Registry not authorized`; OpenAI Codex was `Not implemented`/`Not available`/`Registry not listed`. No row claimed connected or healthy. | frontend projection |
| R3-010 | PASS | — | Setup UX / unavailable actions | Representative setup states expose only relevant metadata; unavailable or server-owned setup actions do not open a stale form or accept credentials. | Inspect DeepSeek (API key), MiniMax OAuth (OAuth), Signal (unavailable), SearXNG (local endpoint), and Slack; inspect Configure controls. | All sampled Configure controls were disabled with `aria-disabled=true`; no dialog or input opened; API response metadata marked DeepSeek's required field as secret/password without returning a value. | frontend projection |
| R3-011 | PASS | — | Legacy sync connectors | Legacy GitHub/sync connector execution remains quarantined while the Connections catalog is available. | Open Settings → Connectors and inspect the sync subsection; issue the explicit authenticated legacy route probe. | UI said `Sync connectors are unavailable in this runtime profile`; `/api/connectors` returned `404`; no legacy GitHub mutation or sync control was exposed. | legacy connector surface |
| R3-012 | PASS | — | Reload / navigation resilience | Reload, leaving Settings, returning, rapid category switching, and repeated detail opening do not crash, blank the bay, duplicate it, or retain stale detail. | Select Web/Firecrawl, leave to Appearance, return to Connectors, rapidly switch categories, and reload. | Return and reload each produced one bay, 57 rows, no detail duplication, and the All category active; no blank panel or crash appeared. | frontend projection |
| R3-013 | PASS | — | API/UI semantics | API and visible UI agree on category, implementation, setup, auth, capabilities, and registry semantics for the requested sample set. | Compare live catalog/detail metadata with Slack, Telegram, Firecrawl, SearXNG, DeepSeek, MiniMax OAuth, and OpenAI Codex. | The API/UI comparison table below records matching values; display wording differences were presentation-only. | Connections API |
| R3-014 | PASS | — | Console / network / response hygiene | The corrected final browser run has no Connections console errors, missing assets, uncaught exceptions, or retry storm; ordinary catalog responses contain no credential values. | Load a clean browser tab, navigate the bay, select details, and inspect console plus backend/frontend request evidence. | Clean post-runtime tab reported no console logs; frontend proxy logs had no errors after correction; response scan found no secret-like credential values and no nonempty credential-value fields. | unknown |
| R3-015 | PASS | — | Responsive / theme / keyboard smoke | Desktop and narrower layout states remain usable, theme states render, and keyboard input/focus smoke does not crash the surface. | Exercise `1280×720`, `768×900`, light, dark, restore system, search keyboard clearing, focus, and Escape. | Narrow layout had no measured horizontal overflow; category/search/detail stayed within bounds; light/dark states rendered; search accepted keyboard input and native controls remained focusable. | frontend projection |
| R3-016 | BUG | P3 | Light theme / disabled setup controls | Disabled Configure controls lose visual label contrast in light theme. | Set Appearance → Light, return to Connectors, and inspect any unavailable Configure button. | For the DeepSeek disabled button, computed foreground and background were both `rgb(107, 114, 128)` with `opacity: 0.5`; the screenshot showed a gray pill without a legible Configure label. Dark theme rendered the label legibly. | frontend projection |
| R3-017 | EXPECTED-UNAVAILABLE | — | Unsupported messaging | Signal, WhatsApp, and Matrix correctly remain discovery-only and cannot launch setup. | Open each detail panel and inspect Configure state. | Each showed `Adapter Not implemented`, `Setup Not available`, explanatory no-adapter text, and disabled Configure. | channels subsystem |
| R3-018 | EXPECTED-UNAVAILABLE | — | Catalog-only web providers | Firecrawl, Tavily, Exa, Parallel, SearXNG, Brave Search, DDGS / DuckDuckGo, and xAI / Grok correctly remain catalog-only. | Open each web detail panel and inspect capabilities, setup, and Configure state. | Search capability labels matched the expected split; each said no Codexify web adapter exists and selecting it does not change current search behavior; Configure was disabled. | Connections API |
| R3-019 | EXPECTED-UNAVAILABLE | — | OAuth-oriented inference | MiniMax OAuth, OpenAI Codex, Google Gemini OAuth, Qwen OAuth, and GitHub Copilot safely avoid dead OAuth flows. | Open each OAuth-oriented detail panel and inspect auth text and Configure state. | Each showed `OAuth (browser)`, no backend authorization handler, catalog/discovery-only wording, and disabled Configure; no OAuth request was sent. | provider registry |
| R3-020 | EXPECTED-UNAVAILABLE | — | API-key / local setup | Server-owned API-key setup and the local SearXNG endpoint remain unavailable in this read-only control plane. | Inspect DeepSeek, OpenAI API, MiniMax API, Groq, and SearXNG. | API-key entries showed `Needs setup` plus registry state, but no credential form or mutation route; SearXNG showed `Local endpoint` and `Setup Not available`. | provider registry |

## Sampled expected-unavailable integrations

The following unavailable behavior worked correctly and is not a product defect:

| Integration(s) | Expected behavior observed |
|---|---|
| Signal, WhatsApp, Matrix | Visible for discovery, `Not implemented`, `Not available`, no fake setup path. |
| Firecrawl, Tavily, Exa, Parallel, SearXNG, Brave Search, DDGS / DuckDuckGo, xAI / Grok | Capabilities are descriptive catalog metadata; no live search/extract adapter or setup action is implied. |
| MiniMax OAuth, OpenAI Codex, Google Gemini OAuth, Qwen OAuth, GitHub Copilot | Browser-OAuth intent is labeled, but missing backend handler is explicit and Configure is disabled. |
| DeepSeek, OpenAI API, MiniMax API, Groq, SearXNG | Server-owned API-key/local setup remains unavailable; registry or endpoint metadata does not imply a live connection. |

## API/UI consistency summary

The live API response and the UI projection were semantically consistent for
the requested samples. The API response used canonical fields while the UI
used human-readable labels.

| Integration | API meaning | UI meaning | Result |
|---|---|---|---|
| Slack | `messaging`; `partial`; setup `unavailable`; token auth; channel adapter binding | Messaging; Adapter Partial; Setup Not available; Authentication: Token; runtime adapter text | PASS |
| Telegram | `messaging`; `partial`; setup `unavailable`; token auth; channel adapter binding | Messaging; Adapter Partial; Setup Not available; Authentication: Token; runtime adapter text | PASS |
| Firecrawl | `web`; `unimplemented`; setup `unavailable`; API key; `extract, search`; no adapter binding | Web; Adapter Not implemented; Setup Not available; API key; extract/search; catalog-only text | PASS |
| SearXNG | `web`; `unimplemented`; setup `unavailable`; local endpoint; `search`; no adapter binding | Web; Adapter Not implemented; Setup Not available; Local endpoint; search; catalog-only text | PASS |
| DeepSeek | `inference`; `implemented`; setup `needs_setup`; API key; registry registered but unauthorized because credentials are missing | Inference; Adapter Implemented; Setup Needs setup; Authentication: API key; Registry not authorized | PASS |
| MiniMax OAuth | `inference`; `unimplemented`; setup `unavailable`; `oauth_browser`; handler absent; registry entry unauthorized | Inference; Adapter Not implemented; Setup Not available; OAuth (browser); Registry not authorized; no handler text | PASS |
| OpenAI Codex | `inference`; `unimplemented`; setup `unavailable`; `oauth_browser`; handler absent; not registered | Inference; Adapter Not implemented; Setup Not available; OAuth (browser); Registry not listed; no handler text | PASS |

The ordinary catalog payload contained no secret-bearing credential values.
Required-field metadata identified secret/password treatment for DeepSeek, but
no API key or token value was returned.

## Console summary

The clean post-runtime browser tab reported no console `error` or `warn` entries
while loading and exercising Settings → Connectors. No React error, uncaught
exception, rejected promise, missing Connections asset, or Connections API
error was observed in the corrected run. The application shell still showed
the pre-existing `Provider degraded / failure: chat_unhealthy` status banner;
it was unrelated to the Connections catalog and was not classified as a
Connections defect.

The first temporary frontend container was discarded before the final pass
because its proxy still targeted the unavailable Compose hostname `backend`.
Its 500 transport errors, including failed optional requests, are harness
preflight evidence only and are not counted as Round 3 product findings.

## Network summary

- `GET /api/connections`: authenticated `200`; the browser rendered all 57
  catalog items through the same-origin frontend proxy.
- `GET /api/connections/{id}`: authenticated direct probes for Slack and
  DeepSeek returned `200`; an unknown ID returned `404`. Detail selection in
  the UI uses the already-loaded catalog object and did not require a separate
  detail request for each click.
- `GET /api/connectors` requested?: **No in the corrected final browser run**;
  the legacy subsection rendered the unavailable-profile message. The explicit
  authenticated backend quarantine probe did request it and returned `404`.
- OpenAPI exposed only `/api/connections` and
  `/api/connections/{connection_id}` for these two route families; the legacy
  connector path was absent.
- Unavailable OAuth Configure controls were disabled, so no nonexistent OAuth
  handler was requested.
- No request loop or retry storm was observed after the frontend proxy was
  corrected; the final frontend proxy log contained no API error.
- No secret-bearing request headers or credential values were recorded.

## Responsive/theme summary

At the default `1280×720` viewport, the Connections bay, category controls,
search, list, detail panel, and sync-connector message rendered in the
existing Settings layout. At `768×900`, the category controls and search
remained in bounds; the bay reported no horizontal overflow, and the list and
detail panel remained vertically scrollable. Long labels remained within the
measured content bounds. The light and dark themes both rendered the selected
category, status text, borders, and detail panel; disabled-action label
contrast in light theme is the P3 finding R3-016. System theme was restored
after the pass.

Keyboard smoke covered focus, search typing, keyboard clearing, Escape, and
native button/input presence. Search input accepted sequential keyboard input;
the in-app browser's synthetic Tab/Enter activation could not be separated
reliably from browser-driver event behavior, so no product keyboard defect is
asserted from that limitation.

## OAuth-readiness assessment

1. **MiniMax OAuth auth type:** `OAuth (browser)` / `oauth_browser`, with
   chat capability and no API-key field.
2. **Safely unavailable?** Yes. The catalog reports the entry as unimplemented,
   setup unavailable, and lacking a backend authorization handler; Configure is
   disabled and no dead flow launches.
3. **Obvious future OAuth place?** Yes. The existing Connections detail panel
   already presents auth, setup, registry, and handler state, and the
   catalog's OAuth metadata provides a natural future authorization action in
   that same detail surface.
4. **Redesign likely?** No for the next implementation slice. A future
   MiniMax OAuth handler can attach to the existing detail/setup boundary; it
   will need backend authorization, callback/state handling, and explicit
   persistence/registry semantics, but this QA found no need for a new Settings
   page or a catalog redesign.

## Recommendation

`proceed-to-minimax-oauth`

The catalog/control-plane semantics are trustworthy enough to proceed to a
bounded MiniMax OAuth implementation slice. Keep the light-theme disabled
Configure contrast defect as deferred frontend polish and preserve the current
no-handler, no-mutation behavior until OAuth backend proof exists.

## Release-truth boundary

This proof establishes live availability of the read-only Connections catalog
and per-connection projection in the supported local Web profile. Catalog
visibility does not promote provider execution, runtime authorization,
connection health, credential persistence, messaging setup, web-provider
execution, generic sync connector support, or any OAuth flow. The legacy
`connectors` route remains quarantined, the connector worker behavior was not
changed, and no provider-registry or cloud-provider governance was widened.
