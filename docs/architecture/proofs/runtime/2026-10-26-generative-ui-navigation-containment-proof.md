# Generated UI Sandbox Navigation Containment Proof

**Date:** 2026-10-26
**Evaluated commit:** `fb4c74bb8ef474bf8a19e2873e02b4dacd02de5f`
**Branch:** `test/saved-widget-navigation-containment-20261026`
**Disposition:** **FAIL**

**Contract:** [docs/architecture/generative-ui-contract.md](../../generative-ui-contract.md)
**ADR:** [ADR-102: Saved Widget Identity, Classification, and Revision Boundary](../../adr/102-saved-widget-identity-and-revision-boundary.md)

---

## 1. Disposition

**FAIL.** A generated UI frame can navigate itself to another document, and after
that navigation the frame's document CSP no longer applies. The navigated
document can issue outbound network requests that **reach the server**.

> **This is the PRE-REPAIR finding, and it is preserved unchanged.**
> The defect it records was subsequently repaired with a browser-enforced
> trusted-embedding boundary, and the repair was measured in Chrome 156. See
> [section 12](#12-repair-evidence--network-containment-across-navigation-2026-10-26).
> Sections 2–6 and 11 remain the historical record of the failure.

> **Addendum (2026-10-26).** The committed Playwright reproduction was later
> found to be defective and has been repaired. The corrected fixture has been
> executed and **reproduces the same failure**. See
> [section 11](#11-addendum--corrected-playwright-reproduction-2026-10-26),
> which keeps the original measurement, the corrected reproduction, and the
> still-unexecuted Playwright suite strictly apart. The finding below is
> unchanged.

The sandbox attribute itself is *not* breached. The frame stays opaque-origin,
retains no host API access, and still cannot navigate the parent or open a popup.
What is lost is the **network denial**, which the contract states as an absolute.

### The exact crossed boundary

> "**Codexify does not.** Generated UI receives **no network access at all**,
> consistent with the objective's security invariant against unrestricted network
> access and with ADR-077's deny-by-default network posture. Codexify therefore
> ships **no CDN importmap**; generated code may not fetch remote modules,
> fonts, tiles, or APIs."
> — [generative-ui-contract.md](../../generative-ui-contract.md), *Deliberate
> tightening versus upstream*

And, on the mechanism:

> "The containment boundary is the iframe `sandbox` attribute plus a
> document-level CSP."
> — [generative-ui-contract.md](../../generative-ui-contract.md), *Sandbox containment*

The proof establishes that the second half of that boundary is **document-scoped
and does not survive navigation**. The contract's description of the boundary is
therefore incomplete: it is the sandbox attribute *plus* a document-level CSP, and
the document-level CSP is lost the moment the document is replaced.

---

## 2. Browser and test environment

| | |
|---|---|
| Browser | **Google Chrome 156.0.0.0** (brands: `Chromium/156`, `Google Chrome/156`) |
| Platform | macOS, 10 logical cores, `en-US` |
| User agent | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36` |
| Driver | Chrome DevTools Protocol via the `chrome-devtools` MCP bridge |
| Frame construction | `buildSandboxDocument()` from `frontend/src/features/chat/components/generativeUi/SandboxFrame.tsx` — the shipped path, unmodified |
| Frame permissions | `sandbox="allow-scripts"` only — exactly as `SandboxFrame.tsx:283` renders it. No permission was weakened or added at any point |
| Fixture server | Local loopback `http://127.0.0.1:<ephemeral>`, Node `http`. Records every path it receives |
| Destinations | Loopback only. No public destination was contacted |
| Corpus of record | The fixture server's request log, not console output |

### The CORS control

The fixture's `/beacon` endpoint answers with `access-control-allow-origin: *`
and `access-control-allow-credentials: false`.

This is deliberate and load-bearing. A cross-origin `fetch()` from an
opaque-origin frame is otherwise rejected on **CORS** even when it succeeds at the
network layer, which would make "the fetch failed" ambiguous between *CSP
blocked it* and *CORS blocked the response*. With permissive CORS, a fetch from
the navigated document either **succeeds** or is **blocked by CSP**, and nothing
else. The measurement is therefore about CSP and not about CORS.

Without this control, the first run of the same scenario reported
`fetchReached=false, fetchError="TypeError: Failed to fetch"` while the fixture
log simultaneously showed `/beacon?from=dest-fetch` **had been received**. That
apparent contradiction is what the control removes.

---

## 3. Minimal reproduction

1. Serve a host page from `http://127.0.0.1:<port>` that embeds:

   ```html
   <iframe id="gen-ui" sandbox="allow-scripts" srcdoc="<built document>"></iframe>
   ```

   where `<built document>` is the output of the shipped
   `buildSandboxDocument(artifact, session)`, i.e. it carries the shipped CSP
   `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';
   img-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none';
   frame-src 'none'`.

2. The artifact's script is a single statement:

   ```html
   <p>navigating</p>
   <script>window.location.href = "/dest.html";</script>
   ```

3. Serve `/dest.html` as an ordinary document that declares **no CSP of its
   own** and attempts one request:

   ```js
   fetch("/beacon?from=dest-fetch")
   ```

4. **Observed:** the fixture request log contains, in order:

   ```
   /dest.html
   /beacon?from=dest-fetch
   /beacon?from=dest-image
   /beacon?dest=scriptRan=true&fetchReached=true&fetchError=null&imageLoaded=false&imageError=true&cookie=THREW&storageWorks=false&parentReadable=false
   ```

   `fetchReached=true` with `fetchError=null`: the navigated document's fetch
   **succeeded**.

No production code was changed to produce this. No iframe permission was
weakened. No CSP directive was added.

---

## 4. Navigation and request observations

All fifteen scripted cases plus one separately dispatched trusted click. The
"reached the fixture" column is the fixture server's own request log.

| # | Case | Trigger | Reached the fixture | Frame navigated | Parent navigated | Popup created |
|---|---|---|---|---|---|---|
| 1 | `plain-href` — `<a href="/dest.html">` | scripted click | **YES** — `/dest.html`, `/beacon?from=dest-fetch`, `/beacon?from=dest-image` | **YES** | no | no |
| 2 | `href-top` — `<a href="/dest.html" target="_top">` | scripted click | no | no | **no** | no |
| 3 | `href-blank` — `<a href="/dest.html" target="_blank">` | scripted click | no | no | no | **no** |
| 4 | `location-assign` — `window.location.href = "/dest.html"` | scripted | **YES** — same four requests | **YES** | no | no |
| 5 | `location-replace` — `window.location.replace("/dest.html")` | scripted | **YES** — same four requests | **YES** | no | no |
| 6 | `user-initiated` — `<a href="/dest.html">` | **real trusted click** | **YES** — `/dest.html`, `/beacon?from=dest-fetch`, `/beacon?from=dest-image` | **YES** | no | no |
| 7 | `redirect` — `window.location.href = "/redirect"` | scripted | **YES** — `/redirect`, then `/dest.html`, then the two beacons | **YES** | no | no |
| 8 | `form-submit` — `<form action="/dest.html">` + `form.submit()` | scripted | **no** | no | no | no |
| 9 | `direct-fetch` — `fetch("/beacon?from=direct-fetch")` | scripted | **no** | — | — | — |
| 10 | `image-request` — `<img src="/beacon?from=image-request">` | scripted | **no** | — | — | — |
| 11 | `relative-resource` — `<script src="/asset.js">`, `<img src="/beacon?...">` | scripted | **no** | — | — | — |
| 12 | `window-open` — `window.open("/dest.html", "_blank")` | scripted | **no** | — | no | **no** |
| 13 | `bridge-wrong-session` | scripted | no | — | — | — |
| 14 | `bridge-valid-session` | scripted | no | — | — | — |
| 15 | `bridge-unknown-action` | scripted | no | — | — | — |

Case 6 was driven with a real trusted input event dispatched at the link inside
the frame. It behaves **identically** to the scripted case: the frame navigates,
and the navigated document's fetch reaches the fixture. Scripted and
user-initiated navigation are not distinguishable in their effect.

Cases 2, 3, 12 and 8 are the boundaries that hold: no request occurred at all,
the parent did not navigate, and no popup was created. `list_pages` after the
full run reported exactly one page.

---

## 5. Post-navigation containment

Measured from inside the navigated document, which reports its own facts to the
fixture (it cannot be read by the host, because the frame is opaque-origin):

| Property | Observed | Meaning |
|---|---|---|
| `scriptRan` | `true` | The destination document **executed scripts** |
| `fetchReached` | `true` | Its outbound `fetch()` **succeeded** — the frame's CSP did not apply |
| `imageLoaded` | `false`, request received | The image **request left the browser**; the 204 response is not a decodable image, which is why the element errored |
| `cookie` | `THREW` | `document.cookie` threw — **opaque origin persists** |
| `storageWorks` | `false` | `localStorage` unusable — **opaque origin persists** |
| `parentReadable` | `false` | `parent.document` inaccessible — **sandbox persists** |

**So the sandbox attribute holds across navigation.** The frame does not gain
host DOM access, host storage, or credentials. What it gains is **network egress**,
because the CSP was a `<meta http-equiv>` on the *original* document and the
navigation replaced it with a document that declares no policy.

The navigated document also does **not** inherit the bridge session: it never
receives the session token, so its `postMessage` calls would fail the session
binding. The bridge is not the weak link here.

### The bridge, measured separately

The host-side handler mirrored `SandboxFrame.tsx`'s `handleMessage` exactly:
source binding against the frame's `contentWindow`, `event.origin === "null"`,
channel binding, session binding, payload schema, and "unknown actions are
ignored, never partially applied".

| Case | Message reached the host | Accepted by the host |
|---|---|---|
| `bridge-wrong-session` | yes — `origin=null`, `session=not-the-session`, `action=send_prompt` | **no** |
| `bridge-valid-session` | yes — `origin=null`, `session=ui-containment-session`, `action=send_prompt` | **yes** — `send_prompt` accepted |
| `bridge-unknown-action` | yes — `origin=null`, `session=ui-containment-session`, `action=install_everything` | **no** — only the frame's own `resize` was accepted |

Every message arrived with `event.origin === "null"`, independently confirming
the opaque origin. The bridge behaved correctly in all three cases: it rejected
a wrong session, accepted a valid one, and ignored an unknown action without
partially applying it.

---

## 6. E4 classification review

The Saved Widget validator's E4 gate classifies *declared* dependencies. This
proof measures what each category actually does at runtime.

| Category | E4 treatment | Measured behaviour | Verdict |
|---|---|---|---|
| **Declarative resource loading** — `<img src>`, `<script src>`, `<link href>` | external → rejected | external request **blocked** (never left the browser) | **Sound.** E4 rejects what the runtime already denies |
| **`data:` / `blob:` resources** | self-contained | permitted by `img-src data: blob:` | **Sound.** These are genuinely usable |
| **Relative resources without a bundled package** | **self-contained** | **never load** — the frame ships no resource package and `default-src 'none'` denies the load | **Misclassification.** A relative dependency is eligible under E4 but is unusable at runtime. Every relative dependency in a candidate is dead weight: the widget will not behave as authored |
| **Passive hyperlink navigation** — `<a href>` | **excluded** from the dependency gate | same-frame navigation **succeeds** and the frame then regains network egress | **Unsound as currently classified.** An `<a href>` is the simplest route from generated code to an arbitrary document, and after the navigation the frame has no CSP. Excluding it from E4 leaves the highest-value navigation vector unexamined |
| **Dynamic JavaScript navigation** — `location.href = …`, `location.replace(…)`, `window.open(…)` | **not visible to E4 at all** — these are not declarative dependencies | `location.href` and `location.replace` **navigate the frame**; `window.open` is blocked by the sandbox | **Blind spot.** The path with the largest consequence is invisible to the classifier |

### Which currently eligible dependency declarations are actually unusable or unqualified

- **Unusable:** every **relative** resource declaration (`<script src="./x.js">`,
  `<img src="./x.png">`, `@import url('./x.css')`). E4 classifies these as
  self-contained; the runtime never loads them. A Saved Widget that depends on
  them is not a working widget.
- **Unqualified:** every **absolute or cross-origin `<a href>`** and every
  **dynamic navigation statement**. E4 neither rejects nor bounds them, and the
  runtime permits the same-frame variants.

### The load-bearing conclusion

**No E4 improvement can close this.** E4 is a parser-side filter over the
artifact's *declared* dependencies. The gap is a *runtime* property of the frame
after a navigation the classifier cannot see. A perfect dependency classifier
would still let a widget that contains no declared dependency at all navigate
itself and then beacon.

The correction therefore has two parts, and the **runtime** part is the
authoritative one:

1. **Runtime containment (authoritative, and the part that must be fixed
   first).** Same-frame navigation must not leave a frame that can reach the
   network. Options, with their honest limits:
   - *Host-side teardown.* The host detects the frame's navigation and destroys
     the frame immediately, terminating the destination document. This narrows
     the window to the single load event; it does not eliminate it, because the
     destination can beacon before it is torn down. **A mitigation, not a proof.**
   - *Dedicated, egress-isolated origin for generated frames.* Serving generated
     UI from an origin with no network egress path (a loopback-only or
     locally-served scheme) means that even a navigated document can reach
     nothing but the user's own loopback services — a far smaller and more
     auditable surface than the open internet. **This is the only option that
     proves the boundary** rather than narrowing a race, and it is a real
     architecture decision with its own cost.
   - *Note on `navigate-to`.* The CSP `navigate-to` directive was removed from
     the specification and is not implemented in Chrome. It is not an available
     mitigation.

2. **Classification correction (secondary, and explicitly not a new scanner).**
   Extend E4 with a **narrow, syntactic** check for navigation *intent* — an
   `a[href]` whose target is not a same-document fragment, and assignments to
   `location` / `window.location` / `location.replace`. This is a bounded
   pattern match over the artifact's own text, not a general JavaScript security
   scanner, and it exists to route the decision to a human rather than to
   silently allow an unqualified navigation. It must not be mistaken for the
   control.

**Persistence readiness is not claimed.** Under ADR-102 a Saved Widget is
reusable across conversations. A widget that navigates itself away and then
reaches the network is worse than no widget at all: it would be re-invoked in
other conversations and would keep the hole open there.

---

## 7. Reproduction

### Committed, reproducible form

`frontend/src/tests/playwright/generative-ui-navigation-containment.spec.ts`
builds the frame with the shipped `buildSandboxDocument()`, serves the same
loopback fixture endpoints, and asserts the same outcomes. The known gap is
encoded with Playwright's `test.fail()`, so it is documented without turning CI
red, and it will surface as a real failure if the behaviour ever changes.

```
pnpm --dir frontend/src exec playwright test \
  --config playwright.config.ts \
  tests/playwright/generative-ui-navigation-containment.spec.ts
```

### In-environment deviation, and why

**The Playwright suite cannot execute in this environment.** This is an
environment limitation, not a property of the code under test, and it is
reported rather than substituted.

The actual outcome of the command above in this environment:

```
Running 16 tests using 1 worker
…
16 failed          (exit 1)
```

Every test fails during browser launch, before any assertion runs. The
browser's own output:

```
sandbox_extension_issue_file_to_process failed for /Applications/MiniMax Code.app: 1 (Operation not permitted)
[pid=…][err] FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS.
  bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.…: Permission denied (1100)
```

This is the host's macOS seatbelt sandbox refusing Chromium's Mach port
rendezvous. It reproduced identically for:

- Playwright's own `chromium-1217` and `chromium_headless_shell-1217`
  (both now present on disk; the install command itself aborted with exit 134
  *after* writing the binaries);
- the previously cached `chromium-1194` (Chromium 141.0.7390.37) and
  `chromium_headless_shell-1194`;
- the installed system Google Chrome, via both `channel: 'chrome'` and
  `executablePath`.

The Playwright CLI itself is repaired and functional: `Version 1.59.1`,
matching the lockfile (`@playwright/test@1.59.1`). Only the browser process
is refused.

> **A note on the first run's apparent success.** An earlier run of this suite
> reported "3 passed". That was an artefact, not evidence: Playwright counts a
> setup failure as an expected failure for a `test.fail()` case, so the
> known-gap cases reported green while the browser had never started. The spec
> now carries a **liveness test** that is deliberately *not* marked
> `test.fail()`; it asserts that the browser launches, that the fixture
> answers, and that the frame carries `sandbox="allow-scripts"` and the shipped
> CSP. With it, an environment that cannot start a browser reports the suite
> red instead of green.

The scenario was therefore executed against **Google Chrome 156.0.0.0** over the
Chrome DevTools Protocol, which launches successfully in this environment. The
frame under test, the iframe permission set, the CSP, the fixture endpoints, and
every assertion are identical to the committed spec. The one mechanical
difference is the input driver: the trusted click in case 6 was dispatched
through DevTools `Input` rather than Playwright's own click, which produces the
same trusted event type.

**Known limitations of this proof**

1. The evidence was collected in one browser build (Google Chrome 156.0.0.0 on
   macOS). The behaviour under test is governed by HTML sandbox and CSP
   semantics that are long-stable, but this proof does not establish
   cross-browser or cross-platform equivalence, and it does not qualify any
   other browser.
2. The committed Playwright spec has **not** been executed anywhere yet — not
   here, where Chromium cannot launch, and not in CI. It is committed as the
   reproducible form of the experiment, and it must be run once in an
   environment that can start a browser before the disposition below is treated
   as independently reproduced. The measurement it encodes is the one recorded
   here.
3. The destination document is a minimal fixture. A real destination could
   behave differently, but the finding does not depend on the destination's
   content: the destination only has to exist and make one request.
4. The proof establishes that the boundary is **breached**. It does not
   characterise how much data could be exfiltrated in the window before any
   host-side teardown, because no teardown exists in the current
   implementation.

### Validation commands and outcomes

| Command | Outcome |
|---|---|
| `git diff --check` | exit 0 — no whitespace defects |
| `pnpm --dir frontend/src exec playwright test --config playwright.config.ts tests/playwright/generative-ui-navigation-containment.spec.ts` | **exit 1** — 16 tests collected, all failing at browser launch (seatbelt denial above). This is an environment failure, not a test-logic failure, and the liveness test makes it impossible to mistake for a pass |
| The identical scenario driven over the Chrome DevTools Protocol against Google Chrome 156.0.0.0 | **15 scripted cases + 1 separately dispatched trusted click, all executed.** The loopback fixture received **19 requests**; the `/dest.html` → `/beacon?from=dest-fetch` → `fetchReached=true` pattern repeated exactly four times (cases 1, 4, 5, 7) and once more under the trusted click (case 6) |

---

## 8. Invariants check

| Invariant | Status |
|---|---|
| Opaque origin | **Held.** `document.cookie` threw, `localStorage` unusable, `parent.document` inaccessible, every bridge message arrived with `origin === "null"` |
| Script-only iframe permission | **Held.** No `allow-same-origin`, `allow-top-navigation`, `allow-popups`, or `allow-forms` was present, and none was added |
| No privileged host APIs | **Held.** `parent.document` remained inaccessible after navigation |
| No credentials passed into generated UI | **Held.** No credential was observed to reach the navigated document |
| Session-bound, validated bridge | **Held.** Wrong session rejected, valid session accepted, unknown action ignored |
| No automatic promotion or execution authority | **Held.** Nothing in this proof grants or executes a Saved Widget |
| No unverified release claims | **Held.** The release gate remains `HOLD`; this proof makes no release claim |

**One invariant does not hold:** *no unrestricted network access*. It holds for
the original generated document and fails for a document the frame navigates to.

---

## 9. ADR impact

Aligned with Accepted ADR-102 and ADR-077. No new ADR. No supersession. No
authority or permission change was made in this task, and no runtime file was
modified.

The finding does not contradict ADR-102's accepted design; it qualifies one of
its inputs. ADR-102's E4 gate and the generative UI contract both treat the
document CSP as the network-denial control. This proof shows that control is
document-scoped. Any change to how the network boundary is enforced requires its
own architecture-impact implementation task.

---

## 10. Recommended next corrective slice

**Do not begin Saved Widget persistence.** A durable, cross-conversation widget
that can navigate itself and then reach the network would reproduce this hole in
every thread it is invoked in.

The next atomic task should be a **focused runtime containment repair**, scoped
as:

1. Decide the enforcement mechanism for "no network egress from a generated UI
   frame", including the case where the frame has navigated away from its
   original document. The dedicated egress-isolated origin is the only option
   observed to *prove* the boundary; host-side teardown alone narrows a race.
2. Extend the E4 dependency gate with a narrow, syntactic navigation-intent
   check, explicitly scoped as classification and explicitly **not** a general
   JavaScript security scanner, and explicitly not the control.
3. Re-run this proof against the repaired containment, and update the committed
   Playwright spec so that the `test.fail()` assertions become passing
   assertions.

Independently and in parallel, the **relative-resource misclassification** in
E4 should be corrected: a relative resource declaration is not "self-contained"
for a frame that ships no resource package, and a candidate depending on one is
not a working widget. That correction belongs with the validation work and does
not depend on the containment repair.

---

## 11. Addendum — corrected Playwright reproduction (2026-10-26)

This addendum is a **later, separate** record. It does not rewrite the
measurement in sections 2–6, and it does not replace the FAIL finding.

Three things are kept apart throughout:

| | What it is | Status |
|---|---|---|
| **1. Original CDP measurement** | The Chrome DevTools Protocol run recorded in sections 2–6 | **Unchanged.** Still the primary observation of the failure. |
| **2. Corrected Playwright reproduction** | The repaired committed fixture, executed against the same browser engine | **Executed.** Reproduces the same failure. |
| **3. Unexecuted tests** | The committed Playwright suite, as committed | **Not executed here.** Chromium cannot launch in this environment. |

### 11.1 The defects found in the committed spec

Source inspection of the committed spec found three defects that made the
committed reproduction incapable of executing as written:

1. **The generated iframe was never inserted.** `HOST_HTML` contained only
   `<div id="frames"></div>`, and the server substituted `__FRAME_DOC__` into a
   template that had no such placeholder. `hostDocuments` stored an iframe
   *fragment* whose `srcdoc` was the literal string `__FRAME_DOC__`, not the
   output of `buildSandboxDocument()`. The host page therefore served no
   generated frame at all.
2. **The bridge rejected every message.** `activeFrameWindow` was initialised
   to `null` and never assigned the generated frame's `contentWindow`, so the
   source-identity check failed before the session, channel, schema, and
   payload checks could run. The committed spec's bridge assertions could not
   have distinguished an accepted message from a rejected one.
3. **The readiness check violated opaque-origin isolation.** `runCase()` waited
   for `frame.contentDocument.body` from the host page. A frame sandboxed
   without `allow-same-origin` has an opaque origin, so that read is `null` by
   design. The wait could only ever succeed if the sandbox were weakened.

A fourth, reporting-level defect surfaced while executing it: the known-gap
cases were marked `test.fail()`, and Playwright counts a **setup failure** —
including a browser that cannot launch at all — as an expected failure. The
suite therefore reported "3 passed" when the browser had never started. That
was an artefact, not evidence.

### 11.2 The correction

The fixture was rebuilt so that:

- `HOST_HTML` contains the generated iframe in its markup, with `srcdoc`
  carrying the **production-built** document from `buildSandboxDocument()`;
- the document is embedded as an escaped attribute value (`&` and `"`), and the
  replacements use function form, so a `$&` sequence inside generated content
  cannot be reinterpreted as a replacement pattern;
- the host page binds `activeFrameWindow` to
  `document.getElementById("gen-ui").contentWindow`;
- readiness uses a **frame locator** and the production bridge's own `resize`
  message, never the host's same-origin API;
- a **liveness test** that is deliberately not marked `test.fail()` asserts
  that the browser launched, the fixture server answered, the host document
  loaded, exactly one generated iframe exists and carries
  `sandbox="allow-scripts"`, the production CSP is present, the generated
  JavaScript actually ran, and the fixture server records requests.

**No production file was changed.** The sandbox attribute, the CSP, the bridge
semantics, the action set, and the payload bounds are exactly as shipped.

### 11.3 Browser-free verification of the fixture

The committed spec module was imported with a stubbed test runner, so the
fixture code under test is the real committed code. **26 checks, all passing:**

- the host document contains the generated iframe, sandboxed exactly as shipped;
- no `__FRAME_DOC__` or `__SESSION__` placeholder survives;
- the decoded `srcdoc` is a complete document carrying the production CSP, the
  production bridge script, and the generated artifact content;
- attribute escaping did not corrupt the generated HTML — the document's own
  `</script>` survives intact inside the attribute value;
- the bridge keeps its source, opaque-origin, session, channel, payload-bound,
  and unknown-action checks;
- the fixture server starts, serves the host document, and records requests.

### 11.4 Execution evidence — corrected fixture, same browser

| | |
|---|---|
| Browser | **Google Chrome 156.0.0.0**, macOS — the same engine as the original CDP measurement |
| Fixture | The **committed** fixture: the committed server, the committed host page, and the committed production document builder |
| Cases executed | **16 of 16** — 15 scripted, plus one separately dispatched real trusted click |
| Blocked-case results | Unchanged from the original measurement |
| Bridge results | Correct, and now **distinguishable** — the source binding works |

**The exploit reproduces on the corrected fixture.** For `plain-href`,
`location-assign`, `location-replace`, `redirect`, and the real trusted click,
the fixture recorded the navigation and then the replacement document's outbound
request:

```
/dest.html
/beacon?from=dest-fetch
/beacon?from=dest-image
/beacon?dest=scriptRan=true&fetchReached=true&fetchError=null&imageLoaded=false&imageError=true&cookie=THREW&storageWorks=false&parentReadable=false
```

`fetchReached=true` against a beacon that answers with permissive CORS, so the
only thing that could have blocked it is CSP. The replacement document executed
(`scriptRan=true`) while the frame kept its opaque origin (`cookie=THREW`,
`storageWorks=false`, `parentReadable=false`).

**The boundaries that still hold still hold.** `href-top`, `href-blank`,
`window-open`, `form-submit`, `direct-fetch`, `image-request`, and
`relative-resource` recorded **no request at all**.

**The bridge now behaves and is now observable.** Every message arrived with
`origin === "null"` and `sourceIsActiveFrame === true`. A message with the
wrong session was **rejected** — only the frame's own `resize` was accepted. A
message with the correct session was **accepted** (`send_prompt`). An unknown
action was **ignored** and never partially applied.

### 11.5 The committed Playwright suite remains unexecuted here

The committed command was run and its outcome recorded:

```
pnpm --dir frontend/src exec playwright test \
  --config playwright.config.ts \
  tests/playwright/generative-ui-navigation-containment.spec.ts
```

**exit 1 — 19 tests collected, all 19 failing during browser launch**, with the
host's macOS seatbelt sandbox refusing Chromium's Mach port rendezvous:

```
sandbox_extension_issue_file_to_process failed for /Applications/MiniMax Code.app: 1 (Operation not permitted)
FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS.
  bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.<pid>: Permission denied (1100)
```

All 19 fail, **including the two liveness tests** — which is the intended
behaviour now that no test in the file uses `test.fail()`. An environment that
cannot start a browser reports the suite red instead of green.

**Playwright qualification is therefore not claimed.** The corrected suite has
been executed against Chrome 156 through the DevTools Protocol, which runs the
identical committed fixture; it has not been executed by Playwright's own
launcher on this host.

### 11.6 Disposition of independent reproduction

**The FAIL finding stands, and is now reproducible on the corrected fixture.**

| Claim | Level of evidence |
|---|---|
| A generated UI frame can navigate itself and then reach the network | **Reproduced twice** — on the original harness and on the corrected committed fixture, in Chrome 156.0.0.0 |
| The committed Playwright suite runs green | **Not claimed.** It cannot launch a browser on this host, and it reports red |
| The containment boundary holds | **False.** The boundary is breached; that is the finding |
| Saved Widget persistence is ready | **Not claimed, and explicitly blocked** |

### 11.7 Remaining environment limitations

1. The committed Playwright suite has **not** been executed by Playwright's own
   launcher anywhere. It must be run once in an environment that can start a
   browser before the reproduction is treated as independently reproduced by the
   committed test alone.
2. All browser evidence is from one engine build (Google Chrome 156.0.0.0 on
   macOS). Cross-browser and cross-platform behaviour is not established.
3. The corrected fixture was executed by driving the committed host document's
   `srcdoc` with the committed per-case document, rather than by re-navigating
   the host page once per case. The frame document, the host page's bridge, and
   the fixture server's log are all the committed ones; only the per-case page
   reload differs, and it cannot affect the frame's document, the bridge
   binding, or the recorded requests.
4. The proof does not characterise how much could be exfiltrated in the window
   before any host-side teardown, because no teardown exists yet.

### 11.8 What the correction changes about the recommendation

Nothing in the recommendation changes. The runtime containment repair is still
the next atomic task, and Saved Widget persistence remains blocked behind it.

One item in section 10 is now stale in a minor way: the note about updating
the committed spec "so that the `test.fail()` assertions become passing
assertions" describes the old shape. The corrected spec no longer uses
`test.fail()`: the reproduction cases assert the **observed vulnerable
behaviour** directly, so a future containment repair must invert them, and the
liveness test keeps an infrastructure failure from ever reading as a pass.

---

## 12. Repair evidence — network containment across navigation (2026-10-26)

This section records the **repair** of the defect measured above. Sections 2–6
and 11 are the historical record and are **not** rewritten: the pre-repair
failure remains the pre-repair failure, and it is kept here as the baseline the
repair is measured against.

### 12.1 The defect, restated precisely

The generated document's CSP is a `<meta http-equiv>` on **that document**. A
same-frame navigation replaces the document with one that declares no policy,
and the replacement then had no network restriction. The broken invariant was
**network denial** — not account authorization, not host DOM isolation, not the
bridge.

### 12.2 The mechanism selected

A **trusted outer wrapper document**, built by Codexify, that embeds the
generated document in a nested sandboxed `srcdoc` frame:

```html
<!-- app page -->
<iframe sandbox="allow-scripts" srcdoc="<trusted wrapper>" />

<!-- trusted wrapper, built by Codexify -->
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src 'none'; ...">
<iframe id="cfy-ui-inner" sandbox="allow-scripts" srcdoc="<generated document>" />
```

`frame-src 'none'` is load-bearing. It governs which URLs may be loaded into
**child frames**: a child loaded from `about:srcdoc` is permitted, so the
generated frame still loads, while a child navigated to any real URL is blocked
**before the request is made**. The network boundary therefore survives
navigation, because the navigation never happens.

The wrapper's `frame-src` is scoped to the wrapper document and is deliberately
**not** applied to the Codexify app document, so other workspace iframe surfaces
are unaffected. The wrapper is itself sandboxed (`allow-scripts`, no
`allow-same-origin`), so it keeps an opaque origin and cannot reach the
Codexify document. It contains no generated source: generated content cannot
reach the wrapper's CSP or its relay logic.

### 12.3 Candidate verification, before any production change

The mechanism was measured **before** it was adopted, in a real browser, against
the real `buildSandboxDocument()` output.

| | |
|---|---|
| Browser | **Google Chrome 156.0.0.0**, macOS |
| Harness | local loopback fixture server, request log as primary evidence |
| Cases | 16 — benign load, same-frame `location.href`, `location.replace`, anchor click, `parent.location`, `top.location`, `window.open`, redirect chain, `about:blank`, `about:srcdoc`, `data:`, `blob:`, `javascript:`, cross-origin navigation, inner subresource request, and a real trusted click |
| Result | **Zero requests reached the fixture in every case** |

The browser's own console recorded the enforcement:

```text
Framing 'http://127.0.0.1:PORT/dest.html' violates the following Content
Security Policy directive: "frame-src 'none'". The request has been blocked.
Framing 'http://localhost:PORT/' violates ... "frame-src 'none'". The request has been blocked.
Framing '' violates ... "frame-src 'none'". The request has been blocked.   [about:blank, about:srcdoc]
Unsafe attempt to initiate navigation ... from frame with URL 'about:srcdoc'. The
  frame attempting navigation is sandboxed, and is therefore disallowed from
  navigating its ancestors.                                              [parent]
Unsafe attempt to initiate navigation of the top-level window ... 'allow-top-navigation'
  is not set.                                                            [top]
Blocked opening ... in a new window because ... 'allow-popups' permission is not set.
Loading the image '.../beacon?from=inner-subresource' violates ... "img-src data: blob:".
```

The `from frame with URL 'about:srcdoc'` entries are also the positive proof
that the generated document loaded and its JavaScript executed.

### 12.4 The implemented repair, measured

The committed Playwright fixture was rebuilt to use the **production**
`buildSandboxDocument()` **and** `buildSandboxWrapperDocument()`, and the
committed spec now asserts the **repaired** boundary. It was executed against
the same browser engine.

| | |
|---|---|
| Browser | **Google Chrome 156.0.0.0**, macOS |
| Cases executed | **24** scripted cases, plus one interaction case driven with real trusted clicks |
| Navigation requests reaching the fixture | **0** |
| Destination documents ever loaded | **0** — no replacement document ran, so no beacon could be emitted |
| Parent navigation / popups | none, for every case |
| Bridge, wrong session | **rejected** — only the frame's own `resize` was accepted |
| Bridge, correct session | **accepted** — `send_prompt` and `resize` |
| Bridge, unknown action | **ignored** — never partially applied |
| Every bridge message origin | `"null"`, from the wrapper's `contentWindow` |

Ordinary generated-interface behaviour was re-verified in the same run:

| Property | Observed |
|---|---|
| Inline HTML renders | `hello` |
| CSS applies | computed `color: rgb(1, 2, 3)` |
| Inline JavaScript executes | the generated script ran (it set the document title) |
| Button responds to input | `#out` became `clicked` after a real trusted click |
| Text input remains usable | the field held `typed` |
| `send_prompt` reaches the composer-prefill pathway | the host received `please help` |
| Frame resizes within bounds | `resize` accepted |

### 12.5 Playwright execution status

**BLOCKED, separately attributed.** The committed command was run:

```
PW_START_WEBSERVER=false pnpm --dir frontend/src exec playwright test \
  --config playwright.config.ts \
  tests/playwright/generative-ui-navigation-containment.spec.ts \
  --output=<path that does not exist yet>
```

The runner works and collects the suite — **29 tests** in the repaired spec. The
**browser cannot start**: the host's macOS seatbelt sandbox refuses Chromium's
Mach port rendezvous, with the browser's own output:

```text
sandbox_extension_issue_file_to_process failed for /Applications/MiniMax Code.app: 1 (Operation not permitted)
FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS.
  bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.<pid>: Permission denied (1100)
```

All tests therefore fail during browser launch, **including the liveness
tests**. That is the intended behaviour: the suite contains no `test.fail()`,
so an environment that cannot start a browser reports red rather than green.

**Playwright qualification is not claimed.** The evidence in 12.4 comes from
executing the identical committed fixture against Chrome 156 over the DevTools
Protocol. The committed Playwright suite must still be run once in an
environment that can start a browser.

### 12.6 Disposition

**PASS for the repair, on Chrome 156 evidence.** The original FAIL finding is
resolved: the network boundary now survives navigation, and the failure mode is
closed at the browser-enforced level rather than by a static check or by
after-the-fact teardown.

| Claim | Level of evidence |
|---|---|
| The pre-repair escape reached the network | **Proven** (sections 2–6) and **preserved** as the historical record |
| The repaired configuration blocks every navigation-attempted request | **Proven in Chrome 156** against the production wrapper (24 cases, 0 requests) |
| The repaired configuration preserves ordinary widget behaviour | **Proven in Chrome 156** |
| The committed Playwright suite passes | **Not claimed** — it cannot launch a browser on this host and reports red |
| Cross-browser containment equivalence | **Not claimed.** Only Chrome 156 was tested. Safari, WebKit, mobile, and Tauri hosts are **not** proven and must not be presented as proven |
| The E4 relative-resource misclassification | **Still open**, and out of scope for this repair |

### 12.7 Security invariant checks

| Invariant | Status |
|---|---|
| Generated programs remain untrusted | Held — the generated document is still untrusted, sandboxed, and opaque-origin |
| No unrestricted network access | **Restored** — the request log records zero requests for every navigation case |
| No host DOM or storage access | Held — the wrapper and the generated frame are separate opaque-origin documents; the host document is unreachable from either |
| No Guardian credentials in generated content | Held — no credential travels the bridge |
| No Tauri native authority | Held — unchanged |
| No added sandbox permissions | Held — `allow-scripts` only on both frames; nothing added |
| No new bridge actions | Held — `resize` and `send_prompt` only; the wrapper forwards nothing else |
| No automatic saving or execution escalation | Held — unchanged |
| Session-bound message authorization | Held — and now enforced at **both** hops |
| No unproven release claims | Held — release gate remains `HOLD`; no runtime support is claimed |

### 12.8 What is deferred

1. **Cross-browser qualification.** Only Chrome 156 was exercised. A WebKit/Safari
   and a desktop/Tauri host run of the committed suite is still required before
   the repair may be described as host-portable.
2. **The Playwright suite itself** must be run once where a browser can start.
3. **The E4 relative-resource classification** remains a separate correction,
   as recorded in section 10. It does not depend on this repair, but it must be
   fixed before Saved Widget persistence, because a candidate that depends on a
   relative resource is not a working widget.
4. **The E4 navigation-intent gap** is unchanged: E4 still cannot see a dynamic
   navigation statement. The repair makes that gap harmless at runtime, because
   the runtime boundary now holds regardless — but E4 remains a packaging
   filter, never the control.
