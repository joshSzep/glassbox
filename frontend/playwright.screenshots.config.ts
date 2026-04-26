import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  expect: {
    timeout: 10_000,
  },
  forbidOnly: Boolean(process.env.CI),
  fullyParallel: false,
  outputDir: "test-results/v4-audit-screenshots/playwright-artifacts",
  reporter: process.env.CI ? "github" : "list",
  retries: 0,
  testDir: "e2e",
  testMatch: "v4-audit-screenshots.spec.ts",
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:3211",
    screenshot: "off",
    trace: "retain-on-failure",
    video: "off",
  },
  webServer: {
    command: "V4_AUDIT_SCREENSHOTS=1 pnpm exec next dev --hostname 127.0.0.1 --port 3211",
    reuseExistingServer: false,
    timeout: 120_000,
    url: "http://127.0.0.1:3211/app",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
