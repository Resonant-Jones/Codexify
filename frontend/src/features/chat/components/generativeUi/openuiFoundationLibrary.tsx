/**
 * Codexify OpenUI Foundation Pack v2 — the approved first-party component library.
 *
 * Design posture (see docs/architecture/generative-ui-contract.md):
 * - Read-only. No component accepts an event handler, styling prop, URL, or callback.
 * - Every visual value resolves from an inherited Codexify shell token. Components
 *   install no theme provider and hard-code no color, shadow, radius, or spacing scale.
 * - Schemas are flat and positional. Nesting is expressed with fixed-depth unions of
 *   component `.ref`s, never with recursive schemas.
 *
 * Composition contract enforced here (and re-checked by openuiProgramAdmission):
 *   root      = CodexifyStack
 *   Stack     -> leaf | CodexifyCard
 *   Card      -> leaf            (never Card, never Stack)
 *   depth     -> at most 3 (Stack, then Card, then a leaf)
 */
import React from "react";
import { createLibrary, defineComponent } from "@openuidev/react-lang";
import { z } from "zod/v4";

/** Approved library version for the composable foundation pack. */
export const OPENUI_FOUNDATION_LIBRARY_VERSION = 2;

/* ------------------------------------------------------------------ *
 * Token layer
 *
 * Tokens are consumed, never defined: this pack creates no new runtime
 * theme tokens. Four of the ten contract tokens are not currently
 * declared anywhere in the repository, so they are consumed through
 * `var(--token, <fallback>)` following the existing generative-UI
 * pattern (see openuiNative v1 and nativeRegistry PANEL_STYLE). The
 * unresolved dependency list is exported so the gap is inspectable
 * rather than silently absorbed.
 * ------------------------------------------------------------------ */

export const PANEL_BORDER = "var(--panel-border)";
export const PANEL_BACKGROUND = "var(--panel-bg)";
export const TEXT_COLOR = "var(--text)";
export const MUTED_COLOR = "var(--muted)";
export const ACCENT = "var(--accent)";

const CARD_PADDING = "var(--card-pad, 0.75rem)";
const CARD_RADIUS = "var(--card-radius, var(--tile-radius, 0.75rem))";
const MICRO_RADIUS = "var(--radius-micro, 0.375rem)";
const SHELL_GAP = "var(--shell-gap, 0.5rem)";

/**
 * Contract tokens this pack consumes that have no declaration in the current
 * tree. Reported rather than created; see the proof document's limitations.
 */
export const OPENUI_UNDECLARED_TOKEN_DEPENDENCIES = [
  "--card-pad",
  "--card-radius",
  "--radius-micro",
  "--shell-gap",
] as const;

/** Content stays inside the host conversation lane and never forces horizontal scroll. */
const CONTAINER_STYLE: React.CSSProperties = {
  maxWidth: "100%",
  minWidth: 0,
  overflowWrap: "anywhere",
  color: TEXT_COLOR,
};

/* ------------------------------------------------------------------ *
 * Content leaves
 * ------------------------------------------------------------------ */

const TextLeaf = defineComponent({
  name: "CodexifyText",
  description: "Body text with a bounded size and emphasis vocabulary.",
  props: z.object({
    text: z.string().max(400),
    size: z.enum(["sm", "md", "lg"]).optional(),
    emphasis: z.enum(["normal", "strong", "muted"]).optional(),
  }),
  component: ({ props }) => {
    const size = props.size === "sm" ? "0.8125rem" : props.size === "lg" ? "1.0625rem" : "0.9375rem";
    const color = props.emphasis === "muted" ? MUTED_COLOR : TEXT_COLOR;
    const weight = props.emphasis === "strong" ? 600 : 400;
    return (
      <p
        data-testid="openui-foundation-text"
        style={{ ...CONTAINER_STYLE, margin: 0, fontSize: size, color, fontWeight: weight }}
      >
        {props.text}
      </p>
    );
  },
});

const HeadingLeaf = defineComponent({
  name: "CodexifyHeading",
  description: "Semantic section heading. Level 2-4 only, so it never competes with the host page title.",
  props: z.object({
    text: z.string().max(120),
    level: z.enum(["2", "3", "4"]).optional(),
  }),
  component: ({ props }) => {
    const level = (props.level ?? "3") as "2" | "3" | "4";
    const Tag = `h${level}` as "h2" | "h3" | "h4";
    const size = level === "2" ? "1.0625rem" : level === "3" ? "0.9375rem" : "0.875rem";
    return (
      <Tag
        data-testid="openui-foundation-heading"
        data-level={level}
        style={{ ...CONTAINER_STYLE, margin: 0, fontSize: size, fontWeight: 600, color: TEXT_COLOR }}
      >
        {props.text}
      </Tag>
    );
  },
});

