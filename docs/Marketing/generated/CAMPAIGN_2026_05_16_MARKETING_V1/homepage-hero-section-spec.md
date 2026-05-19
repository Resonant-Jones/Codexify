# Homepage Hero Section Spec

Campaign ID: `CAMPAIGN_2026_05_16_MARKETING_V1`  
Primary concept: `Hero Concept 1 - Threadline Continuity`  
Primary lane: `Memory Spine`  
Secondary support lane: `Operator Console` (proof/inspectability accents only)

## Component Intent

Deliver a production-ready homepage hero that anchors on continuity and claim-safe trust:

- Core spine: "Own the thread. Build intelligence you can keep."
- Campaign thesis: "Codexify exists because AI made thought faster, but not more durable."
- Primary audiences: solo AI builders and local-first/privacy-conscious AI users.

## Final Public-Facing Copy

### Desktop Copy

Headline:
- Own the thread. Build intelligence you can keep.

Subheadline:
- Codexify is a local-first cognitive workspace for turning scattered chats, documents, and workflow traces into durable project intelligence you can retrieve and inspect.

CTA row:
- Primary CTA button: Explore Codexify
- Optional secondary link: Read current truth

Proof-callout chip:
- Supported path: local-first by default; thread/project continuity is a core workflow surface.

### Mobile Copy

Headline:
- Own the thread. Build intelligence you can keep.

Subheadline:
- Codexify helps turn scattered chats, documents, and workflow traces into durable project intelligence.

CTA row:
- Primary CTA button: Explore Codexify
- Optional secondary link: Read current truth

Proof-callout chip:
- Local-first by default. Continuity is a core workflow surface.

## Layout Notes

### Desktop (>=1200px)

- Content split: left 45%, visual 55%.
- Left column order: headline -> subheadline -> CTA row -> proof-callout chip.
- Right column: continuity-spine image with 4 to 5 abstract nodes and subtle glass depth.
- Keep max text width around 16 to 18 words per line for headline and 55 to 72 characters for subheadline line wraps.
- CTA row stays on one line when space allows.

### Tablet (768px to 1199px)

- Content split: left 50%, visual 50%, or stacked hybrid if width is constrained.
- Preserve hierarchy: headline first, then subheadline, then CTA row, then proof-callout.
- Visual can reduce to 3 to 4 nodes while retaining the same continuity line direction.
- Secondary link may wrap below primary CTA if needed.

### Mobile (<=767px)

- Vertical stack order: headline -> subheadline -> primary CTA -> optional secondary link -> proof-callout chip -> visual.
- Visual simplified to a vertical memory-spine with 3 key nodes.
- Maintain breathing room around CTA and proof-callout for tap clarity.
- Keep proof-chip concise and single-line where possible.

## Visual and Background Guidance

Use Image Generation Seed 1 direction:

- Quiet cinematic dark slate environment.
- A single luminous continuity line threading through abstract nodes implying search, conversation, document, and artifact transitions.
- Obsidian shadows, muted teal/cyan accents, subtle glass layers, warm iron highlights.
- No text or logos in image output.
- No neon sci-fi clutter, no loud UI chrome, no decorative complexity that competes with copy.

Implementation notes:

- Treat the background as a contextual continuity field, not literal product UI.
- Use Operator Console motifs only as faint peripheral support for inspectability (micro status-strip hints, not dashboard density).
- Preserve strong copy contrast over the image with overlay gradients if needed.

## Accessibility Notes

- Use a single semantic `h1` for the hero headline.
- Ensure color contrast meets WCAG AA for headline, subheadline, CTA, and proof-callout chip.
- Proof-callout chip must be real text (not baked into image).
- CTA and optional link must be keyboard reachable with visible focus states.
- Provide meaningful `aria-label` for primary CTA if button text is reused elsewhere.
- Respect reduced-motion preferences: disable decorative spine motion or use minimal opacity transitions only.
- Ensure tap targets are at least 44px high on mobile.
- Do not rely on color alone to communicate proof-callout significance.

## Why This Is Claim-Safe

- Copy stays within safe claims: local-first supported posture, thread/project continuity, durable intelligence framing, and inspectability.
- It avoids caution/future/rejected territory such as autonomous operation, hosted SaaS maturity, enterprise-readiness guarantees, and absolute privacy/security promises.
- Proof-callout wording is bounded and specific, and does not imply universal reliability or zero-loss guarantees.

## Do Not Implement These Lines

Unsafe variants that must not appear in hero copy:

- "Fully autonomous agents run your workflow end to end."
- "Codexify is a mature hosted SaaS platform."
- "Enterprise-ready out of the box."
- "Guaranteed privacy and zero context loss."
- "Set-and-forget intelligence with no supervision."
- "Never lose context again."

## Optional Alternate Microcopy (A/B)

Use only one alternate set at a time. Keep the same claim boundaries.

Variant A:
- Subheadline: Codexify is a local-first cognitive workspace for keeping project context durable across chats, docs, and workflow traces.
- Secondary link: See claim boundary
- Proof chip: Evidence-linked claims. Inspectable runtime truth.

Variant B:
- Subheadline: From fragmented AI sessions to durable project intelligence you can retrieve, inspect, and build on.
- Secondary link: View proof surfaces
- Proof chip: Supported local-first posture. Continuity over scrollback.

Variant C:
- Subheadline: Build with memory that keeps the line between first thought and finished artifact.
- Secondary link: Read current truth
- Proof chip: Local-first by default. Claims tied to proof.
