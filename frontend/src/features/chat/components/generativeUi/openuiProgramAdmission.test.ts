/**
 * Admission proof for the version-2 foundation pack.
 *
 * Every case here asserts the *admission* decision, not merely that a string
 * parses. The hostile cases are chosen from parser behaviour measured against
 * @openuidev/react-lang 1.0.1, including two the parser accepts silently
 * (card-in-card, and an `@Run(...)` action argument) and therefore only the
 * structural walk can refuse.
 */
import { describe, expect, it } from "vitest";
import {
  OPENUI_V2_MAX_DEPTH,
  OPENUI_V2_MAX_LIST_ENTRIES,
  OPENUI_V2_MAX_NODES,
  OPENUI_V2_MAX_PROGRAM_CHARS,
  OPENUI_V2_MAX_STATEMENTS,
  admitOpenUiFoundationProgram,
} from "./openuiProgramAdmission";

const V2 = 2;

/** Wrap a body expression in the required root assignment. */
const prog = (body: string) => `root = ${body}`;
const STACK = "CodexifyStack";

function admit(program: string) {
  return admitOpenUiFoundationProgram({ libraryVersion: V2, program });
}

function expectAdmitted(program: string) {
  const result = admit(program);
  expect(result.ok, result.ok ? "" : `expected admission, refused: ${result.reason}`).toBe(true);
  return result as Extract<typeof result, { ok: true }>;
}

function expectRefused(program: string) {
  const result = admit(program);
  expect(result.ok, `expected refusal, admitted: ${result.ok ? result.program : ""}`).toBe(false);
  return result as Extract<typeof result, { ok: false }>;
}

