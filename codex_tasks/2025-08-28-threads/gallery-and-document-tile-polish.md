
Prompt for Codex – Gallery & Document Tile polish

Goal
Unify the visual language of gallery previews and document tiles into rounded-square tiles with an edge-to-edge image preview, a simplified bezel, and a bottom banner for document metadata. Preserve the existing gallery grid spacing and layout.

Tech context
 • React + TypeScript + Tailwind.
 • Current PreviewTile lives at src/components/ui/PreviewTile.tsx and already supports square.
 • Design tokens: use existing CSS variables where possible: --chip-bg, --panel-border, --text, --accent-strong.
 • Do not modify grid sizing or gaps anywhere (keep the gallery layout exactly as is).

⸻

Tasks

1) PreviewTile – Simplified bezel + true edge-to-edge image
 • Add an optional prop: bezel?: "default" | "simple" (default = "default" to avoid breaking changes).
 • When square && bezel === "simple":
 • Keep the outer 3px internal rim on <CardContent className="p-[3px]">.
 • Remove the inner border and inner drop shadow from the tile container.
 • Concretely, drop the border and shadow-sm classes from the inner wrapper in this mode.
 • Ensure the child image/video truly fills the rounded square edge-to-edge:
 • Keep overflow-hidden and rounded-* on the container.
 • Child should remain absolute inset-0 w-full h-full object-cover block.
 • Maintain the existing active ring behavior (inset box-shadow using --accent-strong).

Acceptance (PreviewTile)
 • In square + bezel="simple" mode, there is only the 3px outer rim; no inner border line and no inner shadow.
 • The image touches the rounded bounds with zero inset; no stray gaps.
 • Non-square usage remains visually unchanged.

2) Recent Document Tiles – Rounded squares + bottom banner
 • Update Recent Document Tiles to use the same rounded-square container language as gallery images (reuse PreviewTile if helpful).
 • Add a bottom banner that spans the full width inside the rounded tile:
 • Height: ~36–44px (choose a fixed height that looks balanced with the current grid).
 • Content: file name (truncate middle or end) and extension.
 • The banner’s background color must match the document icon color for the file’s extension.
 • Pull the color from the existing settings mapping for extension types (use the settings store/source of truth).
 • If no mapping exists, fall back to a sensible default token (e.g., var(--panel-border) at ~12–16% opacity over --chip-bg).
 • Text color must meet contrast (AA) over the banner background; adjust with a readable on-color (e.g., --text or computed).
 • Ensure the image or file preview (if any) still fills the tile; the banner sits on top as an overlay pinned to bottom with a subtle top divider (e.g., border-t using --panel-border at 1px).

Acceptance (Recent)
 • Tiles are rounded squares, matching gallery image corners.
 • Banner shows name + extension, truncates gracefully, and color-matches the icon/extension theme.
 • No change to the gallery grid’s spacing or column structure.

3) Pinned preview tiles – tighter vertical rhythm
 • For text-only pinned preview tiles, reduce vertical padding so the text “hugs” without extra top/bottom space.
 • Create a compact text style variant (e.g., py-1.5 or similar) while respecting the existing grid width and horizontal stretch.
 • Do not alter grid spacing or the number of columns.

Acceptance (Pinned)
 • Pinned tiles feel snug vertically, with no apparent extra top/bottom padding.
 • Grid alignment and horizontal stretch remain exactly the same as today.

⸻

Implementation notes
 • Prefer composition over duplication: if PreviewTile can be parameterized (square, bezel, footerBanner), reuse it for documents.
 • Keep the existing rounded-* token consistent across gallery and document tiles (match current gallery radius).
 • Respect a11y:
 • Images must have alt (pass through from children or accept a prop).
 • Focus states visible; reuse the active ring for keyboard focus if appropriate.
 • Avoid regressions:
 • Do not change gallery grid classes, gaps, or container widths.
 • Non-square PreviewTile usage should remain pixel-identical unless bezel="simple" is explicitly set.

⸻

Deliverables
 1. Updated src/components/ui/PreviewTile.tsx with bezel prop and conditional classes for the simplified bezel in square mode.
 2. A document tile component (or update the existing one) that renders:
 • Rounded-square container consistent with gallery tiles.
 • Bottom banner with name + extension and color pulled from the extension-to-color settings map.
 3. Minor style tweak for pinned preview tiles to reduce vertical padding (introduce a compact variant or prop).
 4. Story/test examples or usage snippets demonstrating:
 • Gallery image using square bezel="simple".
 • Recent Document Tile with banner in two different extension colors (e.g., .pdf, .md).
 • Pinned tile with compact vertical padding.

Do not touch grid spacing or layout files beyond swapping in the updated components/props.

⸻

Quick usage examples (for verification)

// Gallery image – edge-to-edge with simplified bezel
<PreviewTile square bezel="simple">
  <img src="/demo/cat.jpg" alt="Sample" />
</PreviewTile>

// Recent document tile – banner color follows extension mapping
<DocumentTile file={{ name: "PulseOS System Design", ext: "md" }} />

// Pinned tile – compact text padding
<PinnedTile compact>
  Codexify Roadmap Q4
</PinnedTile>

When you paste this into Codex, it should produce a patch touching PreviewTile.tsx, your document tile component, and the pinned list component—without altering the gallery grid’s spacing.
