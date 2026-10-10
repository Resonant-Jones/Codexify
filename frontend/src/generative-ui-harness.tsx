/**
 * Runtime proof harness for the generative UI rendering path.
 *
 * Mounts the real ChatBubble component with canonical message content so a
 * browser can interact with the generated artifacts for real. jsdom does not
 * execute iframe srcdoc, so this is the only way to prove the calculator's
 * controls actually work and that the frame really is contained.
 *
 * Proof-only. Not part of the shipped application.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import ChatBubble from "@/features/chat/components/ChatBubble";
import {
  serializeUiArtifact,
  type GenerativeUiArtifact,
} from "@/features/chat/components/generativeUi/artifactCodec";

const CALCULATOR: GenerativeUiArtifact = {
  version: 1,
  kind: "sandbox",
  title: "Calculator",
  initialHeight: 260,
  html: [
    '<div class="wrap">',
    '<output id="display" data-testid="display" aria-live="polite">0</output>',
    '<div class="pad">',
    ...["7", "8", "9", "/", "4", "5", "6", "*", "1", "2", "3", "-", "0", ".", "=", "+"]
      .map((key) => `<button type="button" data-key="${key}">${key}</button>`),
    "</div>",
    '<button type="button" id="clear" class="clear">C</button>',
    '<button type="button" id="ask" class="ask">Ask Guardian to explain</button>',
    "</div>",
  ].join(""),
  css: [
    "body{font-size:15px}",
    "#display{display:block;text-align:right;font-size:1.6rem;font-weight:600;",
    "padding:.5rem;border:1px solid rgba(127,127,127,.35);border-radius:.5rem;margin-bottom:.5rem}",
    ".pad{display:grid;grid-template-columns:repeat(4,1fr);gap:.35rem}",
    ".pad button,.clear{font-size:1.05rem;padding:.5rem;border-radius:.4rem;",
    "border:1px solid rgba(127,127,127,.35);background:#fff;cursor:pointer}",
    ".clear{margin-top:.35rem;width:100%}.ask{margin-top:.35rem;width:100%}",
  ].join(""),
  js: [
    'var display = document.getElementById("display");',
    'var expr = "";',
    'var keys = ["7","8","9","/","4","5","6","*","1","2","3","-","0",".","=","+"];',
    // Recursive-descent evaluator. Deliberately avoids eval/new Function so it',
    // runs under the Codexify CSP, which omits unsafe-eval on purpose.',
    'function evaluate(src) {',
    '  var i = 0;',
    '  function peek() { return src.charAt(i); }',
    '  function eat(ch) { if (peek() === ch) { i += 1; return true; } return false; }',
    '  function factor() {',
    '    if (eat("-")) return -factor();',
    '    var start = i, sawDot = false;',
    '    while (i < src.length) {',
    '      var c = src.charAt(i);',
    '      if (c >= "0" && c <= "9") { i += 1; }',
    '      else if (c === "." && !sawDot) { sawDot = true; i += 1; }',
    '      else break;',
    '    }',
    '    var token = src.slice(start, i);',
    '    if (!token || token === ".") throw new Error("number expected");',
    '    var n = Number(token);',
    '    if (typeof n !== "number" || !isFinite(n)) throw new Error("bad number");',
    '    return n;',
    '  }',
    '  function term() {',
    '    var v = factor();',
    '    for (;;) { if (eat("*")) v = v * factor(); else if (eat("/")) v = v / factor(); else return v; }',
    '  }',
    '  function sum() {',
    '    var v = term();',
    '    for (;;) { if (eat("+")) v = v + term(); else if (eat("-")) v = v - term(); else return v; }',
    '  }',
    '  if (!src.trim()) throw new Error("empty");',
    '  var out = sum();',
    '  if (i !== src.length) throw new Error("trailing");',
    '  if (typeof out !== "number" || !isFinite(out)) throw new Error("not finite");',
    '  return String(out);',
    '}',
    'function flush(){ display.textContent = expr || "0"; }',
    'document.querySelectorAll("[data-key]").forEach(function (btn) {',
    '  btn.addEventListener("click", function () {',
    '    var key = btn.dataset.key;',
    '    if (key === "=") {',
    '      try { expr = evaluate(expr); } catch (e) { expr = "Error"; }',
    '    } else { expr += key; }',
    '    flush();',
    '  });',
    '});',
    'document.getElementById("clear").addEventListener("click", function () { expr = ""; flush(); });',
    // Exercise the host bridge: this must prefill the composer, never send.',
    'document.getElementById("ask").addEventListener("click", function () {',
    '  window.cfyUI.sendPrompt("Explain that 12 + 30 = 42");',
    '});',
    'flush();',
    // Prove the bridge exists and report back to the host title for inspection.
    'document.title = window.cfyUI ? "ready:bridge-present" : "ready:bridge-missing";',
  ].join("\n"),
};

const CHART: GenerativeUiArtifact = {
  version: 1,
  kind: "native",
  component: "chart.bar",
  props: {
    title: "Guardian thread volume",
    series: [
      { label: "Mon", value: 42 },
      { label: "Tue", value: 68 },
      { label: "Wed", value: 51 },
      { label: "Thu", value: 87 },
      { label: "Fri", value: 63 },
    ],
  },
};

const MESSAGES = [
  { label: "sandbox-calculator", content: [
    "Here is a calculator. Click the controls:",
    serializeUiArtifact(CALCULATOR),
  ].join("\n\n") },
  { label: "native-chart", content: [
    "Thread volume this week:",
    serializeUiArtifact(CHART),
  ].join("\n\n") },
  { label: "malformed", content: [
    "This artifact is malformed and must degrade safely:",
    "<!-- cfy-ui:@@@not-a-valid-payload@@@ -->",
    "Prose after a bad artifact.",
  ].join("\n\n") },
  { label: "plain", content: "An ordinary message with `code` and **bold** stays untouched." },
];

function Bubble({ label, content, index }: { label: string; content: string; index: number }) {
  return (
    <section data-harness-message={label}>
      <ChatBubble
        isGuardian
        message={{
          id: `harness-${index}`,
          authorId: "bot",
          authorName: "Guardian",
          content,
          createdAt: Date.now(),
        }}
      />
    </section>
  );
}

function App() {
  return (
    <>
      <h1>Codexify generative UI runtime proof</h1>
      {MESSAGES.map((entry, index) => (
        <Bubble key={entry.label} label={entry.label} content={entry.content} index={index} />
      ))}
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);