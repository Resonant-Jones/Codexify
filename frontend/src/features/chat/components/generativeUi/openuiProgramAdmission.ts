/**
 * Version-aware, fail-closed admission for Codexify OpenUI foundation programs.
 *
 * The official OpenUI parser is necessary but **not** sufficient. Measured
 * against @openuidev/react-lang 1.0.1, the parser:
 *   - accepts a CodexifyCard nested inside a CodexifyCard with zero errors,
 *     even when the parent schema's union contains only leaf refs;
 *   - drops an unknown component from the tree and still returns a renderable
 *     root;
 *   - stores `@Run(...)` action arguments and `$var` references as AST objects
 *     inside `props` with no error at all.
 *
 * A permissive parser is therefore never the security boundary. This module
 * re-derives the admitted structure from the resolved tree and rejects anything
 * it cannot positively classify as a bounded literal.
 *
 * Contract: docs/architecture/generative-ui-contract.md
 */
import { createParser } from "@openuidev/react-lang";
import {
  OPENUI_FOUNDATION_LIBRARY_VERSION,
  codexifyOpenUiFoundationLibrary,
} from "./openuiFoundationLibrary";

/** Declared bounds for a version-2 program. */
export const OPENUI_V2_MAX_PROGRAM_CHARS = 4096;
export const OPENUI_V2_MAX_STATEMENTS = 16;
export const OPENUI_V2_MAX_NODES = 12;
export const OPENUI_V2_MAX_DEPTH = 3;
export const OPENUI_V2_MAX_LIST_ENTRIES = 12;

export type OpenUiAdmissionResult = { ok: true; program: string } | { ok: false; reason: string };

const parser = createParser(codexifyOpenUiFoundationLibrary.toJSONSchema(), codexifyOpenUiFoundationLibrary.root);

/* ------------------------------------------------------------------ *
 * Field vocabulary
 * ------------------------------------------------------------------ */

type FieldKind = "string" | "enum" | "boolean" | "number" | "children" | "items";

type Field = { kind: FieldKind; max?: number; values?: readonly string[] };

const TEXT_MAX = 400;
const LABEL_MAX = 100;
const HEADING_MAX = 120;
const BADGE_TEXT_MAX = 40;
const METRIC_VALUE_MAX = 40;
const DETAIL_MAX = 180;
const STATUS_MAX = 80;
const ITEM_MAX = 160;

/** Exactly the props each approved component accepts. Anything else is unknown. */
const COMPONENT_FIELDS: Record<string, Record<string, Field>> = {
  CodexifyStack: {
    direction: { kind: "enum", values: ["vertical", "horizontal"] },
    wrap: { kind: "boolean" },
    children: { kind: "children" },
  },
  CodexifyCard: {
    heading: { kind: "string", max: HEADING_MAX },
    children: { kind: "children" },
  },
  CodexifyText: {
    text: { kind: "string", max: TEXT_MAX },
    size: { kind: "enum", values: ["sm", "md", "lg"] },
    emphasis: { kind: "enum", values: ["normal", "strong", "muted"] },
  },
  CodexifyHeading: {
    text: { kind: "string", max: HEADING_MAX },
    level: { kind: "enum", values: ["2", "3", "4"] },
  },
  CodexifyBadge: {
    text: { kind: "string", max: BADGE_TEXT_MAX },
    tone: { kind: "enum", values: ["neutral", "info", "success", "warning", "danger"] },
  },
  CodexifyMetric: {
    label: { kind: "string", max: LABEL_MAX },
    value: { kind: "string", max: METRIC_VALUE_MAX },
    detail: { kind: "string", max: DETAIL_MAX },
  },
  CodexifyProgress: {
    label: { kind: "string", max: LABEL_MAX },
    value: { kind: "number" },
    max: { kind: "number" },
    statusText: { kind: "string", max: STATUS_MAX },
  },
  CodexifyList: {
    items: { kind: "items" },
    ordered: { kind: "boolean" },
  },
};

