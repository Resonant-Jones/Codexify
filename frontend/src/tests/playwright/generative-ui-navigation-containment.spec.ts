/**
 * Generated UI sandbox navigation containment — executable reproduction.
 *
 * Establishes, in a real browser, what network requests and what navigation a
 * generated UI iframe can initiate under the containment configuration the
 * product actually ships.
 *
 * The frame is built with the **actual** document-generation path:
 * `buildSandboxDocument()` from
 * `frontend/src/features/chat/components/generativeUi/SandboxFrame.tsx`, and
 * embedded with the **actual** iframe permission set (`sandbox="allow-scripts"`,
 * no `allow-same-origin`, no `allow-top-navigation`, no `allow-popups`, no
 * `allow-forms`). This spec never weakens iframe permissions to make a case
 * pass, and it never substitutes a hand-written CSP mock for the shipped one.
 *
 * Every observation that matters is made through a local loopback fixture
 * server that records the paths it actually receives. The browser console is
 * recorded as supporting detail only; no assertion in this file rests on a
 * console warning alone.
 *
 * The beacon endpoint answers with a permissive CORS header on purpose. A
 * cross-origin fetch from an opaque-origin frame can then *succeed* unless CSP
 * blocks it, which makes the fetch result unambiguous evidence about CSP
 * rather than about CORS.
 *
 * ---------------------------------------------------------------------------
 * READ THIS BEFORE READING ANY ASSERTION
 * ---------------------------------------------------------------------------
 * The "reproduction" tests below assert the **observed vulnerable behaviour**.
 * A passing reproduction test means:
 *
 *     "the known exploit was reproduced"
 *
 * It does NOT mean:
 *
 *     "the containment boundary passed"
 *
 * The security boundary is still broken. These tests are a negative security
 * baseline: they lock in the exploit so that a future containment repair is
 * forced to invert them, and so that a regression cannot be mistaken for a
 * fix. The separate "security regression" tests assert the boundaries that
 * still hold, and they are the ones that must keep passing.
 *
 * No test in this file uses `test.fail()`. Playwright counts a setup failure —
 * including a browser that cannot launch at all — as an expected failure for a
 * `test.fail()` case, which would let this suite report green with no browser
 * ever started. The liveness test below is deliberately unmarked, so an
 * infrastructure failure is always red.
 *
 * Disposition and evidence:
 * docs/architecture/proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md
 *
 * Contract: docs/architecture/generative-ui-contract.md
 * ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
 */
import { test, expect, type Browser, type BrowserContext, type Page } from '@playwright/test';
import http from 'node:http';
import type { AddressInfo } from 'node:net';

import { buildSandboxDocument } from '../../features/chat/components/generativeUi/SandboxFrame';
import type { SandboxUiArtifact } from '../../features/chat/components/generativeUi/artifactCodec';

// ---------------------------------------------------------------------------
// Fixture server
// ---------------------------------------------------------------------------

export const SESSION = 'ui-containment-session';

/**
 * Evidence log: the paths the fixture server actually received as a result of
 * something the generated frame did. Harness plumbing is excluded.
 */
const received: string[] = [];

/** Every request the server received, harness plumbing included. */
const allRequests: string[] = [];

const HARNESS_PATHS = new Set(['/host.html', '/__mark', '/__log', '/__all']);

/**
 * The host page.
 *
 * The iframe is present in the markup and carries the production-generated
 * document in its `srcdoc` attribute. The bridge validation mirrors
 * SandboxFrame.tsx's host-side `handleMessage`: source binding (compared
 * against the frame's `contentWindow`, never the element), opaque-origin
 * binding, channel binding, session binding, schema validation, and "unknown
 * actions are ignored, never partially applied".
 */
