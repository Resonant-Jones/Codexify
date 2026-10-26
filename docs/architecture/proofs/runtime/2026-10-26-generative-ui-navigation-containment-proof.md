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
