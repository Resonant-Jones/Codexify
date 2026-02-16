import { render, screen } from "@testing-library/react";

import type { SystemPromptSummary } from "@/imprint/api";
import PromptCostIndicator from "../PromptCostIndicator";

function renderIndicator(
  summary?: SystemPromptSummary | null,
  variant: "banner" | "popover" = "popover"
) {
  render(<PromptCostIndicator summary={summary} variant={variant} />);
  return screen.getByTestId("prompt-cost-indicator");
}

test("renders UNKNOWN state in popover mode when summary is unavailable", () => {
  const indicator = renderIndicator(undefined);
  expect(indicator).toHaveTextContent("Prompt Cost: UNKNOWN");
  expect(indicator).toHaveTextContent("Prompt estimate unavailable.");
  expect(indicator).toHaveTextContent("Tokens: —");
});

test("renders OK state with token estimate in popover mode", () => {
  const indicator = renderIndicator({
    estimated_tokens_total: 1200,
    threshold: { warn_tokens: 6000, hard_tokens: 8000, status: "ok" },
  });
  expect(indicator).toHaveTextContent("Prompt Cost: OK");
  expect(indicator).toHaveTextContent("Within prompt budget.");
  expect(indicator).toHaveTextContent("Tokens: 1200");
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

test("renders compact popover output without banner wrapper", () => {
  const indicator = renderIndicator({
    estimated_tokens_total: 1500,
    threshold: { warn_tokens: 6000, hard_tokens: 8000, status: "ok" },
  });
  expect(indicator).toHaveAttribute("data-variant", "popover");
  expect(indicator).not.toHaveClass("mx-4");
  expect(indicator).not.toHaveClass("rounded-lg");
  expect(indicator).not.toHaveClass("border");
  expect(screen.queryByTestId("prompt-cost-toggle-tokens")).not.toBeInTheDocument();
});
