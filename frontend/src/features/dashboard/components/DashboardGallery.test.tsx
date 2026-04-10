import { render, screen } from "@testing-library/react";
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

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
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
