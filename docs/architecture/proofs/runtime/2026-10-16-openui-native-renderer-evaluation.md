# OpenUI native-renderer evaluation (isolated frontend proof)

Date: 2026-10-16
Branch: codex/openui-native-evaluation
Base ref: origin/main @ 42e86cb6a76954effa86ab83fc7634e8c9a14a61
Evidence: proven-test for local React/parser/codec seam; not live provider, browser, persistence readback, or release proof.

## Decision

**Candidate: advance to a separate architecture-impact integration design task, not direct production adoption.** OpenUI Lang's React parser and renderer can render a read-only Codexify-owned component styled through existing shell tokens. Existing cfy-ui encoding and schema already carry a native artifact whose props include an OpenUI program, with no new persistence channel. The OpenUI program cannot render in production yet because its component ID is intentionally absent from the native registry.

## What was exercised

- React 19.2.0 and @openuidev/react-lang 1.0.1 are compatible for a small local component.
- A constrained Zod-backed library exposes one read-only CodexifyMetric component.
- Renderer output inherits --panel-border, --card-radius / --tile-radius, --card-pad, --panel-bg, --text, and --muted from the containing shell. No theme provider overrides the shell.
- createParser parses a stored OpenUI Lang program with no parse errors; React renders the expected metric.
- The program round-trips as props within a version:1 kind:native cfy-ui artifact; unknown native component remains rejected by the existing registry.
- The candidate Renderer receives neither toolProvider nor onAction; no direct host action, agent runtime, external data query, mutation, or network permission was enabled.
- OpenUI's lang-core postinstall was suppressed with --ignore-scripts; OPENUI_TELEMETRY_DISABLED and DO_NOT_TRACK were set during installation. Verify telemetry posture before any shipped runtime use.

## Validation

- PASS: `../node_modules/.bin/vitest run --config vitest.config.ts features/chat/components/generativeUi/openuiCandidate.test.tsx features/chat/components/__tests__/GenerativeUI.test.tsx` from frontend/src. 71 tests passed (3 new, 68 existing). Existing ChatBubble tests emitted React act() warnings.
- NOT PASS / baseline caveat: frontend-wide TypeScript check initially lacked installed @types/node and React type definitions in the isolated worktree. After those types were installed, it reported 119 TypeScript errors across pre-existing frontend code, with no diagnostic naming the candidate files. A clean end-to-end typecheck on this branch is not established by this evaluation.
- NOT RUN: real browser responsive/wallpaper/theme proof; malicious-program and parser-bomb stress harness; provider-generated OpenUI programs; stream transport integration; Postgres persisted-reload on live Guardian; dependency security audit.

## Required integration design gate

1. Keep `<!-- cfy-ui:... -->` as the canonical message-bound persistence envelope and preserve current strip-before-inference behavior. Do not introduce an OpenUI checkpoint, model endpoint, provider route, AG-UI runtime, or second assistant identity.
2. Preserve the existing native/sandbox split. OpenUI may render *only* Codexify-registered components; arbitrary JavaScript/HTML remains confined to the existing sandbox, not parsed into trusted React elements.
3. Bound the OpenUI program string before passing it to the parser. Validate parsed component names, nested shape, depth, array sizes, and prop lengths; fail closed on unknown schema/version, malformed programs and parser errors. OpenUI's permissive partial render behavior must not relax the current trust boundary.
4. Disable Query/Mutation and all action/tool dispatch by default; any future action must be approved through a separate Guardian authority contract. Do not rely on omitting onAction alone as a security review.
5. Define an explicit component-pack/schema version and fallback behavior before persisting OpenUI program artifacts in user threads. Preserve compatibility across package updates and registry changes.
6. Prove streaming partial-program behavior, mobile width, shell-token light/dark/wallpaper contrast, accessibility, restore after reload, sanitization, isolation from secrets, and model emission quality (including small local models) independently.
7. Run dependency/license/telemetry review and current-tip full frontend checks before approval. Do not widen Beta or Preview claims while supported-Compose qualification remains HOLD.

## Scope and ADR

Architecture-impact if a production component ID and program format are admitted: `docs/architecture/generative-ui-contract.md` owns renderer rules; ADR-003 preserves message versus attempt identity; ADR-077 establishes deny-by-default sandbox authority posture; ADR-069 owns Beta release gating. No ADR was modified and no runtime contract was changed in this evaluation. An architecture decision may require ADR amendment or new ADR if OpenUI program syntax becomes persistent contract meaning; determine that in the follow-on task. Guardian, AG-UI, cfy-ui codec, SandboxFrame, nativeRegistry, provider prompts, routes, and persistence are unchanged.

## Non-goals

No live registry registration, model prompt integration, complete OpenUI application, tool provider, MCP client, new Guardian runtime, production wiring, deployment, push, release qualification, or migration.
