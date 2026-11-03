# Proof — Codexify OpenUI Foundation Pack v2

Date: 2026-10-17
Branch: `codex/openui-foundation-pack-v2`
Source branch/commit: `codex/openui-native-integration-slice` @ `97aabf2c83cbe242eafd849a7237dd9de9b55f29`
Governing contract: `docs/architecture/generative-ui-contract.md`
Release posture: **HOLD, unchanged.** Nothing here promotes Beta or Private Preview support.

---

## 1. Summary

One bounded outcome: a version-2 Codexify OpenUI foundation pack providing safe,
composable, read-only interfaces with Codexify-native appearance, with
version-1 rendering and persistence compatibility preserved.

Eight first-party components were added, a version-aware fail-closed admission
path was added, and the existing `openui.program` renderer was made
version-discriminating. The artifact envelope (`version: 1`), the component id
(`openui.program`), the `cfy-ui` marker codec, `SandboxFrame`, feature gates,
Guardian authority, and Postgres persistence are all unchanged.

## 2. Component inventory

All eight are registered in `codexifyOpenUiFoundationLibrary` and grouped as
Layout / Content / Data Presentation.

| # | Component | Group | Read-only | Child bearing |
| --- | --- | --- | --- | --- |
| 1 | `CodexifyStack` | Layout | yes | **root only**; leaf or Card |
| 2 | `CodexifyCard` | Layout | yes | leaf only |
| 3 | `CodexifyText` | Content | yes | none |
| 4 | `CodexifyHeading` | Content | yes | none |
| 5 | `CodexifyBadge` | Content/Data | yes | none |
| 6 | `CodexifyMetric` | Data Presentation | yes | none |
| 7 | `CodexifyProgress` | Data Presentation | yes | none |
| 8 | `CodexifyList` | Content | yes | none |

No ninth component, no form/input/button, no event handler, no styling prop.

## 3. Admitted grammar and schemas

```text
root  = CodexifyStack
Stack -> leaf | CodexifyCard
Card  -> leaf                (never Card, never Stack)
leaf  -> no children
depth <= 3                   (Stack, then Card, then a leaf)
```

Component schemas, in **declared order** (which is also positional order):

| Component | Positional props (required first, optional last) |
| --- | --- |
| `CodexifyStack` | `direction: "vertical"\|"horizontal"`, `children: ref[] (max 12)`, `wrap?: boolean` |
| `CodexifyCard` | `children: ref[] (max 8)`, `heading?: string ≤120` |
| `CodexifyText` | `text: string ≤400`, `size?: "sm"\|"md"\|"lg"`, `emphasis?: "normal"\|"strong"\|"muted"` |
| `CodexifyHeading` | `text: string ≤120`, `level?: "2"\|"3"\|"4"` |
| `CodexifyBadge` | `text: string ≤40`, `tone?: "neutral"\|"info"\|"success"\|"warning"\|"danger"` |
| `CodexifyMetric` | `label: string ≤100`, `value: string ≤40`, `detail?: string ≤180` |
| `CodexifyProgress` | `label: string ≤100`, `value: finite ≥0`, `max: finite >0`, `statusText?: string ≤80` |
| `CodexifyList` | `items: string ≤160 (max 12)`, `ordered?: boolean` |

Bounds: 4,096 characters, 16 statements, 12 rendered nodes, depth 3, 12 list
entries, plus per-field string bounds and the `0 ≤ value ≤ max` progress range.

### 3.1 Measured API constraint that shaped the design

`@openuidev/react-lang` 1.0.1 maps positional arguments onto declared schema keys
**in order, without skipping optional keys**. An optional prop declared ahead of
a required one swallows the next argument and makes that required prop
unreachable — `CodexifyStack(direction, wrap?, children)` fails to parse
`CodexifyStack("vertical", [...])` entirely, reporting
`/wrap expects boolean but got array` and `missing required /children`.

Every foundation schema therefore declares **all required props before any
optional prop**. `CodexifyCard([...], "heading")` reads heading-last as a
consequence. This is locked by a regression test
(`foundation pack: positional argument ordering`) that fails if the ordering is
undone.

## 4. Security model — why the parser is not the boundary

Measured directly against the installed 1.0.1 parser:

| Input | Parser result |
| --- | --- |
| `CodexifyCard` nested in `CodexifyCard` (schema union holds leaves only) | **`errors: []`** — fully accepted |
| Unknown child component | `unknown-component` error, child **dropped**, root still renderable |
| `@Run("do")` passed as an argument | **`errors: []`** — stored as `{k:"Comp",name:"Run"}` inside `props` |
| `$state` as an argument | **`errors: []`** — stored as `{k:"StateRef"}`, `hasDynamicProps: true` |
| Orphaned statement | `errors: []`, surfaced only via `meta.orphaned` |
| Unresolved reference | `errors: []`, surfaced only via `meta.unresolved` |

