import { render, screen } from "@testing-library/react";

import type { SystemPromptSummary } from "@/imprint/api";
import PromptCostIndicator from "../PromptCostIndicator";

function renderIndicator(summary?: SystemPromptSummary | null) {
  render(<PromptCostIndicator summary={summary} />);
  return screen.getByTestId("prompt-cost-indicator");
}

test("renders UNKNOWN state when summary is unavailable", () => {
  const indicator = renderIndicator(undefined);
  expect(indicator).toHaveTextContent("Prompt Cost: UNKNOWN");
  expect(indicator).toHaveTextContent("— tokens");
});

test("renders OK state with token estimate", () => {
  const indicator = renderIndicator({
    estimated_tokens_total: 1200,
    threshold: { warn_tokens: 6000, hard_tokens: 8000, status: "ok" },
  });
  expect(indicator).toHaveTextContent("Prompt Cost: OK");
  expect(indicator).toHaveTextContent("1200 tokens");
});

test("renders WARN state", () => {
  const indicator = renderIndicator({
    estimated_tokens_total: 6400,
    threshold: { warn_tokens: 6000, hard_tokens: 8000, status: "warn" },
  });
  expect(indicator).toHaveTextContent("Prompt Cost: WARN");
  expect(indicator).toHaveTextContent("Approaching token budget.");
});

test("renders HARD state warning copy", () => {
  const indicator = renderIndicator({
    estimated_tokens_total: 9200,
    threshold: { warn_tokens: 6000, hard_tokens: 8000, status: "hard" },
  });
  expect(indicator).toHaveTextContent("Prompt Cost: HARD");
  expect(indicator).toHaveTextContent(
    "High prompt cost. Consider trimming persona/docs context."
  );
});
