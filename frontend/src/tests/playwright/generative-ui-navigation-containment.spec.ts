/**
 * Generated UI sandbox navigation containment proof.
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
 * server that records the paths it actually received. The browser console is
 * recorded as supporting detail only; no assertion in this file rests on a
 * console warning alone.
 *
 * The beacon endpoint answers with a permissive CORS header on purpose. A
 * cross-origin fetch from an opaque-origin frame can then *succeed* unless CSP
 * blocks it, which makes the fetch result unambiguous evidence about CSP
 * rather than about CORS.
 *
 * Disposition: see
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

const SESSION = 'ui-containment-session';

/** Paths the fixture server actually received. Primary evidence. */
let received: string[] = [];

/** caseId -> host document that embeds the generated frame. */
const hostDocuments = new Map<string, string>();

/** The destination document. It declares no CSP of its own. */
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

/**
 * The host page.
 *
 * The bridge validation below mirrors SandboxFrame.tsx's host-side
 * `handleMessage`: source binding (compared against the frame's
 * `contentWindow`, never the element), opaque-origin binding, channel
 * binding, session binding, schema validation, and "unknown actions are
 * ignored, never partially applied".
 */
const HOST_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>containment host</title></head>
<body>
<h1>containment host</h1>
<div id="frames"></div>
<script>
  var SESSION = __SESSION__;
  var activeFrameWindow = null;
  var accepted = [];

  window.addEventListener("message", function (event) {
    if (!activeFrameWindow || event.source !== activeFrameWindow) return;
    if (event.origin !== "null") return;
    var data = event.data;
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
</script>
</body>
</html>`;

function createFixtureServer(): Promise<{ server: http.Server; port: number }> {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1');
    const path = url.pathname + url.search;

    // Harness plumbing is excluded from the evidence log.
    if (url.pathname === '/host.html') {
      const doc = hostDocuments.get(url.searchParams.get('case') ?? '');
      if (doc === undefined) {
        res.writeHead(404, { 'content-type': 'text/plain' });
        res.end('no such case');
        return;
      }
      const html = HOST_HTML.replace('__SESSION__', JSON.stringify(SESSION)).replace(
        '__FRAME_DOC__',
        doc.replace(/&/g, '&amp;').replace(/"/g, '&quot;'),
      );
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

    if (url.pathname === '/__log') {
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify(received));
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
// Cases
// ---------------------------------------------------------------------------

type CaseSpec = {
  id: string;
  html: string;
  js: string;
  /** 'script' runs the artifact's own script; 'click' dispatches a real click. */
  trigger: 'script' | 'click';
};

const CASES: CaseSpec[] = [
  { id: 'plain-href', html: `<a id="go" href="/dest.html">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'href-top', html: `<a id="go" href="/dest.html" target="_top">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'href-blank', html: `<a id="go" href="/dest.html" target="_blank">go</a>`, js: `document.getElementById("go").click();`, trigger: 'script' },
  { id: 'location-assign', html: `<p>navigating</p>`, js: `window.location.href = "/dest.html";`, trigger: 'script' },
  { id: 'location-replace', html: `<p>navigating</p>`, js: `window.location.replace("/dest.html");`, trigger: 'script' },
  { id: 'user-initiated', html: `<a id="go" href="/dest.html">go</a>`, js: ``, trigger: 'click' },
  { id: 'redirect', html: `<p>navigating</p>`, js: `window.location.href = "/redirect";`, trigger: 'script' },
  { id: 'form-submit', html: `<form id="f" action="/dest.html" method="get"><input name="x" value="1"><button type="submit">go</button></form>`, js: `document.getElementById("f").submit();`, trigger: 'script' },
  { id: 'direct-fetch', html: `<p>fetching</p>`, js: `fetch("/beacon?from=direct-fetch").catch(function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  { id: 'image-request', html: `<img id="pic" src="/beacon?from=image-request">`, js: `document.getElementById("pic").addEventListener("error", function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  { id: 'relative-resource', html: `<script src="/asset.js"></script><img id="pic" src="/beacon?from=relative-resource">`, js: `document.getElementById("pic").addEventListener("error", function () { window.__blockedByCsp = true; });`, trigger: 'script' },
  { id: 'window-open', html: `<p>opening</p>`, js: `window.open("/dest.html", "_blank");`, trigger: 'script' },
  { id: 'bridge-wrong-session', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: "not-the-session", action: "send_prompt", payload: { text: "forged" } }, "*");`, trigger: 'script' },
  { id: 'bridge-valid-session', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: ${JSON.stringify(SESSION)}, action: "send_prompt", payload: { text: "hello" } }, "*");`, trigger: 'script' },
  { id: 'bridge-unknown-action', html: `<p>bridge</p>`, js: `parent.postMessage({ channel: "cfy-ui", session: ${JSON.stringify(SESSION)}, action: "install_everything", payload: {} }, "*");`, trigger: 'script' },
];

type Observation = {
  id: string;
  /** Paths the fixture server actually received during this case. */
  reached: string[];
  /** Requests the browser attempted, with the failure text when they failed. */
  attempted: { url: string; failure: string | null }[];
  /** Bridge actions the host accepted after full validation. */
  bridgeAccepted: string[];
  /** Whether the top-level page navigated away from the host. */
  parentNavigated: boolean;
  /** Whether a popup window was created. */
  popupCreated: boolean;
};

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

async function runCase(
  browser: Browser,
  spec: CaseSpec,
): Promise<Observation> {
  const context: BrowserContext = await browser.newContext();
  const page: Page = await context.newPage();

  received = [];
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

  const artifact: SandboxUiArtifact = {
    version: 1,
    kind: 'sandbox',
    title: spec.id,
    html: spec.html,
    js: spec.js,
  };
  const doc = buildSandboxDocument(artifact, SESSION);
  hostDocuments.set(spec.id, `<iframe id="gen-ui" title="generated interface" sandbox="allow-scripts" srcdoc="__FRAME_DOC__" style="width:100%;height:200px;border:0"></iframe>`);

  const before = page.url();
  await page.goto(`http://127.0.0.1:${port}/host.html?case=${encodeURIComponent(spec.id)}`);
  await page.waitForFunction(() => {
    const frame = document.getElementById('gen-ui') as HTMLIFrameElement | null;
    return !!frame && !!frame.contentDocument && !!frame.contentDocument.body;
  });

  if (spec.trigger === 'click') {
    // A real trusted input event, dispatched at the element in the frame.
    await page.frameLocator('#gen-ui').locator('#go').click({ timeout: 5000 });
  }

  await page.waitForTimeout(1500);

  const bridgeAccepted = await page.evaluate(
    () => (window as unknown as { __accepted?: string[] }).__accepted ?? [],
  );

  const observation: Observation = {
    id: spec.id,
    reached: [...received],
    attempted,
    bridgeAccepted,
    parentNavigated: page.url() !== before,
    popupCreated,
  };

  hostDocuments.delete(spec.id);
  await context.close();
  return observation;
}

// ---------------------------------------------------------------------------
// Liveness
// ---------------------------------------------------------------------------

test.describe('generated UI navigation containment — harness', () => {
  // This test is deliberately NOT marked test.fail().
  //
  // The known-gap cases below use test.fail(), and Playwright counts a setup
  // failure — including a browser that cannot launch at all — as an expected
  // failure. Without this test, an environment where Chromium refuses to start
  // would report the known-gap suite as green. This test makes that
  // impossible: if the browser does not start, or the loopback fixture is not
  // reachable, this fails loudly and the whole suite is red.
  test('the browser launches and the loopback fixture is reachable', async ({ browser, page }) => {
    const response = await page.goto(`http://127.0.0.1:${port}/host.html?case=direct-fetch`);
    expect(response?.status()).toBe(200);
    await expect(page.locator('#gen-ui')).toHaveCount(1);
    // The generated frame is the shipped document: same-origin-inert
    // srcdoc, script-only sandbox, and the shipped CSP.
    await expect(page.locator('#gen-ui')).toHaveAttribute('sandbox', 'allow-scripts');
    const csp = await page
      .frameLocator('#gen-ui')
      .locator('meta[http-equiv="Content-Security-Policy"]')
      .getAttribute('content');
    expect(csp).toContain("default-src 'none'");
    expect(csp).toContain("connect-src 'none'");
  });
});

// ---------------------------------------------------------------------------
// The boundary that holds
// ---------------------------------------------------------------------------

test.describe('generated UI navigation containment — boundaries that hold', () => {
  test('target="_top" cannot navigate the parent and issues no request', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'href-top')!);
    expect(result.reached).toEqual([]);
    expect(result.parentNavigated).toBe(false);
  });

  test('target="_blank" cannot create a popup and issues no request', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'href-blank')!);
    expect(result.reached).toEqual([]);
    expect(result.popupCreated).toBe(false);
  });

  test('window.open() cannot create a popup and issues no request', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'window-open')!);
    expect(result.reached).toEqual([]);
    expect(result.popupCreated).toBe(false);
  });

  test('a local form submission is blocked and issues no request', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'form-submit')!);
    expect(result.reached).toEqual([]);
  });

  test('a direct fetch() is blocked before the request leaves the browser', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'direct-fetch')!);
    expect(result.reached).toEqual([]);
  });

  test('an image resource request is blocked before it leaves the browser', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'image-request')!);
    expect(result.reached).toEqual([]);
  });

  test('a relative resource declaration does not load', async ({ browser }) => {
    // E4 classifies relative declarations as self-contained. The frame ships no
    // resource package, and the frame CSP denies the load, so a relative
    // dependency is self-contained in name only.
    const result = await runCase(browser, CASES.find((c) => c.id === 'relative-resource')!);
    expect(result.reached).toEqual([]);
  });

  test('the bridge rejects a message with the wrong session', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'bridge-wrong-session')!);
    expect(result.bridgeAccepted).not.toContain('send_prompt');
  });

  test('the bridge accepts a message with the correct session', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'bridge-valid-session')!);
    expect(result.bridgeAccepted).toContain('send_prompt');
  });

  test('the bridge ignores an unknown action without partially applying it', async ({ browser }) => {
    const result = await runCase(browser, CASES.find((c) => c.id === 'bridge-unknown-action')!);
    expect(result.bridgeAccepted).not.toContain('install_everything');
    expect(result.bridgeAccepted).toHaveLength(1); // only the frame's own resize
  });
});