/** Components that terminate a branch and may not declare children. */
const LEAF_COMPONENTS = new Set([
  "CodexifyText",
  "CodexifyHeading",
  "CodexifyBadge",
  "CodexifyMetric",
  "CodexifyProgress",
  "CodexifyList",
]);

/** Card accepts leaves only: never another Card, never a Stack. */
const CARD_CHILDREN = LEAF_COMPONENTS;
/** Stack accepts leaves and cards. */
const STACK_CHILDREN = new Set([...LEAF_COMPONENTS, "CodexifyCard"]);

/* ------------------------------------------------------------------ *
 * Structural inspection
 * ------------------------------------------------------------------ */

type Node = {
  type: string;
  typeName: string;
  props: Record<string, unknown>;
  partial: boolean;
  hasDynamicProps?: boolean;
  statementId?: string;
};

function isNode(value: unknown): value is Node {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Node>;
  return (
    candidate.type === "element" &&
    typeof candidate.typeName === "string" &&
    !!candidate.props &&
    typeof candidate.props === "object"
  );
}

function validateLiteral(name: string, field: string, value: unknown, spec: Field): string | null {
  if (value === undefined) return null; // optional prop, simply absent
  switch (spec.kind) {
    case "string":
      if (typeof value !== "string") return `${name}.${field} must be a string literal`;
      if (value.length > (spec.max ?? TEXT_MAX)) return `${name}.${field} exceeds its length bound`;
      return null;
    case "enum":
      if (typeof value !== "string" || !spec.values?.includes(value)) {
        return `${name}.${field} is outside the approved vocabulary`;
      }
      return null;
    case "boolean":
      if (typeof value !== "boolean") return `${name}.${field} must be a boolean literal`;
      return null;
    case "number":
      if (typeof value !== "number" || !Number.isFinite(value)) return `${name}.${field} must be a finite literal`;
      return null;
    case "items":
      if (!Array.isArray(value)) return `${name}.${field} must be a bounded array of strings`;
      if (value.length > OPENUI_V2_MAX_LIST_ENTRIES) return `${name}.${field} exceeds the list-entry bound`;
      for (const entry of value) {
        if (typeof entry !== "string") return `${name}.${field} accepts text entries only`;
        if (entry.length > ITEM_MAX) return `${name}.${field} entry exceeds its length bound`;
      }
      return null;
    default:
      return `${name}.${field} is not admitted`;
  }
}

/** Returns an error string, or null when the whole subtree is admitted. */
function walk(node: Node, depth: number, counter: { nodes: number }, allowed: Set<string>): string | null {
  counter.nodes += 1;
  if (counter.nodes > OPENUI_V2_MAX_NODES) return "program exceeds the rendered-node bound";
  if (depth > OPENUI_V2_MAX_DEPTH) return "program exceeds the nesting-depth bound";

  const fields = COMPONENT_FIELDS[node.typeName];
  if (!fields) return `component ${node.typeName} is not in the approved library`;
  if (!allowed.has(node.typeName)) return `${node.typeName} is not permitted in this position`;
  if (node.partial) return "component tree is incomplete";
  // Any reactive or computed prop arrives flagged. It is never a literal.
  if (node.hasDynamicProps) return `${node.typeName} carries a dynamic or reactive prop`;

  for (const [key, value] of Object.entries(node.props)) {
    const spec = fields[key];
    if (!spec) return `${node.typeName} received unknown prop "${key}"`;
    if (spec.kind === "children") {
      if (!Array.isArray(value)) return `${node.typeName}.children must be an array of component references`;
      const childAllowed =
        node.typeName === "CodexifyStack" ? STACK_CHILDREN : node.typeName === "CodexifyCard" ? CARD_CHILDREN : new Set<string>();
      if (childAllowed.size === 0) return `${node.typeName} may not declare children`;
      if (value.length > OPENUI_V2_MAX_NODES) return `${node.typeName}.children exceeds its array bound`;
      for (const child of value) {
        if (!isNode(child)) return `${node.typeName}.children must contain only component references`;
        const problem = walk(child, depth + 1, counter, childAllowed);
        if (problem) return problem;
      }
      continue;
    }
    const problem = validateLiteral(node.typeName, key, value, spec);
    if (problem) return problem;
  }

  // Cross-field rule the schema cannot express: progress is a finite range.
  if (node.typeName === "CodexifyProgress") {
    const max = node.props.max as number;
    const value = node.props.value as number;
    if (!(max > 0)) return "CodexifyProgress.max must be greater than zero";
    if (!(value >= 0) || !(value <= max)) return "CodexifyProgress.value must fall inside its declared range";
  }

  return null;
}

