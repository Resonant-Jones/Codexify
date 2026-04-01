import { expect, test } from "@playwright/test";

const DESKTOP_MEDIA_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn7Y6sAAAAASUVORK5CYII=";

test.describe("desktop media contract", () => {
  test.beforeEach(async ({ context }) => {
    await context.addInitScript(({ pngBase64 }) => {
      const invokeCalls: Array<{ command: string; payload: unknown }> = [];
      window.localStorage.setItem("cfy.bootstrap.welcomeDismissed", "1");
      (window as any).__CFY_TEST_TAURI_INVOKE_CALLS__ = invokeCalls;
      (window as any).__TAURI_INTERNALS__ = {};
      (window as any).__CFY_TAURI_CORE__ = {
        invoke: async (command: string, payload?: Record<string, unknown>) => {
          invokeCalls.push({ command, payload: payload ?? null });
          if (command === "desktop_get_runtime_config") {
            return {
              mode: "tauri",
              backendBaseUrl: "http://backend.test",
              apiBaseUrl: "http://backend.test/api",
              sseUrl: "http://backend.test/api/events",
              sharePublicBaseUrl: "http://share.test",
              authMode: "local",
            };
          }
          if (command === "desktop_fetch_media") {
            return {
              contentType: "image/png",
              bytesBase64: pngBase64,
              sizeBytes: 68,
            };
          }
          if (command === "desktop_runtime_preflight_check") {
            return {
              dockerCliInstalled: true,
              dockerComposeAvailable: true,
              dockerDaemonReachable: true,
              ready: true,
            };
          }
          if (command === "desktop_run_setup_cli") {
            return {
              ok: true,
              step: "setup",
            };
          }
          if (command === "desktop_compose_up") {
            return {
              ok: true,
              step: "compose-up",
            };
          }
          if (
            command === "desktop_runtime_readiness_check" ||
            command === "desktop_runtime_health_check"
          ) {
            return {
              ok: true,
              step: "health-check",
              ready: true,
              backendReachable: true,
              startupReady: true,
              redisReady: true,
              chatReady: true,
              llmReady: true,
              checks: [],
            };
          }
          if (command === "desktop_get_api_key") {
            return null;
          }
          return null;
        },
      };
    }, { pngBase64: DESKTOP_MEDIA_PNG_BASE64 });
  });

  test("renders backend-owned gallery images through the desktop fetch path", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("button", { name: "Guardian" }).first()
    ).toBeVisible();

    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent("cfy:gallery:add", {
          detail: {
            items: [
              {
                src_url: "/media/images/desktop-proof.png?sig=proof",
                prompt: "Desktop contract image",
                tag: "uploaded",
              },
            ],
          },
        })
      );
    });

    await page.getByRole("button", { name: "Dashboard" }).click();
    await expect(
      page.getByRole("img", { name: "Desktop contract image" }).first()
    ).toBeVisible();

    await page.getByRole("button", { name: "Gallery" }).click();
    await expect(
      page.getByRole("img", { name: "Desktop contract image" }).first()
    ).toBeVisible();

    const desktopFetchPaths = await page.evaluate(() =>
      ((window as any).__CFY_TEST_TAURI_INVOKE_CALLS__ || [])
        .filter((entry: any) => entry.command === "desktop_fetch_media")
        .map((entry: any) => entry.payload?.path)
    );

    expect(desktopFetchPaths).toContain("/media/images/desktop-proof.png");
  });
});
