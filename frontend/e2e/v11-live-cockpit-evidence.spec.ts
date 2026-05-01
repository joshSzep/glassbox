import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { expect, type Page, type TestInfo, test } from "@playwright/test";

import { installGlassboxApiFixture, scenarioRoute } from "./fixtures/glassbox-api";

test.describe("v11 live cockpit evidence", () => {
  test("long-session inspection keeps recovery and freshness cues reachable", async ({
    page,
  }, testInfo) => {
    await installGlassboxApiFixture(page, "large-transcript");
    await page.setViewportSize({ height: 900, width: 1440 });

    await page.goto("/app/queues/active");
    await page.getByRole("link", { name: /large-transcript-session/ }).click();
    await page.getByRole("tab", { name: "Actions" }).click();
    const actionsPanel = page.getByRole("tabpanel", { name: "Actions tab panel" });

    await expect(page.getByRole("heading", { name: "large-transcript-session" })).toBeVisible();
    await expect(actionsPanel.getByText("Pending approvals")).toBeVisible();
    await expect(actionsPanel.getByText("Tool retry posture")).toBeVisible();
    await expect(actionsPanel.getByText("Tool attempt recovery")).toBeVisible();
    await expect(actionsPanel.getByText("Compaction recovery")).toBeVisible();
    await expect(actionsPanel.getByText("Provider recovery", { exact: true })).toBeVisible();

    await page.getByRole("tab", { name: "Transcript" }).click();
    await expect(
      page.getByText("Live output is still arriving while approval waits."),
    ).toBeVisible();

    await page.getByRole("tab", { name: "Runtime" }).click();
    await expect(page.getByRole("heading", { name: "Runtime context" })).toBeVisible();
    await expect(page.getByText("Fresh transcript compaction")).toBeVisible();
    await expect(page.getByText("Stale compaction")).toBeVisible();

    await page.getByRole("tab", { name: "Evidence" }).click();
    await expect(page.getByRole("heading", { name: "Event evidence" })).toBeVisible();
    await expect(page.getByText("Projection details")).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await retainEvidence(page, testInfo, {
      notes: [
        "Long-session route kept pending approval, live output, stale tool-attempt recovery, compaction freshness, and provider advisory cues reachable.",
        "Desktop viewport had no horizontal overflow.",
      ],
      scenario: "long-session-inspection",
      status: "passed",
    });
  });

  test("stale verification evidence stays advisory and inspectable", async ({ page }, testInfo) => {
    await installGlassboxApiFixture(page, "artifact-drift");

    await page.goto("/app/sessions/artifact-session?queue=active&tab=evidence");

    await expect(page.getByRole("heading", { name: "Verification cues" })).toBeVisible();
    const verificationSummary = page.getByLabel("Verification summary");
    await expect(verificationSummary.getByText("Blocking evidence", { exact: true })).toBeVisible();
    await expect(verificationSummary.getByText("Advisory evidence", { exact: true })).toBeVisible();
    await expect(page.getByLabel(/Copyable artifact path evals\/impact\.json/)).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await retainEvidence(page, testInfo, {
      notes: [
        "Artifact-backed verification drift remained inspectable in the evidence tab.",
        "Blocking and advisory evidence were separated without treating provider or drift artifacts as live runtime failures.",
      ],
      scenario: "stale-verification-evidence",
      status: "passed",
    });
  });

  test("stream degradation and reconnect evidence preserve selected-session context", async ({
    page,
  }, testInfo) => {
    const fixture = await installGlassboxApiFixture(page, "projection-degraded");

    await page.goto(scenarioRoute("projection-degraded"));

    await expect(page.getByRole("heading", { name: "degraded-session" })).toBeVisible();
    await expect(
      page.getByText("Projection stale: canonical events remain authoritative."),
    ).toBeVisible();

    await page.getByRole("tab", { name: "Evidence" }).click();
    await expect(page.getByRole("heading", { name: "Event evidence" })).toBeVisible();
    await expect(page.getByText("stream degraded")).toBeVisible();
    await expect(page.getByText("Projection details")).toBeVisible();

    await expect
      .poll(() => fixture.eventStreamRequests.length, { timeout: 10_000 })
      .toBeGreaterThan(1);
    await expect(page.getByRole("heading", { name: "degraded-session" })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await retainEvidence(page, testInfo, {
      notes: [
        "Degraded stream control frame remained visible in the evidence pane.",
        `Observed ${fixture.eventStreamRequests.length} stream requests, retaining selected-session context across reconnect attempts.`,
      ],
      scenario: "stream-degradation-reconnect",
      status: "passed",
    });
  });

  test("queue navigation keeps live actions and historical snapshots distinct", async ({
    page,
  }, testInfo) => {
    await installGlassboxApiFixture(page);
    await page.setViewportSize({ height: 844, width: 390 });

    await page.goto("/app");
    await page.getByRole("link", { name: /Questions/ }).click();
    await expect(page.getByRole("heading", { name: "Questions sessions" })).toBeVisible();
    await page.getByRole("link", { name: /session-1/ }).click();
    await expect(page.getByRole("heading", { name: "session-1" })).toBeVisible();
    await page.getByRole("tab", { name: "Actions" }).click();
    await expect(
      page
        .getByRole("tabpanel", { name: "Actions tab panel" })
        .getByText("Answer pending question", { exact: true }),
    ).toBeVisible();
    await page.getByRole("link", { name: /Back to Questions queue/ }).click();

    await page.getByRole("link", { name: /Historical/ }).click();
    await page.getByRole("link", { name: /historical-session/ }).click();
    await expect(page.getByRole("heading", { name: "historical-session" })).toBeVisible();
    await expect(page.getByText("historical-only", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Send prompt" })).toBeDisabled();
    await expectNoHorizontalOverflow(page);

    await retainEvidence(page, testInfo, {
      notes: [
        "Mobile queue navigation preserved the pending-question action path.",
        "Historical snapshot opened as inspect-only work with prompt mutation disabled.",
      ],
      scenario: "queue-navigation-historical-snapshot",
      status: "passed",
    });
  });
});

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

async function retainEvidence(
  page: Page,
  testInfo: TestInfo,
  result: { notes: string[]; scenario: string; status: "passed" },
) {
  const evidenceDir = process.env.GBX_V11_LIVE_COCKPIT_EVIDENCE_DIR;
  if (evidenceDir === undefined || evidenceDir.trim().length === 0) {
    return;
  }

  const rootEvidenceDir = path.isAbsolute(evidenceDir)
    ? evidenceDir
    : path.resolve(process.cwd(), "..", evidenceDir);
  const scenarioDir = path.resolve(rootEvidenceDir, "automated", "playwright", result.scenario);
  await mkdir(scenarioDir, { recursive: true });

  const screenshotPath = path.join(scenarioDir, "screenshot.png");
  await page.screenshot({ fullPage: true, path: screenshotPath });

  const summary = {
    browser: testInfo.project.name,
    notes: result.notes,
    scenario: result.scenario,
    screenshot: screenshotPath,
    status: result.status,
    title: testInfo.title,
    url: page.url(),
    viewport: page.viewportSize(),
  };
  const summaryPath = path.join(scenarioDir, "summary.json");
  await writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  await testInfo.attach(`${result.scenario} evidence`, {
    contentType: "application/json",
    path: summaryPath,
  });
}