/* ------------------------------------------------------------------ *
 * Entry point
 * ------------------------------------------------------------------ */

/**
 * Admit one version-2 foundation program, or explain why it was refused.
 *
 * Every rejection path is total: an unclassifiable program renders no artifact.
 */
export function admitOpenUiFoundationProgram(props: Record<string, unknown>): OpenUiAdmissionResult {
  if (props.libraryVersion !== OPENUI_FOUNDATION_LIBRARY_VERSION) {
    return { ok: false, reason: "unknown library version" };
  }
  if (Object.keys(props).length !== 2) return { ok: false, reason: "unexpected prop keys" };

  const raw = props.program;
  if (typeof raw !== "string" || !raw.trim()) return { ok: false, reason: "program must be a non-empty string" };
  if (raw.length > OPENUI_V2_MAX_PROGRAM_CHARS) return { ok: false, reason: "program exceeds the character bound" };

  // Exactly one root assignment. A missing or duplicated root never renders.
  const heads = raw.match(/^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[^=]/gm) ?? [];
  const rootAssignments = heads.filter((head) => head.trimStart().startsWith("root")).length;
  if (rootAssignments === 0) return { ok: false, reason: "program has no root statement" };
  if (rootAssignments > 1) return { ok: false, reason: "program declares more than one root" };

  const parsed = parser.parse(raw);
  if (parsed.meta.incomplete) return { ok: false, reason: "program is incomplete" };
  if (parsed.meta.errors.length > 0) {
    return { ok: false, reason: `parser rejected program: ${parsed.meta.errors[0].code}` };
  }
  if (parsed.meta.unresolved.length > 0) return { ok: false, reason: "program has unresolved references" };
  if (parsed.meta.orphaned.length > 0) return { ok: false, reason: "program has orphaned statements" };
  if (parsed.meta.statementCount > OPENUI_V2_MAX_STATEMENTS) {
    return { ok: false, reason: "program exceeds the statement bound" };
  }
  // Query/Mutation are extracted as their own statement lists.
  if (parsed.queryStatements.length > 0) return { ok: false, reason: "Query is not admitted" };
  if (parsed.mutationStatements.length > 0) return { ok: false, reason: "Mutation is not admitted" };
  // Reactive `$variables` and a computed root are never literals.
  if (Object.keys(parsed.stateDeclarations).length > 0) return { ok: false, reason: "reactive variables are not admitted" };
  if (parsed.rootExpression) return { ok: false, reason: "dynamic root selection is not admitted" };

  if (!parsed.root) return { ok: false, reason: "program produced no root" };
  if (parsed.root.typeName !== "CodexifyStack") return { ok: false, reason: "root must be CodexifyStack" };
  if (parsed.root.statementId !== "root") return { ok: false, reason: "root statement is not addressable" };

  const counter = { nodes: 0 };
  const problem = walk(parsed.root, 1, counter, new Set(["CodexifyStack"]));
  if (problem) return { ok: false, reason: problem };

  return { ok: true, program: raw.trim() };
}