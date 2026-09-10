const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");

const htmlPath = path.join(__dirname, "rc-atlas-prototype.html");
const html = fs.readFileSync(htmlPath, "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(match => match[1]);
const modelMatch = html.match(/<script\s+data-atlas-model>([\s\S]*?)<\/script>/i);

assert.ok(modelMatch, "prototype exposes the pure Atlas model script");
const context = { console };
context.globalThis = context;
vm.createContext(context);
vm.runInContext(modelMatch[1], context, { filename: "rc-atlas-model.js" });
const M = context.AtlasModel;

test("all executable inline JavaScript has valid syntax", () => {
  assert.ok(scripts.length >= 2);
  scripts.forEach((source, index) => assert.doesNotThrow(() => new vm.Script(source, { filename: `inline-${index}.js` })));
});

test("prototype-local Codexify material tokens preserve the canonical geometry contract", () => {
  const expectedTokens = {
    "--radius-micro": "12px",
    "--radius-tile": "19px",
    "--card-radius": "19px",
    "--edge-chrome": "6px",
    "--frame": "1.5px",
    "--bezel": "6px",
    "--rim": "1.5px",
    "--card-pad": "12px",
  };
  for (const [token, value] of Object.entries(expectedTokens)) {
    assert.match(html, new RegExp(`${token}:\\s*${value.replace(".", "\\.")}`));
  }
  for (const token of ["--panel-bg", "--panel-border", "--panel-bezel", "--panel-sheet", "--panel-sheet-border", "--chip-bg", "--chip-border", "--text", "--muted", "--text-subtle", "--surface-hover", "--surface-soft", "--accent", "--accent-strong"]) {
    assert.match(html, new RegExp(`${token}:`), `${token} is defined locally`);
  }
  assert.match(html, /\.entity-card\s*\{[\s\S]*border-radius:\s*var\(--card-radius\)/);
  assert.match(html, /\.entity-card::before,[\s\S]*clip-path:\s*inset\(0 round var\(--card-radius\)\)/);
  assert.match(html, /\.entity-card\.active\s*\{[\s\S]*var\(--accent-strong\)/);
});

test("persistent hierarchy rail and hierarchy-only controls are removed", () => {
  assert.doesNotMatch(html, /<aside[^>]+class=["'][^"']*sidebar/i);
  assert.doesNotMatch(html, /\b(?:sidebarTree|sidebarSources|renderSidebar|side-scroll|section-title|tree-level|tree-row|mini-glyph)\b/);
  assert.doesNotMatch(html, /--depth\s*:/);
  assert.match(html, /\.app\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) 350px/);
  assert.match(html, /<header class="topbar">[\s\S]*<div class="product-identity"[^>]*>[\s\S]*RC Atlas/);
});

test("Directory is flat and Sources owns source discovery", () => {
  const directoryRenderer = html.match(/function renderDirectory\(\)[\s\S]*?function renderSources\(\)/)?.[0] || "";
  assert.match(directoryRenderer, /D\.entities\.filter\(item => item\.graph !== false/);
  assert.match(directoryRenderer, /class="directory-list"/);
  assert.match(directoryRenderer, /class="directory-row/);
  assert.doesNotMatch(directoryRenderer, /hierarchyRows|tree-level|--depth/);
  assert.match(html, /data-view="sources"/);
  assert.match(html, /id="sourcesView"/);
  assert.match(html, /Reviewed architecture reading path/);
});

test("graph cards use progressive disclosure instead of exposed taxonomy", () => {
  const graphRenderer = html.match(/function renderGraph\(\)[\s\S]*?function renderRoutes\(\)/)?.[0] || "";
  assert.match(graphRenderer, /entity-descriptor/);
  assert.match(graphRenderer, /selection-state/);
  assert.doesNotMatch(graphRenderer, /entity-kind/);
  assert.doesNotMatch(graphRenderer, /entity-id/);
  assert.match(graphRenderer, /title="\$\{esc\(classification\)\}/);
  assert.match(html, /<dt>Stable ID<\/dt>/, "stable IDs remain available in the inspector");
  assert.match(html, /<dt>Runtime evidence<\/dt>/, "runtime evidence remains available in the inspector");
});

test("Galaxy remains explicit, spatial, reversible, and reduced-motion aware", () => {
  assert.match(html, /id="galaxyGate"/);
  assert.match(html, /#confirmGalaxy"\)\.addEventListener\("click", enterGalaxy\)/);
  assert.match(html, /galaxy-departing/);
  assert.match(html, /galaxy-returning/);
  assert.match(html, /transform:\s*scale\(\.68\)/);
  assert.match(html, /state\.navigation = \{ selectedId: prior\.navigation\.selectedId, history: prior\.navigation\.history\.slice\(\) \}/);
  assert.match(html, /prefers-reduced-motion:\s*reduce/);
  assert.match(html, /reducedMotion\(\) \? 0 : 540/);
});

test("fixture IDs are unique and every reference is valid", () => {
  assert.deepEqual(Array.from(M.validate()), []);
  const ids = M.data.entities.map(entity => entity.id);
  assert.equal(new Set(ids).size, ids.length);
});

test("hierarchy relationships use legal parent-child kinds", () => {
  for (const entity of M.data.entities.filter(entity => entity.parentId)) {
    const parent = M.byId(entity.parentId);
    assert.ok(parent, `parent exists for ${entity.id}`);
    assert.ok(M.data.hierarchy[parent.kind].includes(entity.kind), `${parent.kind} may contain ${entity.kind}`);
  }
  assert.equal(M.byId("home-rc").kind, "homebase");
  assert.equal(M.byId("space-contributor").parentId, "home-rc");
  assert.equal(M.byId("room-orientation").parentId, "space-contributor");
});

test("Threads remain separate from Rooms and Messages remain separate from Threads", () => {
  const roomThreads = M.childrenOf("room-orientation").filter(entity => entity.kind === "thread");
  assert.deepEqual(Array.from(roomThreads, entity => entity.id).sort(), ["thread-boundaries", "thread-welcome"]);
  assert.notDeepEqual(M.data.messages["thread-welcome"], M.data.messages["thread-boundaries"]);
  for (const [threadId, messages] of Object.entries(M.data.messages)) {
    assert.equal(M.byId(threadId).kind, "thread");
    for (const message of messages) {
      assert.equal(M.byId(message.id).kind, "message");
      assert.equal(M.byId(message.id).parentId, threadId);
    }
  }
});

test("display names are independent of identity, routing, and hierarchy", () => {
  const renamed = M.data.entities.map(entity => ({ ...entity, name: `Renamed ${entity.kind}` }));
  assert.equal(M.byId("home-rc", renamed).kind, "homebase");
  assert.deepEqual(Array.from(M.childrenOf("home-rc", renamed), entity => entity.id).sort(), ["space-contributor", "space-public"]);
  assert.deepEqual(Array.from(M.ancestorsOf("thread-welcome", renamed), entity => entity.id), ["org-rc", "home-rc", "space-contributor", "room-orientation", "thread-welcome"]);
});

test("graph and non-spatial directory expose the same destinations", () => {
  assert.deepEqual(M.graphIds(), M.listIds());
  assert.ok(M.graphIds().includes("home-collab"));
  assert.ok(M.graphIds().includes("node-vault"));
  assert.ok(!M.graphIds().includes("message-welcome-1"));
});

test("entity selection still drives navigation and contextual inspection", () => {
  assert.match(html, /const nav = event\.target\.closest\("\[data-navigate\]"\)/);
  assert.match(html, /navigateTo\(nav\.dataset\.navigate/);
  assert.match(html, /function renderInspector\(\)/);
  assert.match(html, /<dt>Stable ID<\/dt>/);
  assert.match(html, /<dt>Parent\/context<\/dt>/);
});

test("Project projection exposes only the selected sample resources", () => {
  assert.deepEqual(Array.from(M.projectedResourceIds("room-orientation")), ["artifact-framework", "artifact-atlas-contract"]);
  assert.deepEqual(Array.from(M.projectedResourceIds("room-design")), []);
  const projection = M.data.relationships.find(edge => edge.kind === "projection");
  assert.equal(M.byId(projection.from).kind, "project");
  assert.equal(M.byId(projection.to).kind, "room");
});

test("source snapshots and synthetic fixtures carry explicit truth labels", () => {
  for (const source of M.data.sources) {
    assert.ok(source.path.startsWith("docs/architecture/"));
    assert.match(source.status, /proposed|contract|guide/);
    assert.equal(source.origin, "repository snapshot");
    assert.match(source.representation, /excerpt|summary/);
    assert.equal(source.runtimeEvidence, "not evaluated");
  }
  assert.equal(M.byId("home-collab").synthetic, true);
  assert.ok(M.data.relationships.every(edge => edge.evidence && edge.explanation));
});

test("navigation preserves history and invalid selections recover safely", () => {
  let nav = M.createNavigation("home-rc");
  nav = M.navigate(nav, "space-contributor");
  nav = M.navigate(nav, "room-orientation");
  nav = M.navigate(nav, "thread-welcome");
  assert.equal(nav.selectedId, "thread-welcome");
  nav = M.back(nav);
  assert.equal(nav.selectedId, "room-orientation");
  const recovered = M.navigate(nav, "missing-entity");
  assert.equal(recovered.selectedId, "home-rc");
});

test("presentation storage accepts only bounded view state and falls back on failure", () => {
  const fallback = M.defaultPresentation();
  const malformed = M.loadPresentation({ getItem() { return "{broken"; } });
  assert.deepEqual(malformed, fallback);
  const blocked = M.loadPresentation({ getItem() { throw new Error("blocked"); } });
  assert.deepEqual(blocked, fallback);
  const stored = M.loadPresentation({ getItem() { return JSON.stringify({ viewport: { x: 12, y: 18, scale: 99 }, positions: { "home-rc": { x: 77, y: 88 } }, memberships: ["ignored"] }); } });
  assert.equal(stored.viewport.scale, 1.35);
  assert.deepEqual(JSON.parse(JSON.stringify(stored.positions["home-rc"])), { x: 77, y: 88 });
  assert.equal("memberships" in stored, false);
});

test("persistent simulation boundary and unavailable Send state are present", () => {
  assert.match(html, /Interactive design prototype · sample topology · no live connections/);
  assert.match(html, /Send unavailable/);
  assert.match(html, /Illustrative discovery · synthetic sectors · no live availability/);
  assert.doesNotMatch(html, />\s*Repo implemented\s*</);
  assert.doesNotMatch(html, />\s*logged in\s*</i);
});

test("prototype is self-contained and initiates no external service path", () => {
  assert.doesNotMatch(html, /<script[^>]+src=/i);
  assert.doesNotMatch(html, /<link[^>]+rel=["']stylesheet/i);
  assert.doesNotMatch(html, /@import\s/i);
  assert.doesNotMatch(html, /\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(/);
  assert.doesNotMatch(html, /serviceWorker\.register/);
});