Because two of the most dangerous shapes parse silently, admission
(`openuiProgramAdmission.ts`) re-derives the resolved tree and rejects anything it
cannot positively classify as a bounded literal. It refuses on `meta.errors`,
`meta.incomplete`, `meta.unresolved`, `meta.orphaned`, statement count,
`queryStatements`, `mutationStatements`, `stateDeclarations`,
`rootExpression`, root type, and then walks the tree enforcing composition
position, depth, node count, known props, literal kinds, and numeric range.

### 4.1 Mutation evidence — which checks actually discriminate

Each check was disabled in isolation and the suite re-run. A check that stays
green was **not** proving anything and is reported as such.

| # | Disabled check | Result | Verdict |
| --- | --- | --- | --- |
| M1 | Composition position (Card allowed inside Card) | **RED** | **load-bearing and proven** |
| M2 | `hasDynamicProps` guard | green | redundant — prop-shape check also refuses |
| M3 | Enum vocabulary check | green | redundant — Zod/parser emits `type-mismatch` first |
| M4 | Rendered-node bound | green | redundant — Zod `.max()` on the children array fires first |
| M5 | Nesting-depth bound | green | masked by M1's position rule; unreachable once positions hold |
| M6 | `CodexifyProgress` cross-field range | **RED** | **load-bearing and proven** |

The honest conclusion: the structural walk earns its place for the two rules a
schema cannot express — **composition position** and **cross-field numeric
range**. The remaining checks are deliberate defense in depth against future
parser or library changes, and this document does not claim independent coverage
for them.

M1 initially produced a **false green**: the first card-in-card test used nested
cards *with children*, so the depth bound fired first and masked the missing
position check. The test was rewritten to use a childless nested container so
the depth rule could not mask the position rule. This false green is the reason
the mutation table exists.

## 5. Validation results

All commands run from the repository root of the isolated worktree.

| Command | Result |
| --- | --- |
| focused `vitest run` (4 authorized test files) | **131 passed / 131** |
| `pnpm --dir frontend test` (full) | 3-4 files / 4 tests failing across three samples — all pre-existing and non-generative-UI; see §5.2 |
| `pnpm --dir frontend typecheck` | **0 errors** |
| `pnpm --dir frontend build` | **succeeded in 2.79s** |
| `git diff --check` | clean |

The production build emits OpenUI as its own separate chunk
(`dist/assets/openuiNative-*.js`, ~181 kB) distinct from the main bundle, which
is build-level evidence that the lazy boundary still holds.

### 5.1 Baseline correction

The task brief stated a baseline of "5 files failed" for the full frontend test
and "119 errors" for typecheck. Measured on the actual source commit in a clean
worktree:

- Full frontend test baseline: **4 files / 5 tests failing**
  (`UnifiedDesktopCompositor` ×2, `GuardianMobileSidebarAppMenu`,
  `SettingsPanelShell`, `GuardianMobileFrameShell`) — all in persona layout and
  settings, none touching generative UI.
- Frontend typecheck baseline: **0 errors**, not 119.

The typecheck discrepancy matters: because the baseline is clean, **any** type
error in this change is attributable to this change. No new failures were
introduced, and no baseline failure is attributed to this task.

### 5.2 Pre-existing flakiness in the full suite

Three full-suite samples after this change produced **different** failing sets:

| Sample | Failing files |
| --- | --- |
| 1 | UnifiedDesktopCompositor, GuardianMobileSidebarAppMenu, SettingsPanelShell, `ChatView.loop-guards` |
| 2 | UnifiedDesktopCompositor, GuardianMobileSidebarAppMenu, SettingsPanelShell |
| 3 | UnifiedDesktopCompositor, GuardianMobileSidebarAppMenu, SettingsPanelShell |

The three stable files are all baseline failures in persona layout and settings.
`GuardianMobileFrameShell` (a baseline failure) appeared in the baseline run but
not in the post-change samples, and `ChatView.loop-guards` appeared once and then
vanished. That instability, together with a varying "Unhandled Errors" count
(28 / 34 / 59), indicates a pre-existing load-sensitive flake surface rather than
a regression: `ChatView.loop-guards` passes **12/12 in isolation on three
consecutive runs**, and the suite emits cross-file unhandled rejections.

**No generative-UI test failed in any sample**, and the four authorized test files
pass 131/131 on every run. This is reported as an observed limitation of the
suite, not as a clean bill of health for the pre-existing failures.

