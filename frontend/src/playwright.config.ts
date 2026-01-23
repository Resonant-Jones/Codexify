import { defineConfig, devices } from '@playwright/test';

const baseURL = (process.env.PW_BASE_URL || 'http://127.0.0.1:5173').replace(/\/$/, '');

const envFlag = (value: string | undefined, fallback: boolean) => {
  if (!value) return fallback;
  const normalized = value.trim().toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true;
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false;
  return fallback;
};

const reuseExistingServer = envFlag(
  process.env.PW_REUSE_EXISTING_SERVER,
  !process.env.CI
);
const startWebServer = envFlag(
  process.env.PW_START_WEBSERVER,
  !process.env.PW_BASE_URL
);

export default defineConfig({
  testDir: './tests/playwright',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1920, height: 1080 } },
    },
  ],
  webServer: startWebServer
    ? {
        command: 'pnpm dev --host 127.0.0.1',
        url: baseURL,
        reuseExistingServer,
        timeout: 120000,
      }
    : undefined,
});
