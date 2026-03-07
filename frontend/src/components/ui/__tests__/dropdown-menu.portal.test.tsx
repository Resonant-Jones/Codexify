import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

describe("DropdownMenu", () => {
  it("portals menu content outside overflow-clipped containers", () => {
    const { container } = render(
      <div data-testid="clipper" style={{ overflow: "hidden", width: 120, height: 40 }}>
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Choice A</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    const menu = screen.getByRole("menu");
    const clipper = screen.getByTestId("clipper");

    expect(menu).toBeInTheDocument();
    expect(document.body.contains(menu)).toBe(true);
    expect(clipper.contains(menu)).toBe(false);
    expect(container.contains(menu)).toBe(false);
    expect(menu).toHaveStyle({ width: "max-content" });
    expect(menu.className).toContain("max-w-[min(32rem,calc(100vw-24px))]");
  });
});