/**
 * Status/category vocabulary. Every tone pairs an already theme-aware surface
 * with its matching foreground token, so contrast is preserved in light and dark
 * without a model-authored color.
 */
const BADGE_TONES = {
  neutral: { background: "var(--chip-bg)", border: "var(--chip-border)", color: TEXT_COLOR },
  info: { background: "var(--info-surface)", border: "var(--info-surface)", color: "var(--info-text)" },
  success: {
    background: "color-mix(in oklab, var(--accent) 18%, transparent)",
    border: "var(--accent-weak)",
    color: TEXT_COLOR,
  },
  warning: { background: "var(--tag-surface)", border: "var(--tag-surface)", color: "var(--tag-text)" },
  danger: {
    background: "var(--danger-surface)",
    border: "var(--danger-border)",
    color: "var(--danger-text)",
  },
} as const;

const BadgeLeaf = defineComponent({
  name: "CodexifyBadge",
  description: "Small status or category label drawn from an approved tone vocabulary.",
  props: z.object({
    text: z.string().max(40),
    tone: z.enum(["neutral", "info", "success", "warning", "danger"]).optional(),
  }),
  component: ({ props }) => {
    const tone = BADGE_TONES[props.tone ?? "neutral"];
    return (
      <span
        data-testid="openui-foundation-badge"
        data-tone={props.tone ?? "neutral"}
        style={{
          ...CONTAINER_STYLE,
          display: "inline-flex",
          alignItems: "center",
          maxWidth: "100%",
          padding: "0.125rem 0.5rem",
          borderRadius: MICRO_RADIUS,
          border: `1px solid ${tone.border}`,
          background: tone.background,
          color: tone.color,
          fontSize: "0.75rem",
          fontWeight: 600,
          lineHeight: 1.5,
        }}
      >
        {props.text}
      </span>
    );
  },
});

/** v2 metric: same panel language as the version-1 metric, distinct test id. */
const MetricLeaf = defineComponent({
  name: "CodexifyMetric",
  description: "Read-only metric showing a label, a value, and optional detail.",
  props: z.object({
    label: z.string().max(100),
    value: z.string().max(40),
    detail: z.string().max(180).optional(),
  }),
  component: ({ props }) => (
    <section
      data-testid="openui-foundation-metric"
      style={{
        ...CONTAINER_STYLE,
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: CARD_RADIUS,
        padding: CARD_PADDING,
        background: PANEL_BACKGROUND,
        color: TEXT_COLOR,
      }}
    >
      <div style={{ color: MUTED_COLOR, fontSize: "0.875em" }}>{props.label}</div>
      <strong style={{ display: "block", fontSize: "1.6em" }}>{props.value}</strong>
      {props.detail ? <div style={{ color: MUTED_COLOR }}>{props.detail}</div> : null}
    </section>
  ),
});

/** Finite, explicitly ranged progress with an accessible name and status text. */
const ProgressLeaf = defineComponent({
  name: "CodexifyProgress",
  description: "Bounded progress indicator over an explicit finite range.",
  props: z.object({
    label: z.string().max(100),
    value: z.number().finite().min(0),
    max: z.number().finite().positive(),
    statusText: z.string().max(80).optional(),
  }),
  component: ({ props }) => {
    const max = props.max;
    const ratio = Math.min(Math.max(props.value / max, 0), 1);
    const percent = Math.round(ratio * 100);
    return (
      <div data-testid="openui-foundation-progress" style={{ ...CONTAINER_STYLE, display: "grid", gap: "0.25rem" }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
            justifyContent: "space-between",
            fontSize: "0.8125rem",
          }}
        >
          <span style={{ color: TEXT_COLOR }}>{props.label}</span>
          <span style={{ color: MUTED_COLOR }}>
            {`${percent}%`}
          </span>
        </div>
        <div
          role="progressbar"
          aria-label={props.label}
          aria-valuenow={props.value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-valuetext={`${percent}%`}
          style={{
            height: "0.5rem",
            width: "100%",
            borderRadius: MICRO_RADIUS,
            background: "var(--chip-bg)",
            overflow: "hidden",
          }}
        >
          <div
            data-testid="openui-foundation-progress-fill"
            style={{ width: `${percent}%`, height: "100%", background: "var(--accent-strong)" }}
          />
        </div>
        {props.statusText ? (
          <div data-testid="openui-foundation-progress-status" style={{ color: MUTED_COLOR, fontSize: "0.8125rem" }}>
            {props.statusText}
          </div>
        ) : null}
      </div>
    );
  },
});