## 6. Acceptance criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | All eight v2 components register | ✅ | `codexifyOpenUiFoundationLibrary`; registry test unchanged at 3 ids |
| 2 | Composed read-only dashboard renders | ✅ | `renders a metric dashboard from a valid version-2 program` |
| 3 | Stack → Card → leaf composition | ✅ | `composes Stack -> Card -> leaf components` |
| 4 | v1 metric artifacts still render unchanged | ✅ | v1 test suite untouched and green; v1 validator byte-identical |
| 5 | v2 round-trips the existing cfy-ui codec | ✅ | `round-trips a version-2 program through the unmodified cfy-ui codec` |
| 6 | Invalid/oversized/executable/unknown programs fail closed | ✅ | `openuiProgramAdmission.test.ts` (23 tests) |
| 7 | Hostile text appears only as inert text | ✅ | `renders hostile markup as inert text and never as host DOM` |
| 8 | Each component inherits Codexify tokens | ✅ | `expresses colour and surface through tokens rather than literals` |
| 9 | No action/tool/mutation/network/credential authority | ✅ | no `toolProvider`, no `onAction`; admission refuses Query/Mutation/action args |
| 10 | OpenUI remains lazy-loaded | ✅ | `nativeRegistry` `React.lazy` boundary untouched |
| 11 | Existing generative-UI tests remain green | ✅ | 80/80 baseline tests still pass, unmodified in intent |
| 12 | Concrete proof document | ✅ | this file |

## 7. Proof fixtures

Deterministic fixtures cover: metric dashboard; status overview; mixed
text/card/list layout; multiple progress indicators; empty root; maximum node
and list boundaries; token inheritance; v1 compatibility; v2 codec round-trip;
unknown component rejection; orphaned references; cycles/computed roots;
oversized programs and arrays; Query/Mutation/Action rejection; variable and
expression rejection; markup-injection; feature-gate-disabled behaviour.

Rendering is exercised through the **registered native path**
(`ChatBubble` → `resolveNativeUiComponent("openui.program")` → lazy renderer),
not merely through Zod parsing.

## 8. Invariants

- Guardian remains authoritative for actions and permissions — untouched.
- Postgres remains canonical for message persistence — untouched.
- cfy-ui encoding and marker stripping unchanged — reused as-is.
- `SandboxFrame` unchanged.
- Feature gates retain behaviour; `VITE_GENERATIVE_UI` still default-off.
- No new provider, model, inference, or agent runtime.
- No Query/Mutation tools or `toolProvider`.
- Only registered first-party React components execute in the host.
- Invalid programs render no native artifact; transcript prose survives.
- Existing v1 artifacts continue to restore.

## 9. ADR impact

- **ADR-003** (message vs request identity): the artifact still rides canonical
  message content. No new identity is introduced.
- **ADR-077** (execution authority): unchanged; execution authority remains
  denied by default. No sandbox or permission change was required or made.
- **ADR-069** (Beta support boundary): unchanged. Release claims remain bounded.

**No new architectural decision was required.** Guardian authority, artifact
ownership, sandbox permissions, and canonical message semantics are untouched.

## 10. Unproven runtime surfaces

Honest limits of this evidence. jsdom tests do **not** prove:

- Real-browser rendering, layout, or paint behaviour.
- Actual CSS custom-property resolution — jsdom does not resolve `var()`
  substitution, so token inheritance is proven as *"the component references the
  token and hard-codes no colour"*, not as *"the computed colour changed with
  the theme"*. Real light/dark switching is **not** proven here.
- Responsive/mobile overflow behaviour in a real viewport.
- Screen-reader announcement of the progress bar.
- Live model generation of a valid version-2 program.
- Postgres persistence and restore-after-reload of a v2 artifact.
- Streaming (`isStreaming`) behaviour for v2; the renderer is used with
  `isStreaming={false}`.

## 11. Reported token dependency gap

Four contract tokens have **no declaration anywhere in the current tree**:
`--card-pad`, `--card-radius`, `--radius-micro`, `--shell-gap`.

(Confirmed: `--card-pad` is only set to `0px` inside the feature-scoped
`features/onboarding/onboarding.css`; `--tile-radius` is declared in
`tokens.css`; the rest are absent.) They are consumed with
`var(--token, <fallback>)` following the existing generative-UI pattern, and
exported as `OPENUI_UNDECLARED_TOKEN_DEPENDENCIES` with a test asserting the
list. Per the task's non-goals this pack creates **no new runtime theme
tokens**; declaring these belongs to a separate token-layer decision.

## 12. Deferred component categories

Explicitly **not** built here: forms and user input; buttons or action handlers;
data fetching; theme-pack selection; component-pack marketplace or installer;
charts; tables; media; code blocks. Interactive capability would require a
separately approved architecture-impact change plus explicit Guardian policy.

## 13. Housekeeping note

A throwaway parser probe, `frontend/src/features/chat/components/generativeUi/scratch.test.ts`,
was created during implementation. The sandbox denied both deletion and rename,
and the vitest include glob collects any `*.test.ts`, so it was reduced to a
single inert placeholder test. It is **untracked and never staged** (the commit
uses an explicit path list, never `git add .`). It should be deleted manually.