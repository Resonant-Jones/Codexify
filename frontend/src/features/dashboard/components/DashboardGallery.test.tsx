import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const runtimeState = vi.hoisted(() => ({
  invokeTauriCommandMock: vi.fn(),
  tauriRuntime: false,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  resolveBackendUrl: (path: string) =>
    `http://backend.test${path.startsWith("/") ? path : `/${path}`}`,
  getRuntimeConfigSync: () => ({
    mode: runtimeState.tauriRuntime ? "tauri" : "web",
    backendBaseUrl: "http://backend.test",
    apiBaseUrl: "http://backend.test/api",
    sseUrl: "http://backend.test/api/events",
    sharePublicBaseUrl: "http://share.test",
    authMode: "local",
  }),
  isTauriRuntime: () => runtimeState.tauriRuntime,
  invokeTauriCommand: runtimeState.invokeTauriCommandMock,
}));

import DashboardGallery from "@/features/dashboard/components/DashboardGallery";
import { normalizeMediaUrl } from "@/lib/mediaUrl";

function setViewportWidth(width: number) {
  act(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: width,
    });
    window.dispatchEvent(new Event("resize"));
  });
}

describe("DashboardGallery desktop media rendering", () => {
  beforeEach(() => {
    setViewportWidth(1280);
  });

  afterEach(() => {
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
    vi.restoreAllMocks();
  });

  it("renders dashboard tiles through the desktop fetch contract in Tauri", async () => {
    runtimeState.tauriRuntime = true;
    runtimeState.invokeTauriCommandMock.mockResolvedValue({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:dashboard-image"),
    });

    render(
      <DashboardGallery
        items={[
          {
            id: "dashboard-image-1",
            src: "/media/images/dashboard-tauri.png?sig=abc123#panel",
            prompt: "Dashboard image",
          },
        ]}
        onOpenPreview={vi.fn()}
      />
    );

    const image = await screen.findByRole("img", { name: "Dashboard image" });
    expect(image).toHaveAttribute("src", "blob:dashboard-image");
    expect(runtimeState.invokeTauriCommandMock).toHaveBeenCalledWith(
      "desktop_fetch_media",
      { path: "/media/images/dashboard-tauri.png" }
    );
  });
});

describe("DashboardGallery mobile interaction feedback", () => {
  beforeEach(() => {
    setViewportWidth(390);
  });

  afterEach(() => {
    runtimeState.tauriRuntime = false;
    runtimeState.invokeTauriCommandMock.mockReset();
    setViewportWidth(1280);
    cleanup();
    vi.restoreAllMocks();
  });

  it("applies shared press feedback to phone tiles and releases on activation", () => {
    const onOpenPreview = vi.fn();
    render(
      <DashboardGallery
        items={[
          {
            id: "dashboard-image-1",
            src: "/media/images/dashboard-touch.png",
            prompt: "Dashboard image",
          },
        ]}
        onOpenPreview={onOpenPreview}
      />
    );

    const tile = screen.getByRole("button", { name: "Dashboard image" });
    expect(tile).toHaveClass("mobile-press-feedback");
    expect(tile).toHaveAttribute("data-press-feedback", "idle");

    fireEvent.pointerDown(tile, {
      button: 0,
      buttons: 1,
      isPrimary: true,
      pointerType: "touch",
    });
    expect(tile).toHaveAttribute("data-press-feedback", "pressed");

    fireEvent.click(tile);
    expect(tile).toHaveAttribute("data-press-feedback", "idle");
    expect(onOpenPreview).toHaveBeenCalledTimes(1);
  });

  it("marks the active preview tile and keeps badges tokenized", () => {
    const item = {
      id: "dashboard-image-active",
      src: "/media/images/dashboard-active.png",
      prompt: "Dashboard image",
      source_tag: "generated",
    };

    render(
      <DashboardGallery
        items={[item]}
        activeItemSrc={normalizeMediaUrl(item.src)}
        onOpenPreview={vi.fn()}
      />
    );

    const tile = screen.getByRole("button", { name: "Dashboard image" });
    expect(tile).toHaveAttribute("data-state", "active");

    const badge = screen.getByText("Generated");
    expect(badge).toHaveStyle({
      right: "calc(var(--card-pad) / 2)",
      bottom: "calc(var(--card-pad) / 2)",
      padding: "calc(var(--card-pad) / 6) calc(var(--card-pad) / 2)",
      borderRadius: "999px",
    });
  });

  it("renders every supplied image without a show-more fallback", () => {
    render(
      <DashboardGallery
        items={[
          { id: "dashboard-image-1", src: "/media/images/dashboard-1.png", prompt: "One" },
          { id: "dashboard-image-2", src: "/media/images/dashboard-2.png", prompt: "Two" },
          { id: "dashboard-image-3", src: "/media/images/dashboard-3.png", prompt: "Three" },
          { id: "dashboard-image-4", src: "/media/images/dashboard-4.png", prompt: "Four" },
          { id: "dashboard-image-5", src: "/media/images/dashboard-5.png", prompt: "Five" },
        ]}
        onOpenPreview={vi.fn()}
      />
    );

    expect(screen.getAllByRole("button", { name: /^(One|Two|Three|Four|Five)$/ })).toHaveLength(5);
    expect(screen.getByRole("button", { name: "Five" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Show/i })).not.toBeInTheDocument();

    const tile = screen.getByRole("button", { name: "One" });
    expect(tile).toHaveClass("mobile-press-feedback");
    expect(tile).toHaveAttribute("data-press-feedback", "idle");

    fireEvent.pointerDown(tile, {
      button: 0,
      buttons: 1,
      isPrimary: true,
      pointerType: "touch",
    });
    expect(tile).toHaveAttribute("data-press-feedback", "pressed");

    fireEvent.click(tile);
    expect(tile).toHaveAttribute("data-press-feedback", "idle");
  });
});