describe("version-2 admission: envelope", () => {
  it("admits a composed Stack -> Card -> leaf program", () => {
    expectAdmitted(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("Waiting"), CodexifyBadge("ok", "info")], "Queue")])`),
    );
  });

  it("admits multi-statement programs whose statements are all reachable", () => {
    expectAdmitted(
      [
        'header = CodexifyHeading("Overview", "2")',
        prog(`${STACK}("vertical", [header, CodexifyList(["a", "b"])])`),
      ].join("\n"),
    );
  });

  it("rejects an unknown library version and unexpected prop keys", () => {
    expect(admitOpenUiFoundationProgram({ libraryVersion: 3, program: prog(`${STACK}("vertical", [])`) }).ok).toBe(false);
    expect(admitOpenUiFoundationProgram({ libraryVersion: 1, program: 'root = CodexifyMetric("a","b")' }).ok).toBe(false);
    expect(
      admitOpenUiFoundationProgram({ libraryVersion: V2, program: prog(`${STACK}("vertical", [])`), extra: 1 }).ok,
    ).toBe(false);
  });

  it("rejects non-string, empty, and oversized programs", () => {
    expect(admitOpenUiFoundationProgram({ libraryVersion: V2, program: 42 as unknown as string }).ok).toBe(false);
    expect(admitOpenUiFoundationProgram({ libraryVersion: V2, program: "   " }).ok).toBe(false);
    const oversized = prog(`${STACK}("vertical", [CodexifyText("${"x".repeat(OPENUI_V2_MAX_PROGRAM_CHARS)}")])`);
    expect(oversized.length).toBeGreaterThan(OPENUI_V2_MAX_PROGRAM_CHARS);
    expectRefused(oversized);
  });

  it("rejects a missing root and a duplicated root", () => {
    expectRefused('spare = CodexifyText("x")');
    expectRefused(`${prog(`${STACK}("vertical", [])`)}\n${prog(`${STACK}("vertical", [])`)}`);
  });
});

describe("version-2 admission: composition", () => {
  // Each of these isolates ONE rule. A childless nested container keeps the tree
  // within the depth bound, so only the position rule can refuse it. Without that
  // separation the depth check would silently mask a missing position check.
  it("rejects Card inside Card at a depth the depth rule alone would admit", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyCard([CodexifyCard([], "inner")], "outer")])`));
  });

  it("rejects Stack inside Card at a depth the depth rule alone would admit", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyCard([${STACK}("vertical", [])], "outer")])`));
  });

  it("rejects nesting deeper than the declared depth bound", () => {
    expect(OPENUI_V2_MAX_DEPTH).toBe(3);
    expectAdmitted(prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("leaf")], "depth")])`));
    // Stack(1) -> Card(2) -> Card(3) -> leaf(4) exceeds the depth bound.
    expectRefused(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyCard([CodexifyText("x")], "inner")], "outer")])`),
    );
  });

  it("rejects a non-Stack root", () => {
    expectRefused(prog('CodexifyCard([CodexifyText("x")], "only")'));
    expectRefused(prog('CodexifyText("x")'));
  });

  it("rejects more rendered nodes than the declared node bound", () => {
    expect(OPENUI_V2_MAX_NODES).toBe(12);
    const children = Array.from({ length: 13 }, (_, i) => `CodexifyBadge("b${i}")`).join(", ");
    expectRefused(prog(`${STACK}("vertical", [${children}])`));
    const twelve = Array.from({ length: 11 }, (_, i) => `CodexifyBadge("b${i}")`).join(", ");
    expectAdmitted(prog(`${STACK}("vertical", [${twelve}])`));
  });

  it("rejects more statements than the declared statement bound", () => {
    expect(OPENUI_V2_MAX_STATEMENTS).toBe(16);
    const many = Array.from({ length: 17 }, (_, i) => `s${i} = CodexifyText("v")`).join("\n");
    expectRefused(`${many}\n${prog(`${STACK}("vertical", [s0])`)}`);
  });

  it("rejects orphaned and unresolved references", () => {
    expectRefused(`${prog(`${STACK}("vertical", [CodexifyText("x")])`)}\nspare = CodexifyText("y")`);
    expectRefused(prog(`${STACK}("vertical", [missingThing])`));
  });
});

describe("version-2 admission: authority and executability", () => {
  it("rejects Query and Mutation", () => {
    expectRefused('data = Query("metrics", {})');
    expectRefused(`${prog(`${STACK}("vertical", [CodexifyText("x")])`)}\nwrite = Mutation("save", {})`);
  });

  it("rejects an action argument that the parser stores without any error", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyText("x", "sm", @Run("do"))])`));
  });

  it("rejects reactive variables and a computed root", () => {
    expectRefused(`$flag = "vertical"\n${prog(`${STACK}($flag, [CodexifyText("x")])`)}`);
    expectRefused('root = $flag ? CodexifyText("a") : CodexifyText("b")');
  });

  it("rejects unknown components even when the parser would silently drop them", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyWidget("x")])`));
  });

  it("rejects unknown props, including styling and event-handler props", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyText("x")], "onclick")`));
    expect(
      admitOpenUiFoundationProgram({
        libraryVersion: V2,
        program: prog('CodexifyBadge("x", "neutral", { "onclick": "alert(1)" })'),
      }).ok,
    ).toBe(false);
  });

  it("rejects excess arguments reported by the parser", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyText("a", "sm", "extra")])`));
  });
});

describe("version-2 admission: bounded values", () => {
  it("rejects a list longer than the declared entry bound", () => {
    expect(OPENUI_V2_MAX_LIST_ENTRIES).toBe(12);
    const twelve = Array.from({ length: 12 }, (_, i) => `"i${i}"`).join(", ");
    expectAdmitted(prog(`${STACK}("vertical", [CodexifyList([${twelve}])])`));
    const thirteen = Array.from({ length: 13 }, (_, i) => `"i${i}"`).join(", ");
    expectRefused(prog(`${STACK}("vertical", [CodexifyList([${thirteen}])])`));
  });

  it("rejects an out-of-range progress value", () => {
    expectAdmitted(prog(`${STACK}("vertical", [CodexifyProgress("Build", 4, 8)])`));
    expectRefused(prog(`${STACK}("vertical", [CodexifyProgress("Build", 12, 8)])`));
    expectRefused(prog(`${STACK}("vertical", [CodexifyProgress("Build", 1, 0)])`));
  });

  it("rejects an over-long text value", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyText("${"y".repeat(401)}")])`));
  });

  it("rejects a badge tone outside the approved vocabulary", () => {
    expectRefused(prog(`${STACK}("vertical", [CodexifyBadge("x", "chartreuse")])`));
  });
});

describe("version-2 admission: markup is inert, not rejected", () => {
  it("admits hostile text and leaves it to render as inert text", () => {
    const hostile = '<img src=x onerror="window.__cfyXss=1"><script>window.__cfyXss=1</script>';
    const admitted = expectAdmitted(prog(`${STACK}("vertical", [CodexifyText(${JSON.stringify(hostile)})])`));
    expect(admitted.program).toContain("onerror");
  });
});