import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it } from "vitest";

import GuardianPresence from "@/features/chat/components/GuardianPresence";
import type { RuntimeVisualState } from "@/shared/runtimeVisualState";

function visualState(key: RuntimeVisualState["key"]): RuntimeVisualState {
  return {
    key,
    label: key,
    tone: "neutral",
    isTerminal: key === "complete" || key === "error",
    isBlocking: key === "warming" || key === "error",
  };
}

describe("GuardianPresence", () => {
  it("renders a deterministic neutral resting bubble using the Guardian initial", () => {
    render(<GuardianPresence guardianName="  Aster Jones " />);

    const presence = screen.getByTestId("guardian-presence");
    expect(presence).toHaveTextContent("A");
    expect(presence).toHaveAttribute("data-presence-state", "idle");
    expect(presence).toHaveAttribute("aria-hidden", "true");
    expect(presence.style.background).toBe("var(--panel-bg)");
  });

  it.each([
    [
      "queued",
      "var(--info-surface, var(--accent-weak))",
      "var(--info-text, var(--accent))",
    ],
    [
      "starting",
      "var(--info-surface, var(--accent-weak))",
      "var(--info-text, var(--accent))",
    ],
    ["warming", "var(--accent-weak)", "var(--accent)"],
    ["delayed", "var(--accent-weak)", "var(--accent)"],
    ["generating", "var(--accent-strong)", "var(--text-on-accent, var(--text))"],
    ["complete", "var(--accent)", "var(--text-on-accent, var(--text))"],
    [
      "error",
      "var(--danger-surface, var(--accent-weak))",
      "var(--danger-text, var(--text))",
    ],
  ] as const)("maps %s to its token-only color treatment", (key, background, color) => {
    render(<GuardianPresence visualState={visualState(key)} />);

    const presence = screen.getByTestId("guardian-presence");
    expect(presence).toHaveAttribute("data-presence-state", key);
    expect(presence.style.background).toBe(background);
    expect(presence.style.color).toBe(color);
    expect(presence.style.borderColor).toMatch(/^var\(/);
    expect(presence.style.background).not.toMatch(/#[0-9a-f]{3,8}|rgb|hsl/i);
    expect(presence.style.color).not.toMatch(/#[0-9a-f]{3,8}|rgb|hsl/i);
  });

  it("keeps dimensions token-derived and does not invent a runtime state", () => {
    render(<GuardianPresence size="md" />);

    const presence = screen.getByTestId("guardian-presence");
    expect(presence).toHaveAttribute("data-presence-state", "idle");
    expect(presence.style.width).toBe("calc(var(--card-pad) * 3)");
    expect(presence.style.height).toBe("calc(var(--card-pad) * 3)");
  });
});