const HOST_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>containment host</title></head>
<body>
<h1>containment host</h1>
<iframe id="gen-ui" title="generated interface" sandbox="allow-scripts" srcdoc="__FRAME_DOC__" style="width:100%;height:200px;border:0"></iframe>
<script>
  var SESSION = __SESSION__;
  // Source binding. The bridge accepts a message only when it came from this
  // frame's own contentWindow, so the binding has to point at the generated
  // frame. The iframe element precedes this script, so the reference is
  // resolved at parse time.
  var activeFrameWindow = document.getElementById("gen-ui").contentWindow;
  var accepted = [];
  var messages = [];

  window.addEventListener("message", function (event) {
    var raw = event.data;
    messages.push({
      origin: event.origin,
      sourceIsActiveFrame: !!activeFrameWindow && event.source === activeFrameWindow,
      channel: raw && raw.channel,
      session: raw && raw.session,
      action: raw && raw.action
    });
    // Source identity.
    if (!activeFrameWindow || event.source !== activeFrameWindow) return;
    // The opaque origin of a sandboxed frame serializes to "null".
    if (event.origin !== "null") return;
    var data = raw;
    if (!data || typeof data !== "object") return;
    if (data.channel !== "cfy-ui") return;
    if (data.session !== SESSION) return;
    var payload = (data.payload && typeof data.payload === "object" ? data.payload : {});
    if (data.action === "resize") { accepted.push("resize"); return; }
    if (data.action === "send_prompt") {
      var text = typeof payload.text === "string" ? payload.text.trim() : "";
      if (!text || text.length > 2000) return;
      accepted.push("send_prompt");
      return;
    }
    // Unknown actions are ignored, never partially applied.
  });

  window.__accepted = accepted;
  window.__messages = messages;
</script>
</body>
</html>`;

/**
 * The destination document. It declares no CSP of its own.
 *
 * If the frame's original document CSP still applied after the navigation,
 * the fetch below would be denied. It also reports whether host storage,
 * cookies, and the parent document are reachable, so the post-navigation
 * isolation can be measured from inside the frame.
 */
const DEST_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>destination</title></head>
<body>
<p id="marker">destination document</p>
<script>
  window.__destScriptRan = true;
  var facts = {
    scriptRan: true,
    fetchReached: false,
    fetchError: null,
    imageLoaded: false,
    imageError: false,
    cookie: null,
    storageWorks: false,
    parentReadable: false
  };
  try {
    fetch("/beacon?from=dest-fetch")
      .then(function () { facts.fetchReached = true; })
      .catch(function (e) { facts.fetchError = String(e); });
  } catch (e) { facts.fetchError = String(e); }
  try {
    var img = new Image();
    img.onload = function () { facts.imageLoaded = true; };
    img.onerror = function () { facts.imageError = true; };
    img.src = "/beacon?from=dest-image";
  } catch (e) { facts.imageError = true; }
  try { facts.cookie = document.cookie; } catch (e) { facts.cookie = "THREW"; }
  try { window.localStorage.setItem("k", "v"); facts.storageWorks = true; } catch (e) { facts.storageWorks = false; }
  try { void parent.document.title; facts.parentReadable = true; } catch (e) { facts.parentReadable = false; }
  setTimeout(function () {
    var q = Object.keys(facts).map(function (k) {
      return k + "=" + encodeURIComponent(String(facts[k]));
    }).join("&");
    try { new Image().src = "/beacon?dest=" + q; } catch (e) { new Image().src = "/beacon?dest=reportFailed"; }
  }, 500);
</script>
</body>
</html>`;

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

export type CaseSpec = {
  id: string;
  html: string;
  js: string;
  /** 'script' runs the artifact's own script; 'click' dispatches a real click. */
  trigger: 'script' | 'click';
};

