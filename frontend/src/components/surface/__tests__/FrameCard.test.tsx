import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import FrameCard from "../FrameCard";

describe("FrameCard canonical chrome", () => {
  it("builds bezel, frame, rim, and content from shared geometry tokens", () => {
    const { container } = render(
      <FrameCard ariaLabel="Example" selected data-testid="frame-card" style={{ borderRightWidth: 1 }}>
        Content
      </FrameCard>
    );
    const card = screen.getByTestId("frame-card");
    const frame = card.querySelector(".fc-frame");
    const rim = frame?.querySelector(".fc-rim");
    const inner = rim?.querySelector(".fc-inner");
    const css = container.querySelector("style")?.textContent ?? "";

    expect(card).toHaveAttribute("role", "group");
    expect(card).toHaveAttribute("aria-label", "Example");
    expect(card).toHaveAttribute("data-selected", "true");
    expect(card).toHaveStyle({ borderRightWidth: "0px" });
    expect(card.className).not.toMatch(/(?:^|\s)p-4(?:\s|$)/);
    expect(frame).toBeInTheDocument();
    expect(rim).toBeInTheDocument();
    expect(inner).toHaveTextContent("Content");
    expect(css).toMatch(/\.fc-root\s*\{[^}]*padding:\s*var\(--bezel\)/s);
    expect(css).toMatch(/\.fc-frame\s*\{[^}]*padding:\s*var\(--frame\)/s);
    expect(css).toMatch(/\.fc-rim\s*\{[^}]*padding:\s*var\(--rim\)/s);
    expect(css).toMatch(/\.fc-inner\s*\{[^}]*padding:\s*var\(--card-pad\)/s);
    expect(css).not.toMatch(/liquid-bezel-w|padding:\s*8px|margin:\s*3px/);
  });

  it("keeps the canonical rim when the decorative liquid accent is hidden", () => {
    const { container } = render(<FrameCard liquidBezel={false}>Content</FrameCard>);
    expect(container.querySelector(".fc-rim")).toBeInTheDocument();
    expect(container.querySelector(".fc-liquid")).not.toBeInTheDocument();
  });
});
