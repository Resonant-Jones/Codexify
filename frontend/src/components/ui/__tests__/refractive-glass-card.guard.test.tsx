import React from "react";
import { render, screen } from "@testing-library/react";
import ReactiveGlassCard from "@/components/surface/FrameCard";

function withPatchedCanvas<T>(fn: () => T) {
  const orig = HTMLCanvasElement.prototype.getContext as any;
  // Simulate missing WebGL in JSDOM so guard path runs
  HTMLCanvasElement.prototype.getContext = () => null;
  try { return fn(); } finally {
    HTMLCanvasElement.prototype.getContext = orig;
  }
}

test("renders children even when WebGL context is unavailable", () => {
  withPatchedCanvas(() => {
    render(
      <ReactiveGlassCard wallpaperUrl={null}>
        <div data-testid="kid">hello</div>
      </ReactiveGlassCard>
    );
  });
  expect(screen.getByTestId("kid")).toBeInTheDocument();
});