export const CASES: CaseSpec[] = [
  // Liveness: the generated script marks the document, so the harness can
  // prove that production-generated JavaScript actually ran.
  {
    id: 'liveness',
    html: `<p id="exec-marker">pending</p>`,
    js: `document.getElementById("exec-marker").setAttribute("data-executed", "yes");`,
    trigger: 'script',
  },
  // The known exploit.
  { id: 'plain-href', html: `<a id="go" href="/dest.html">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'user-initiated', html: `<a id="go" href="/dest.html">go</a>`, js: ``, trigger: 'click' },
  { id: 'location-assign', html: `<p>navigating</p>`, js: `window.location.href = "/dest.html";`, trigger: 'script' },
  { id: 'location-replace', html: `<p>navigating</p>`, js: `window.location.replace("/dest.html");`, trigger: 'script' },
  { id: 'redirect', html: `<p>navigating</p>`, js: `window.location.href = "/redirect";`, trigger: 'script' },
  // Boundaries that still hold.
  { id: 'href-top', html: `<a id="go" href="/dest.html" target="_top">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'href-blank', html: `<a id="go" href="/dest.html" target="_blank">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'window-open', html: `<p>opening</p>`, js: `window.open("/dest.html", "_blank");`, trigger: 'script' },
  { id: 'form-submit', html: `<form id="f" action="/dest.html" method="get"><input name="x" value="1"><button type="submit">go</button></form>`, js: `document.getElementById("f").submit();`, trigger: 'script' },
  { id: 'direct-fetch', html: `<p>fetching</p>`, js: `fetch("/beacon?from=direct-fetch").catch(function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  { id: 'image-request', html: `<img id="pic" src="/beacon?from=image-request">`, js: `document.getElementById("pic").addEventListener("error", function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  { id: 'relative-resource', html: `<script src="/asset.js"></script><img id="pic" src="/beacon?from=relative-resource">`, js: `document.getElementById("pic").addEventListener("error", function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  // Bridge authorization.
  { id: 'bridge-wrong-session', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: "not-the-session", action: "send_prompt", payload: { text: "forged" } }, "*");`, trigger: 'script' },
  { id: 'bridge-valid-session', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: ${JSON.stringify(SESSION)}, action: "send_prompt", payload: { text: "hello" } }, "*");`, trigger: 'script' },
  { id: 'bridge-unknown-action', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: ${JSON.stringify(SESSION)}, action: "install_everything", payload: {} }, "*");`, trigger: 'script' },
];

/** Escape a value for use inside a double-quoted HTML attribute. */
function escapeAttribute(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

/**
 * Build the host document for one case.
 *
 * The generated frame document comes from the production
 * `buildSandboxDocument()`, and is embedded in the iframe's `srcdoc`
 * attribute. The attribute value is escaped so the generated HTML is not
 * corrupted; the browser decodes it back to the original document.
 *
 * Replacements use function form, so a `$&` or similar sequence inside the
 * generated document cannot be interpreted as a replacement pattern.
 */
export function buildHostDocument(caseId: string): string {
  const spec = CASES.find((candidate) => candidate.id === caseId);
  if (!spec) throw new Error(`unknown case: ${caseId}`);
  const artifact: SandboxUiArtifact = {
    version: 1,
    kind: 'sandbox',
    title: spec.id,
    html: spec.html,
    js: spec.js,
  };
  const document = buildSandboxDocument(artifact, SESSION);
  return HOST_HTML.replace('__SESSION__', () => JSON.stringify(SESSION)).replace(
    '__FRAME_DOC__',
    () => escapeAttribute(document),
  );
}

export function createFixtureServer(): Promise<{ server: http.Server; port: number }> {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1');
    const path = url.pathname + url.search;
    allRequests.push(path);

    if (url.pathname === '/host.html') {
      let html: string;
      try {
        html = buildHostDocument(url.searchParams.get('case') ?? '');
      } catch {
        res.writeHead(404, { 'content-type': 'text/plain' });
        res.end('no such case');
        return;
      }
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      res.end(html);
      return;
    }

    if (url.pathname === '/dest.html') {
      received.push(path);
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      res.end(DEST_HTML);
      return;
    }

    if (url.pathname === '/redirect') {
      received.push(path);
      res.writeHead(302, { location: '/dest.html', 'cache-control': 'no-store' });
      res.end();
      return;
    }

    if (url.pathname === '/asset.js') {
      received.push(path);
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'no-store' });
      res.end('window.__assetLoaded = true;');
      return;
    }

    if (url.pathname === '/beacon') {
      received.push(path);
      // Permissive CORS on purpose, so that only CSP can block a fetch.
      res.writeHead(204, {
        'access-control-allow-origin': '*',
        'access-control-allow-credentials': 'false',
        'cache-control': 'no-store',
      });
      res.end();
      return;
    }

    if (url.pathname === '/__mark') {
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ evidence: received.length, all: allRequests.length }));
      return;
    }

    if (url.pathname === '/__log') {
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify(received));
      return;
    }

    if (url.pathname === '/__all') {
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify(allRequests));
      return;
    }

    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('not found');
  });

  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      resolve({ server, port: (server.address() as AddressInfo).port });
    });
  });
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

let server: http.Server;
let port: number;

test.beforeAll(async () => {
  const started = await createFixtureServer();
  server = started.server;
  port = started.port;
});

test.afterAll(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

type Observation = {
  id: string;
  /** Paths the fixture server actually received during this case. */
  reached: string[];
  /** Requests the browser attempted, with the failure text when they failed. */
  attempted: { url: string; failure: string | null }[];
  /** Bridge actions the host accepted after full validation. */
  bridgeAccepted: string[];
  /** Every bridge message the host received, before any validation. */
  bridgeMessages: { origin: string; sourceIsActiveFrame: boolean; action: string | null }[];
  /** Whether the top-level page navigated away from the host. */
  parentNavigated: boolean;
  /** Whether a popup window was created. */
  popupCreated: boolean;
};

async function runCase(browser: Browser, spec: CaseSpec): Promise<Observation> {
  const context: BrowserContext = await browser.newContext();
  const page: Page = await context.newPage();

  const attempted: { url: string; failure: string | null }[] = [];
  const failures = new Map<string, string>();
  let popupCreated = false;

  page.on('request', (request) => {
    attempted.push({ url: request.url(), failure: null });
  });
  page.on('requestfailed', (request) => {
    failures.set(request.url(), request.failure()?.errorText ?? 'unknown');
    const entry = attempted.find((item) => item.url === request.url());
    if (entry) entry.failure = failures.get(request.url()) ?? null;
  });
  context.on('page', () => {
    popupCreated = true;
  });

  // The evidence log is captured across the whole navigation, so the mark is
  // taken before the host page is requested. A same-frame navigation happens
  // while the frame loads, and it must be inside the slice.
  const mark = await page.request.get(`http://127.0.0.1:${port}/__mark`);
  const before = (await mark.json()) as { evidence: number; all: number };
  const beforeUrl = page.url();

  await page.goto(`http://127.0.0.1:${port}/host.html?case=${encodeURIComponent(spec.id)}`);

  // Readiness must not read the sandboxed document through the host's
  // same-origin API: the frame is sandboxed without allow-same-origin, so
  // `frame.contentDocument` is null by design. A frame locator addresses the
  // frame through the browser instead, so the sandbox is not weakened.
  await page.frameLocator('#gen-ui').locator('body').waitFor({ state: 'attached', timeout: 20000 });

  if (spec.trigger === 'click') {
    // A real trusted input event, dispatched at the element inside the frame.
    await page.frameLocator('#gen-ui').locator('#go').click({ timeout: 15000 });
  }

  await page.waitForTimeout(1500);

  const afterMark = await page.request.get(`http://127.0.0.1:${port}/__mark`);
  const after = (await afterMark.json()) as { evidence: number; all: number };
  const logResponse = await page.request.get(`http://127.0.0.1:${port}/__log`);
  const log = (await logResponse.json()) as string[];
  const reached = log.slice(before.evidence, after.evidence);

  const bridgeAccepted = await page.evaluate(
    () => (window as unknown as { __accepted?: string[] }).__accepted ?? [],
  );
  const bridgeMessages = await page.evaluate(
    () => (window as unknown as { __messages?: { origin: string; sourceIsActiveFrame: boolean; action: string | null }[] }).__messages ?? [],
  );

  const observation: Observation = {
    id: spec.id,
    reached,
    attempted,
    bridgeAccepted,
    bridgeMessages,
    parentNavigated: page.url() !== beforeUrl,
    popupCreated,
  };

  await context.close();
  return observation;
}

function specFor(id: string): CaseSpec {
  const spec = CASES.find((candidate) => candidate.id === id);
  if (!spec) throw new Error(`unknown case: ${id}`);
  return spec;
}

// ---------------------------------------------------------------------------
// Liveness
// ---------------------------------------------------------------------------

test.describe('harness liveness', () => {
  // This test is deliberately NOT marked test.fail(). A browser that cannot
  // launch must fail the suite loudly rather than being counted as an
  // expected security failure.
  test('the browser, fixture server, host document, production frame, CSP, and generated JavaScript are all live', async ({ browser, page }) => {
    // The fixture server is running.
    const mark = await page.request.get(`http://127.0.0.1:${port}/__mark`);
    expect(mark.status()).toBe(200);

    // The host document loads.
    const response = await page.goto(`http://127.0.0.1:${port}/host.html?case=liveness`);
    expect(response?.status()).toBe(200);

    // Exactly one generated iframe, sandboxed exactly as shipped.
    await expect(page.locator('#gen-ui')).toHaveCount(1);
    await expect(page.locator('#gen-ui')).toHaveAttribute('sandbox', 'allow-scripts');

    // The production-generated document loaded, and its JavaScript ran. The
    // marker is inside the frame, so this is observed through the browser,
    // not through the host's same-origin API.
    await expect(
      page.frameLocator('#gen-ui').locator('#exec-marker[data-executed="yes"]'),
    ).toBeVisible({ timeout: 20000 });

    // The shipped CSP is present on the generated document.
    const csp = await page
      .frameLocator('#gen-ui')
      .locator('meta[http-equiv="Content-Security-Policy"]')
      .getAttribute('content');
    expect(csp).toContain("default-src 'none'");
    expect(csp).toContain("connect-src 'none'");
    expect(csp).toContain("form-action 'none'");

    // The fixture server records requests.
    const all = await page.request.get(`http://127.0.0.1:${port}/__all`);
    const allPaths = (await all.json()) as string[];
    expect(allPaths.some((path) => path.startsWith('/host.html'))).toBe(true);
  });

  test('the served host document contains the generated frame and no unresolved placeholder', async ({ page }) => {
    const response = await page.goto(`http://127.0.0.1:${port}/host.html?case=liveness`);
    const html = (await response?.text()) ?? '';
    expect(html).toContain('sandbox="allow-scripts"');
    expect(html).not.toContain('__FRAME_DOC__');
    expect(html).not.toContain('__SESSION__');
  });
});

// ---------------------------------------------------------------------------
// The known exploit — reproduction baseline
// ---------------------------------------------------------------------------

test.describe('known exploit reproduction (a pass means the exploit reproduced, NOT that the boundary held)', () => {
  for (const id of ['plain-href', 'location-assign', 'location-replace', 'redirect', 'user-initiated']) {
    test(`REPRODUCES the exploit: ${id} navigates the frame and the replacement document beacons out`, async ({ browser }) => {
      const result = await runCase(browser, specFor(id));

      // The same-frame navigation reached the fixture.
      expect(result.reached.some((path) => path.startsWith('/dest.html'))).toBe(true);

      // The replacement document's outbound request reached the fixture. The
      // beacon answers with permissive CORS, so only CSP could have blocked
      // it, and the request was received.
      expect(result.reached.some((path) => path.includes('from=dest-fetch'))).toBe(true);

      // The replacement document's own report confirms the fetch succeeded.
      const report = result.reached.find((path) => path.includes('dest='));
      expect(report).toBeDefined();
      expect(decodeURIComponent(report ?? '')).toContain('fetchReached=true');
    });
  }

  test('REPRODUCES the exploit: after the navigation the frame keeps its opaque origin and loses only the CSP', async ({ browser }) => {
    const result = await runCase(browser, specFor('plain-href'));
    const report = decodeURIComponent(result.reached.find((path) => path.includes('dest=')) ?? '');
    // The replacement document executed, and the sandbox still holds.
    expect(report).toContain('scriptRan=true');
    expect(report).toContain('cookie=THREW');
    expect(report).toContain('storageWorks=false');
    expect(report).toContain('parentReadable=false');
    // What it does not hold is the document CSP.
    expect(report).toContain('fetchReached=true');
  });
});

// ---------------------------------------------------------------------------
// Boundaries that still hold — these must keep passing
// ---------------------------------------------------------------------------

test.describe('security regressions (boundaries that still hold)', () => {
  test('the parent frame cannot be navigated', async ({ browser }) => {
    const result = await runCase(browser, specFor('href-top'));
    expect(result.parentNavigated).toBe(false);
    expect(result.reached).toEqual([]);
  });

  test('no popup can be created by a link', async ({ browser }) => {
    const result = await runCase(browser, specFor('href-blank'));
    expect(result.popupCreated).toBe(false);
    expect(result.reached).toEqual([]);
  });

  test('no popup can be created by window.open', async ({ browser }) => {
    const result = await runCase(browser, specFor('window-open'));
    expect(result.popupCreated).toBe(false);
    expect(result.reached).toEqual([]);
  });

  test('a local form submission is blocked', async ({ browser }) => {
    const result = await runCase(browser, specFor('form-submit'));
    expect(result.reached).toEqual([]);
  });

  test("the original document's own fetch is blocked before it leaves the browser", async ({ browser }) => {
    const result = await runCase(browser, specFor('direct-fetch'));
    expect(result.reached).toEqual([]);
  });

  test("the original document's own image load is blocked", async ({ browser }) => {
    const result = await runCase(browser, specFor('image-request'));
    expect(result.reached).toEqual([]);
  });

  test('a relative resource declaration does not load', async ({ browser }) => {
    // E4 classifies relative declarations as self-contained. The frame ships
    // no resource package, and the frame CSP denies the load, so a relative
    // dependency is self-contained in name only.
    const result = await runCase(browser, specFor('relative-resource'));
    expect(result.reached).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Bridge authorization
// ---------------------------------------------------------------------------

test.describe('bridge authorization', () => {
  test('a message with the wrong session is rejected', async ({ browser }) => {
    const result = await runCase(browser, specFor('bridge-wrong-session'));
    expect(result.bridgeMessages.some((message) => message.action === 'send_prompt')).toBe(true);
    expect(result.bridgeAccepted).not.toContain('send_prompt');
  });

  test('a message with the correct session is accepted', async ({ browser }) => {
    const result = await runCase(browser, specFor('bridge-valid-session'));
    expect(result.bridgeAccepted).toContain('send_prompt');
  });

  test('an unknown action is ignored and never partially applied', async ({ browser }) => {
    const result = await runCase(browser, specFor('bridge-unknown-action'));
    expect(result.bridgeMessages.some((message) => message.action === 'install_everything')).toBe(true);
    expect(result.bridgeAccepted).not.toContain('install_everything');
    // Only the frame's own resize is accepted.
    expect(result.bridgeAccepted).toEqual(['resize']);
  });

  test('every bridge message arrives from the opaque origin', async ({ browser }) => {
    const result = await runCase(browser, specFor('bridge-valid-session'));
    expect(result.bridgeMessages.length).toBeGreaterThan(0);
    for (const message of result.bridgeMessages) {
      expect(message.origin).toBe('null');
      expect(message.sourceIsActiveFrame).toBe(true);
    }
  });
});
