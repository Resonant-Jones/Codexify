const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");

const htmlPath = path.join(__dirname, "rc-atlas-prototype.html");
const modulesPath = path.join(__dirname, "..", "docs", "architecture", "modules-and-ownership.md");
const html = fs.readFileSync(htmlPath, "utf8");
const modulesSource = fs.readFileSync(modulesPath, "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(match => match[1]);
const modelMatch = html.match(/<script\s+data-atlas-model>([\s\S]*?)<\/script>/i);

assert.ok(modelMatch, "prototype exposes the pure Atlas model script");
const context = { console };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(modelMatch[1], context, { filename: "rc-atlas-model.js" });
const M = context.AtlasModel;
const plain = value => JSON.parse(JSON.stringify(value));

function parseSubsystemMatrix(markdown) {
  const lines = markdown.split(/\r?\n/);
  const start = lines.findIndex(line => line.trim() === "## Subsystem Matrix");
  assert.notEqual(start, -1, "maintained source contains Subsystem Matrix");
  const rows = [];
  for (const line of lines.slice(start + 1)) {
    if (/^##\s/.test(line)) break;
    if (!line.startsWith("|") || /^\|[-\s|]+\|$/.test(line)) continue;
    const cells = line.split("|").slice(1, -1).map(cell => cell.trim());
    if (cells[0] === "Subsystem") continue;
    const anchors = [...cells[3].matchAll(new RegExp("\\x60([^\\x60]+)\\x60", "g"))].map(match => match[1]);
    rows.push({
      name: cells[0],
      moduleClass: cells[1],
      responsibilities: cells[2],
      anchors,
      dependsOn: cells[4],
      dependedOnBy: cells[5],
      blastRadius: cells[6],
    });
  }
  return rows;
}

const matrixRows = parseSubsystemMatrix(modulesSource);
const matrixByName = new Map(matrixRows.map(row => [row.name, row]));

test("all executable inline JavaScript has valid syntax", () => {
  assert.ok(scripts.length >= 2);
  scripts.forEach((source, index) => assert.doesNotThrow(() => new vm.Script(source, { filename: "inline-" + index + ".js" })));
});

test("source projection represents every Subsystem Matrix row exactly once", () => {
  assert.equal(matrixRows.length, 20);
  assert.equal(M.data.entities.length, matrixRows.length);
  const sourceNames = matrixRows.map(row => row.name).sort();
  const atlasNames = M.data.entities.map(item => item.name).sort();
  assert.deepEqual(plain(atlasNames), sourceNames);
  assert.equal(new Set(atlasNames).size, atlasNames.length);
});

test("projected classes, responsibilities, dependency text, and blast radius match the maintained matrix", () => {
  for (const item of M.data.entities) {
    const row = matrixByName.get(item.name);
    assert.ok(row, "source row exists for " + item.name);
    assert.equal(item.moduleClass, row.moduleClass);
    assert.equal(item.responsibilities, row.responsibilities);
    assert.equal(item.dependsOn, row.dependsOn);
    assert.equal(item.dependedOnBy, row.dependedOnBy);
    assert.equal(item.blastRadius, row.blastRadius);
  }
});

test("every Key code anchor originates from its documented subsystem row", () => {
  for (const item of M.data.entities) {
    const row = matrixByName.get(item.name);
    assert.deepEqual(plain(item.anchors), row.anchors, "anchors match " + item.name);
  }
  assert.match(html, />Key code anchors</);
  assert.doesNotMatch(html, /Files contained in this module/i);
  assert.doesNotMatch(html, /exhaustive module membership/i);
});

test("documentation-backed modules carry bounded real-source provenance", () => {
  assert.equal(M.data.inspectedCommit, "cb551de1866715ef421026203ffe2a87cec8aaca");
  for (const item of M.data.entities) {
    assert.equal(item.kind, "module");
    assert.equal(item.source.path, "docs/architecture/modules-and-ownership.md");
    assert.equal(item.source.classification, "authoritative_now");
    assert.equal(item.source.section, "Subsystem Matrix");
    assert.equal(item.source.authority, "documentation_snapshot");
    assert.equal(item.source.commit, M.data.inspectedCommit);
    assert.equal("synthetic" in item, false);
  }
});

test("module category vocabulary comes directly from the source and is written on cards", () => {
  const sourceClasses = [...new Set(matrixRows.map(row => row.moduleClass))].sort();
  assert.deepEqual(plain([...M.data.moduleClasses].sort()), sourceClasses);
  assert.deepEqual(sourceClasses, ["core loop", "experimental", "retired", "supporting"]);
  const graphRenderer = html.match(/function renderGraph\(\)[\s\S]*?function renderRoutes\(\)/)?.[0] || "";
  assert.match(graphRenderer, /class="module-category"/);
  assert.match(graphRenderer, /classLabel\(item\.moduleClass\)/);
  assert.match(html, /\.entity-card\.category-core-loop/);
  assert.match(html, /\.entity-card\.category-retired/);
});

test("relationships resolve to valid modules and use the bounded registry", () => {
  assert.deepEqual(plain(M.data.relationshipTypes), ["dependency", "runtime_flow"]);
  const ids = new Set(M.data.entities.map(item => item.id));
  for (const rel of M.data.relationships) {
    assert.ok(ids.has(rel.from), "valid source for " + rel.id);
    assert.ok(ids.has(rel.to), "valid target for " + rel.id);
    assert.ok(M.data.relationshipTypes.includes(rel.kind));
  }
  assert.deepEqual(plain(M.validate()), []);
});

test("every relationship carries source metadata and normalization posture", () => {
  for (const rel of M.data.relationships) {
    assert.ok(rel.explanation);
    assert.ok(rel.source.path.startsWith("docs/architecture/"));
    assert.equal(rel.source.classification, "authoritative_now");
    assert.equal(rel.source.commit, M.data.inspectedCommit);
    assert.ok(rel.source.section);
    assert.ok(["direct_documented", "bounded_normalization"].includes(rel.source.evidenceType));
    assert.ok(rel.source.normalization);
    assert.ok(rel.caution);
  }
  const runtimeEdges = M.data.relationships.filter(rel => rel.kind === "runtime_flow");
  assert.ok(runtimeEdges.length >= 2);
  assert.ok(runtimeEdges.every(rel => rel.source.path === "docs/architecture/flows.md"));
});

test("node and edge meaning is not encoded by color alone", () => {
  assert.match(html, /Core loop/);
  assert.match(html, /Dependency — A depends on B/);
  assert.match(html, /Runtime flow — documented transition/);
  assert.match(html, /rel\.label/);
  assert.match(html, /marker-end/);
  assert.match(html, /\.routes path\.dependency\s*\{[^}]*stroke:/);
  assert.match(html, /\.routes path\.runtime_flow\s*\{[^}]*stroke:[^}]*stroke-dasharray:/);
  assert.match(html, /<dt>Type<\/dt>/);
  assert.match(html, /<dt>Source module<\/dt>/);
  assert.match(html, /<dt>Target module<\/dt>/);
});

test("external dependencies remain inspector details rather than invented module nodes", () => {
  const names = new Set(M.data.entities.map(item => item.name.toLowerCase()));
  for (const external of ["redis", "postgres", "browser storage", "provider credentials", "external network", "environment configuration"]) {
    assert.equal(names.has(external), false, external + " is not a module node");
  }
  assert.ok(M.data.entities.some(item => item.dependsOn.includes("Redis")));
  assert.ok(M.data.entities.some(item => item.dependsOn.includes("Postgres")));
  assert.match(html, /<dt>Depends on<\/dt>/);
});

test("synthetic Galaxy remains clearly outside the documentation-backed local dataset", () => {
  assert.ok(M.data.entities.every(item => item.source.authority === "documentation_snapshot"));
  assert.match(html, /optional synthetic discovery sketch/);
  assert.match(html, /synthetic federation context/);
  assert.match(html, /Illustrative discovery · synthetic sectors · no live availability/);
  assert.doesNotMatch(modelMatch[1], /Open-source makers|Creative technology guild/);
});

test("Directory is flat, searchable, and exactly mirrors graph modules", () => {
  assert.deepEqual(plain(M.graphIds()), plain(M.listIds()));
  assert.equal(M.graphIds().length, 20);
  const renderer = html.match(/function renderDirectory\(\)[\s\S]*?function renderSources\(\)/)?.[0] || "";
  assert.match(renderer, /D\.entities\.filter\(matches\)/);
  assert.match(renderer, /class="directory-list"/);
  assert.match(renderer, /Key code anchors/);
  assert.doesNotMatch(renderer, /parentId|childrenOf|tree-level|--depth/);
});

test("search includes module names, responsibilities, dependency text, and anchors", () => {
  const searchFunction = html.match(/function searchableText\(item\)[\s\S]*?function matches\(item\)/)?.[0] || "";
  assert.match(searchFunction, /item\.name/);
  assert.match(searchFunction, /item\.responsibilities/);
  assert.match(searchFunction, /item\.dependsOn/);
  assert.match(searchFunction, /item\.anchors/);
  assert.match(html, /No modules match/);
});

test("module and edge selection update the contextual inspector", () => {
  assert.match(html, /const nav = event\.target\.closest\("\[data-navigate\]"\)/);
  assert.match(html, /navigateTo\(nav\.dataset\.navigate\)/);
  assert.match(html, /const edgeRow = event\.target\.closest\("\[data-edge-id\]"\)/);
  assert.match(html, /selectEdge\(edgeRow\.dataset\.edgeId\)/);
  assert.match(html, /function renderInspector\(\)/);
  assert.match(html, /<dt>Blast radius<\/dt>/);
  assert.match(html, /<dt>Source commit<\/dt>/);
});

test("compact Legend is optional, dismissible, and not a sidebar", () => {
  assert.match(html, /id="legendPanel"[^>]*hidden/);
  assert.match(html, /id="legendButton"[^>]*aria-controls="legendPanel"/);
  assert.match(html, /id="closeLegend"/);
  assert.match(html, /function toggleLegend\(force\)/);
  assert.doesNotMatch(html, /legend-sidebar|permanent-legend/i);
});

test("persistent hierarchy rail and hierarchy-only controls remain absent", () => {
  assert.doesNotMatch(html, /<aside[^>]+class=["'][^"']*sidebar/i);
  assert.doesNotMatch(html, /\b(?:sidebarTree|renderSidebar|tree-level|tree-row|mini-hierarchy|hamburger|drawer)\b/i);
  assert.doesNotMatch(html, /parentId|childrenOf|ancestorsOf|projectedResourceIds/);
  assert.match(html, /\.app\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) var\(--inspector-width\)/);
});

test("desktop inspector width preserves the former 350px column and a usable Atlas floor", () => {
  assert.equal(M.defaultPresentation(1070, 860).inspectorWidth, 350);
  assert.deepEqual(plain(M.inspectorBounds(1680)), { min: 350, max: 960 });
  assert.deepEqual(plain(M.inspectorBounds(1440)), { min: 350, max: 742 });
  assert.equal(M.clampInspectorWidth(120, 1440), 350);
  assert.equal(M.clampInspectorWidth(600, 1440), 600);
  assert.equal(M.clampInspectorWidth(1200, 1440), 742);
  assert.equal(M.clampInspectorWidth("malformed", 1680), 350);
  assert.match(html, /--inspector-min-width:\s*350px/);
  assert.match(html, /@media \(max-width: 1120px\)[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) 294px/);
});

test("inspector resize handle supports bounded pointer, keyboard, cancellation, and reset", () => {
  assert.match(html, /id="inspectorResizeHandle"[^>]*role="separator"[^>]*aria-orientation="vertical"[^>]*tabindex="0"/);
  assert.match(html, /setPointerCapture\(event\.pointerId\)/);
  assert.match(html, /"pointercancel", finishInspectorResize/);
  assert.match(html, /"lostpointercapture", finishInspectorResize/);
  assert.match(html, /event\.key === "ArrowLeft"/);
  assert.match(html, /event\.key === "ArrowRight"/);
  assert.match(html, /event\.key === "Home"/);
  assert.match(html, /"dblclick"/);
  assert.doesNotMatch(html.match(/function resizeInspector\(requested, persist\)[\s\S]*?(?=    function finishInspectorResize)/)[0], /viewport|navigation|query|selectedEdgeId|documentHistory/);
});

test("the clipped graph canvas cannot become a hidden keyboard scroll container", () => {
  assert.match(html, /\.canvas\s*\{[\s\S]*overflow:\s*hidden;\s*overflow:\s*clip;/);
});

test("initial and reset view use geometry-derived useful fit", () => {
  const positions = Object.fromEntries(M.data.entities.map(item => [item.id, { x: item.x, y: item.y }]));
  const desktop = M.fitViewport(1070, 860, positions);
  const wide = M.fitViewport(1600, 1000, positions);
  assert.ok(desktop.scale >= .4 && desktop.scale <= 1);
  assert.ok(wide.scale >= desktop.scale);
  assert.notDeepEqual(plain(desktop), plain(wide));
  assert.match(html, /M\.defaultPresentation\(els\.canvas\.clientWidth, els\.canvas\.clientHeight\)/);
});

test("presentation storage is bounded and malformed storage falls back safely", () => {
  const fallback = M.defaultPresentation(1070, 860);
  assert.deepEqual(plain(M.loadPresentation({ getItem() { return "{broken"; } }, 1070, 860, 1440)), plain(fallback));
  assert.deepEqual(plain(M.loadPresentation({ getItem() { throw new Error("blocked"); } }, 1070, 860, 1440)), plain(fallback));
  const stored = M.loadPresentation({ getItem() { return JSON.stringify({ viewport: { x: 12, y: 18, scale: 99 }, positions: { "completion-assembly-execution": { x: 77, y: 88 } }, inspectorWidth: 9999, authority: "ignored" }); } }, 1070, 860, 1440);
  assert.equal(stored.viewport.scale, 1.35);
  assert.equal(stored.inspectorWidth, 742);
  assert.deepEqual(plain(stored.positions["completion-assembly-execution"]), { x: 77, y: 88 });
  assert.equal("authority" in stored, false);
  const malformedWidth = M.loadPresentation({ getItem() { return JSON.stringify({ inspectorWidth: "wide" }); } }, 1070, 860, 1680);
  assert.equal(malformedWidth.inspectorWidth, 350);
});

test("navigation preserves history and invalid selections recover safely", () => {
  let nav = M.createNavigation("completion-assembly-execution");
  nav = M.navigate(nav, "context-retrieval-broker");
  nav = M.navigate(nav, "embedding-vector-indexing");
  assert.equal(nav.selectedId, "embedding-vector-indexing");
  nav = M.back(nav);
  assert.equal(nav.selectedId, "context-retrieval-broker");
  assert.equal(M.navigate(nav, "missing-module").selectedId, "completion-assembly-execution");
});

test("source reader return snapshots preserve valid origins and local context", () => {
  const navigation = { selectedId: "context-retrieval-broker", history: ["completion-assembly-execution"] };
  const viewport = { x: 47, y: -31, scale: .82 };
  for (const view of ["sources", "directory", "atlas"]) {
    const captured = M.createReaderReturn({ view, query: "provider", navigation, selectedEdgeId: "dep-completion-provider", viewport }, 318, 144);
    assert.equal(captured.view, view);
    assert.equal(captured.query, "provider");
    assert.deepEqual(plain(captured.navigation), navigation);
    assert.equal(captured.selectedEdgeId, "dep-completion-provider");
    assert.deepEqual(plain(captured.viewport), viewport);
    assert.equal(captured.scrollTop, 318);
    assert.equal(captured.pageScrollTop, 144);
  }

  const invalid = M.createReaderReturn({ view: "reader", query: "kept", navigation, viewport }, -12, -19);
  assert.equal(invalid.view, "atlas");
  assert.equal(invalid.query, "kept");
  assert.equal(invalid.scrollTop, 0);
  assert.equal(invalid.pageScrollTop, 0);
  assert.deepEqual(plain(M.createReaderReturn(null, 0, 0).navigation), plain(M.createNavigation()));
  assert.match(html, /state\.readerReturn = M\.createReaderReturn\(state, scroller \? scroller\.scrollTop : 0, window\.scrollY\)/);
  const close = html.match(/function closeReader\(\)[\s\S]*?(?=    function selectEdge)/)[0];
  assert.doesNotMatch(close, /setActiveView|renderAll|state\.viewport\s*=/);
  assert.doesNotMatch(html, /history\.back\s*\(/);
});

test("Sources exposes the complete governing document set", () => {
  const expected = [
    "docs/architecture/00-current-state.md",
    "docs/architecture/adr/adr-index.md",
    "docs/architecture/README.md",
    "docs/architecture/kb-validity-matrix.md",
    "docs/architecture/architecture-atlas.md",
    "docs/architecture/modules-and-ownership.md",
    "docs/architecture/system-overview.md",
    "docs/architecture/flows.md",
    "docs/architecture/data-and-storage.md",
  ].sort();
  assert.deepEqual(plain(M.data.sources.map(item => item.path).sort()), expected);
  assert.match(html, /data-view="sources"/);
  assert.match(html, /id="sourcesView"/);
  assert.match(html, /data-full-source-id/);
  assert.match(html, /Read source document/);
  assert.doesNotMatch(html, /Read full document|Read snapshot note/);
  assert.doesNotMatch(html, /<a class="button"[^>]+\.md/);
});

test("bounded Markdown rendering covers repository document syntax without raw HTML", () => {
  const rendered = M.renderMarkdown(`---
tags:
* architecture
aliases:
* ADR Index
---
# ADR **Index**

1. [[001-queue-model|ADR-001 Queue Model]]
2. [Current state](../00-current-state.md)

| Field | Meaning |
| --- | --- |
| Status | \`Accepted\` |

> Evidence is not authority.

\`\`\`js
const safe = true;
\`\`\`

<script>alert("no")</script>
[unsafe](javascript:alert(1))`);
  assert.match(rendered, /class="markdown-frontmatter"/);
  assert.match(rendered, /<dt>tags<\/dt><dd>architecture<\/dd>/);
  assert.match(rendered, /<h1 id="adr-index">ADR <strong>Index<\/strong><\/h1>/);
  assert.match(rendered, /<ol><li value="1"><a href="#" data-markdown-href="001-queue-model\.md">ADR-001 Queue Model<\/a><\/li>/);
  assert.match(rendered, /data-markdown-href="\.\.\/00-current-state\.md"/);
  assert.match(rendered, /class="markdown-table-wrap"/);
  assert.match(rendered, /<blockquote>/);
  assert.match(rendered, /<pre><code class="language-js">const safe = true;/);
  assert.match(rendered, /&lt;script&gt;alert\(&quot;no&quot;\)&lt;\/script&gt;/);
  assert.doesNotMatch(rendered, /<script>|javascript:/);
});

test("full-document loading supports offline sources and preserves original access", () => {
  const loader = html.match(/function repositoryRootUrl\(\)[\s\S]*?function closeReader\(\)/)?.[0] || "";
  assert.match(loader, /https\?\|file/);
  assert.match(loader, /url\.origin !== root\.origin/);
  assert.match(loader, /await fetch\(url\.href, \{ cache: "no-store" \}\)/);
  assert.match(loader, /Open original Markdown/);
  const encoded = html.match(/atob\("([A-Za-z0-9+/=]+)"\)/)[1];
  const bundle = JSON.parse(require("node:zlib").gunzipSync(Buffer.from(encoded, "base64")));
  for (const source of M.data.sources) assert.equal(bundle[source.path.toLowerCase()], fs.readFileSync(path.join(__dirname, "..", source.path), "utf8"));
  assert.match(bundle["docs/architecture/adr/001-queue-based-completion-acceptance-model.md"], /Queue-Based/);
  assert.equal((html.match(/\bfetch\s*\(/g) || []).length, 1);
});

test("direct-file reader renders bundled sources without fetch and retains raw links", async () => {
  const article = { innerHTML: '', parentElement: { scrollTop: 0 }, querySelector: () => null };
  const offline = { URL, location: { protocol: 'file:', href: 'file:///repo/projection-ui-map/rc-atlas-prototype.html' },
    Response, Blob, Uint8Array, atob, DecompressionStream,
    D: M.data, M, esc: value => String(value), prepareReader: () => {}, setReaderMode: () => {},
    $: () => ({ focus: () => {} }),
    state: { readerLoadToken: 0 }, els: { readerLink: {}, readerArticle: article, readerTitle: {}, readerPath: {}, reader: { classList: { contains: () => true } } },
    fetch: () => { throw new Error('file mode must not fetch'); } };
  vm.createContext(offline);
  vm.runInContext(html.match(/<script data-atlas-offline-documents>([\s\S]*?)<\/script>/)[1], offline);
  vm.runInContext(html.match(/function repositoryRootUrl\(\)[\s\S]*?(?=    function closeReader\(\))/)[0], offline);
  for (const source of M.data.sources) {
    await offline.openMarkdownReader(source.id, source.path);
    assert.match(offline.els.readerLink.href, /^file:\/\/\/repo\/docs\/architecture\//);
    assert.match(article.innerHTML, /<h[1-6]/);
  }
  await offline.openMarkdownReader('source-adr-index', '001-Queue-Based-Completion-Acceptance-Model.md', 'file:///repo/docs/architecture/adr/adr-index.md');
  assert.match(article.innerHTML, /Queue-Based Completion/);
  await offline.openMarkdownReader('source-adr-index', 'docs/architecture/missing.md');
  assert.match(article.innerHTML, /Open original Markdown/);
});

test("inspector document history preserves projection state and restores its prior content mode", async () => {
  const encoded = html.match(/atob\("([A-Za-z0-9+/=]+)"\)/)[1];
  const bundle = JSON.parse(require("node:zlib").gunzipSync(Buffer.from(encoded, "base64")));
  const functions = html.match(/function prepareReader\(item\)[\s\S]*?(?=    function selectEdge)/)[0];
  for (const view of ['atlas', 'directory', 'sources']) {
    for (const originMode of ['entity', 'relationship']) {
      const classes = new Set();
      const classList = { add: name => classes.add(name), remove: name => classes.delete(name), contains: name => classes.has(name) };
      const body = { scrollTop: 0 };
      const scroller = { scrollTop: 240 };
      const controls = {};
      const state = { view, query: 'docs', navigation: { selectedId: 'completion-assembly-execution', history: [] }, selectedEdgeId: originMode === 'relationship' ? 'edge-example' : null, viewport: { x: 70, y: -20, scale: .6 }, inspectorMode: originMode, documentHistory: [], readerLoadToken: 0 };
      const original = JSON.stringify([state.view, state.query, state.navigation, state.selectedEdgeId, state.viewport]);
      const env = { URL, location: { protocol: 'file:', href: 'file:///repo/projection-ui-map/rc-atlas-prototype.html' }, AtlasDocumentBundle: Promise.resolve(bundle),
        M, D: M.data, state, window: { scrollY: 0 }, document: { activeElement: {} },
        $: selector => controls[selector] ||= { focus: () => {} }, $$: () => [],
        esc: value => String(value), viewScroller: () => scroller, describeReaderFocus: () => ({id:'source'}), restoreReaderFocus: () => {}, renderInspector: () => {},
        els: { inspector: { parentElement: { classList } }, reader: { classList }, readerLink: {}, readerTitle: {}, readerPath: {}, readerArticle: { parentElement: body, querySelector: () => null, innerHTML: '' } } };
      vm.createContext(env); vm.runInContext(functions, env);
      await env.openReader('source-adr-index');
      assert.equal(state.inspectorMode, 'document');
      assert.ok(classes.has('document-mode'));
      assert.match(env.els.readerArticle.innerHTML, /<h1 id="adr-index">/);
      body.scrollTop = 519;
      await env.followDocumentLink('001-Queue-Based-Completion-Acceptance-Model.md');
      assert.equal(state.documentHistory.length, 1);
      assert.match(env.els.readerArticle.innerHTML, /Queue-Based Completion/);
      await env.closeReader();
      assert.match(state.readerDocumentUrl, /adr-index\.md$/);
      assert.equal(body.scrollTop, 519);
      assert.equal(state.inspectorMode, 'document');
      await env.closeReader();
      assert.equal(state.inspectorMode, originMode);
      assert.equal(scroller.scrollTop, 240);
      assert.equal(JSON.stringify([state.view, state.query, state.navigation, state.selectedEdgeId, state.viewport]), original);
      assert.ok(!classes.has('document-mode'));
      assert.equal(env.markdownSourceUrl('https://outside.example/document.md'), null);
      assert.equal(env.markdownSourceUrl('../../outside.md'), null);
      assert.equal(env.markdownSourceUrl('javascript:alert(1)'), null);
    }
  }
  const readerTag = html.match(/<section class="reader"[^>]*>/)[0];
  assert.doesNotMatch(readerTag, /dialog|aria-modal/);
  assert.match(html, /function openReader\(sourceId\) \{ return openMarkdownReader\(sourceId\); \}/);
});

test("full-screen reading reuses the current reader and keeps modal Close separate from reader Back", () => {
  assert.match(html, /id="openFullscreenReader"[^>]*aria-haspopup="dialog"[^>]*>Full screen</);
  assert.match(html, /id="readerFullscreen"[^>]*role="dialog"[^>]*aria-modal="true"[^>]*hidden/);
  assert.match(html, /id="closeFullscreenReader"[^>]*>Close full screen</);
  const fullscreen = html.match(/function setFullscreenReader\(open, restoreFocus = true\)[\s\S]*?(?=    function searchableText)/)[0];
  assert.match(fullscreen, /readerFullscreenMount\.appendChild\(els\.reader\)/);
  assert.match(fullscreen, /inspectorPanel\.appendChild\(els\.reader\)/);
  assert.match(fullscreen, /const scroller = els\.readerArticle\.parentElement, scrollTop = scroller\.scrollTop/);
  assert.doesNotMatch(fullscreen, /renderMarkdown|documentHistory\s*=|readerDocumentUrl\s*=/);
  assert.match(html, /if \(state\.fullscreenReader\) setFullscreenReader\(false\)/);
  assert.equal((html.match(/class="reader"/g) || []).length, 1);
  assert.match(html, /\.reader-fullscreen\s*\{[\s\S]*background:\s*#080d15/);
});

test("Codexify material, Galaxy transition, and reduced motion contracts remain intact", () => {
  for (const [token, value] of Object.entries({
    "--radius-micro": "12px", "--radius-tile": "19px", "--card-radius": "19px", "--edge-chrome": "6px", "--frame": "1.5px", "--bezel": "6px", "--rim": "1.5px", "--card-pad": "12px",
  })) assert.match(html, new RegExp(token + ":\\s*" + value.replace(".", "\\.")));
  assert.match(html, /\.entity-card\.active\s*\{[\s\S]*var\(--accent-strong\)/);
  assert.match(html, /id="galaxyGate"/);
  assert.match(html, /galaxy-departing/);
  assert.match(html, /galaxy-returning/);
  assert.match(html, /state\.navigation = \{ selectedId: prior\.navigation\.selectedId, history: prior\.navigation\.history\.slice\(\) \}/);
  assert.match(html, /prefers-reduced-motion:\s*reduce/);
  assert.match(html, /reducedMotion\(\) \? 0 : 540/);
});

test("truthful boundary copy remains visible and the prototype makes no automatic external request", () => {
  assert.match(html, /Architecture document snapshot · design prototype · no live connections/);
  assert.match(html, /not live federation/);
  assert.match(html, /Offline document snapshot/);
  assert.doesNotMatch(html, /<script[^>]+src=/i);
  assert.doesNotMatch(html, /<link[^>]+rel=["']stylesheet/i);
  assert.doesNotMatch(html, /@import\s/i);
  assert.doesNotMatch(html, /\b(?:XMLHttpRequest|WebSocket|EventSource)\s*\(/);
  assert.doesNotMatch(html, /serviceWorker\.register/);
});