const ListLeaf = defineComponent({
  name: "CodexifyList",
  description: "Bounded list of short text entries as semantic list markup.",
  props: z.object({
    items: z.array(z.string().max(160)).max(12),
    ordered: z.boolean().optional(),
  }),
  component: ({ props }) => {
    const ordered = props.ordered === true;
    return (
      <ul
        data-testid="openui-foundation-list"
        data-ordered={ordered ? "true" : "false"}
        style={{
          ...CONTAINER_STYLE,
          listStyle: ordered ? "decimal" : "disc",
          margin: 0,
          paddingInlineStart: "1.25rem",
          display: "grid",
          gap: "0.25rem",
          color: TEXT_COLOR,
          fontSize: "0.9375rem",
        }}
      >
        {props.items.map((item, index) => (
          <li key={`${index}-${item}`} style={{ overflowWrap: "anywhere" }}>
            {item}
          </li>
        ))}
      </ul>
    );
  },
});

/**
 * The leaf vocabulary. Card and Stack both accept exactly this set, which is what
 * makes the three-level depth bound structural rather than advisory.
 */
const LEAF_UNION = z.union([
  TextLeaf.ref,
  HeadingLeaf.ref,
  BadgeLeaf.ref,
  MetricLeaf.ref,
  ProgressLeaf.ref,
  ListLeaf.ref,
]);

/* ------------------------------------------------------------------ *
 * Layout
 * ------------------------------------------------------------------ */

/**
 * Children are declared before the optional heading on purpose: the OpenUI
 * parser maps positional arguments onto declared keys in order and never skips
 * an optional key, so an optional prop placed ahead of a required one would make
 * that required prop unreachable. Call it as
 * `CodexifyCard([...], "Optional heading")`.
 */
const CardNode = defineComponent({
  name: "CodexifyCard",
  description: "Structured presentation container with an optional heading and read-only leaf children.",
  props: z.object({
    children: z.array(LEAF_UNION).max(8),
    heading: z.string().max(120).optional(),
  }),
  component: ({ props, renderNode }) => (
    <section
      data-testid="openui-foundation-card"
      style={{
        ...CONTAINER_STYLE,
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: CARD_RADIUS,
        padding: CARD_PADDING,
        background: PANEL_BACKGROUND,
        color: TEXT_COLOR,
        display: "grid",
        gap: SHELL_GAP,
        alignContent: "start",
      }}
    >
      {props.heading ? (
        <h3
          data-testid="openui-foundation-card-heading"
          style={{ margin: 0, fontSize: "0.9375rem", fontWeight: 600, color: TEXT_COLOR }}
        >
          {props.heading}
        </h3>
      ) : null}
      {props.children.map((child, index) => (
        <React.Fragment key={`card-child-${index}`}>{renderNode(child)}</React.Fragment>
      ))}
    </section>
  ),
});

const StackRoot = defineComponent({
  name: "CodexifyStack",
  description: "Required root container. Arranges approved leaf components and cards along one axis.",
  props: z.object({
    direction: z.enum(["vertical", "horizontal"]),
    children: z.array(z.union([CardNode.ref, LEAF_UNION])).max(12),
    wrap: z.boolean().optional(),
  }),
  component: ({ props, renderNode }) => {
    const vertical = props.direction !== "horizontal";
    return (
      <div
        data-testid="openui-foundation-stack"
        data-direction={vertical ? "vertical" : "horizontal"}
        style={{
          ...CONTAINER_STYLE,
          display: "flex",
          flexDirection: vertical ? "column" : "row",
          flexWrap: props.wrap === true ? "wrap" : "nowrap",
          gap: SHELL_GAP,
          alignItems: vertical ? "stretch" : "flex-start",
        }}
      >
        {props.children.map((child, index) => (
          <React.Fragment key={`stack-child-${index}`}>{renderNode(child)}</React.Fragment>
        ))}
      </div>
    );
  },
});

/**
 * The approved version-2 library. Only these eight components are registrable;
 * every parent points at a fixed-depth union of `.ref`s, so no schema here is
 * recursive and no renderer resolves a component name dynamically.
 */
export const codexifyOpenUiFoundationLibrary = createLibrary({
  components: [StackRoot, CardNode, TextLeaf, HeadingLeaf, BadgeLeaf, MetricLeaf, ProgressLeaf, ListLeaf],
  root: "CodexifyStack",
  componentGroups: [
    { name: "Layout", components: ["CodexifyStack", "CodexifyCard"] },
    { name: "Content", components: ["CodexifyText", "CodexifyHeading", "CodexifyList"] },
    { name: "Data Presentation", components: ["CodexifyBadge", "CodexifyMetric", "CodexifyProgress"] },
  ],
});

/** Component ids admitted by the foundation pack, in canonical order. */
export const OPENUI_FOUNDATION_COMPONENT_NAMES = [
  "CodexifyStack",
  "CodexifyCard",
  "CodexifyText",
  "CodexifyHeading",
  "CodexifyBadge",
  "CodexifyMetric",
  "CodexifyProgress",
  "CodexifyList",
] as const;

export type OpenUiFoundationComponentName = (typeof OPENUI_FOUNDATION_COMPONENT_NAMES)[number];