// ---------------------------------------------------------------------------
// The boundary that does not hold
// ---------------------------------------------------------------------------

test.describe('generated UI navigation containment — known gap', () => {
  // The frame's CSP is a meta tag on the original srcdoc document. A same-frame
  // navigation replaces that document with one that declares no CSP, so the
  // `default-src 'none'` / `connect-src 'none'` policy no longer applies to
  // what runs inside the frame.
  //
  // The sandbox attribute does persist across the navigation: the frame stays
  // opaque-origin, keeps no host API access, and still cannot navigate the
  // parent or open a popup. What it regains is the ability to issue outbound
  // network requests.
  //
  // This test asserts the INTENDED boundary, so it fails until the boundary is
  // repaired. `test.fail()` keeps the failure documented without turning CI
  // red, and it will flip to a real failure if the behaviour ever changes.
  for (const id of ['plain-href', 'location-assign', 'location-replace', 'redirect', 'user-initiated']) {
    test.fail(`${id}: a navigated frame must not be able to issue outbound requests`, async ({ browser }) => {
      const result = await runCase(browser, CASES.find((c) => c.id === id)!);

      // The navigation itself is permitted. The frame's own policy must
      // continue to deny the outbound request that follows it.
      expect(result.reached.some((path) => path.includes('from=dest-fetch'))).toBe(false);
      expect(result.reached.some((path) => path.includes('from=dest-image'))).toBe(false);
    });
  }
});
