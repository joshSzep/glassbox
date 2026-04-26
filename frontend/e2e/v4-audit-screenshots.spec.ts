import { expect, type Page, test } from "@playwright/test";
import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  installGlassboxApiFixture,
  scenarioFixtures,
  scenarioRoute,
  type ScreenshotScenarioId,
} from "./fixtures/glassbox-api";

const archiveRoot = path.join(process.cwd(), "test-results", "v4-audit-screenshots");
const selectedScenario = process.env.V4_AUDIT_SCENARIO as ScreenshotScenarioId | undefined;
const gitRevision = process.env.V4_AUDIT_REVISION ?? "unknown";

const viewports = [
  { height: 900, name: "desktop", width: 1440 },
  { height: 844, name: "mobile", width: 390 },
] as const;

type ManifestEntry = {
  file: string;
  gitRevision: string;
  operatorState: string;
  route: string;
  scenario: ScreenshotScenarioId;
  view: string;
  viewport: string;
  viewportSize: { height: number; width: number };
};

type ScreenshotView = {
  name: string;
  route: string;
};

const manifest: ManifestEntry[] = [];

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  await rm(archiveRoot, { force: true, recursive: true });
  await mkdir(archiveRoot, { recursive: true });
});

for (const scenario of Object.keys(scenarioFixtures) as ScreenshotScenarioId[]) {
  if (selectedScenario !== undefined && scenario !== selectedScenario) {
    continue;
  }

  const views = screenshotViewsForScenario(scenario);

  for (const view of views) {
    for (const viewport of viewports) {
      test(`v4 screenshot archive: ${scenario} ${view.name} ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize({ height: viewport.height, width: viewport.width });
        await installGlassboxApiFixture(page, scenario);

        await page.goto(view.route);
        await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
        if (view.name === "timeline") {
          await expect(page.getByLabel("Timeline turns")).toBeVisible();
        }
        if (view.name === "lineage") {
          await expect(page.getByLabel("Current lineage anchor")).toBeVisible();
        }
        if (view.name === "evidence") {
          await expect(page.getByLabel("Evidence overview")).toBeVisible();
        }
        if (view.name === "runtime") {
          await expect(page.getByRole("heading", { name: "Runtime context" })).toBeVisible();
        }
        await expectNoDevOnlyChrome(page);

        const file =
          view.name === "default"
            ? `${scenario}.${viewport.name}.png`
            : `${scenario}.${view.name}.${viewport.name}.png`;

        await page.screenshot({
          fullPage: true,
          path: path.join(archiveRoot, file),
        });

        manifest.push({
          file,
          gitRevision,
          operatorState: scenarioFixtures[scenario].summary,
          route: view.route,
          scenario,
          view: view.name,
          viewport: viewport.name,
          viewportSize: { height: viewport.height, width: viewport.width },
        });
      });
    }
  }
}

function screenshotViewsForScenario(scenario: ScreenshotScenarioId): ScreenshotView[] {
  const route = scenarioRoute(scenario);
  const views = [{ name: "default", route }];

  if (
    ["branched-session", "failed-session", "live-session", "pending-approval"].includes(scenario)
  ) {
    views.push({ name: "timeline", route: routeWithTab(route, "timeline") });
  }

  if (["branched-session", "historical-session", "live-session"].includes(scenario)) {
    views.push({ name: "lineage", route: routeWithTab(route, "lineage") });
  }

  if (
    ["artifact-drift", "large-transcript", "live-session", "projection-degraded"].includes(scenario)
  ) {
    views.push({ name: "evidence", route: routeWithTab(route, "evidence") });
  }

  if (["artifact-drift", "large-transcript"].includes(scenario)) {
    views.push({ name: "runtime", route: routeWithTab(route, "runtime") });
  }

  return views;
}

function routeWithTab(route: string, tab: string): string {
  const url = new URL(route, "http://glassbox.local");
  url.searchParams.set("tab", tab);
  return `${url.pathname}${url.search}`;
}

test.afterAll(async () => {
  await writeFile(
    path.join(archiveRoot, "manifest.json"),
    `${JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        gitRevision,
        scenarios: manifest,
      },
      null,
      2,
    )}\n`,
  );
  await writeFile(path.join(archiveRoot, "index.md"), renderIndex(manifest));
});

async function expectNoDevOnlyChrome(page: Page): Promise<void> {
  const visibleDevElements = await page.evaluate(() => {
    const devChromeSelectors = [
      "[data-nextjs-toast]",
      ".nextjs-toast",
      ".dev-tools-indicator-menu",
      "#devtools-indicator",
    ];
    const candidates = Array.from(
      document.querySelectorAll(
        "nextjs-portal, script[data-nextjs-dev-overlay], [data-nextjs-toast]",
      ),
    );

    for (const element of Array.from(document.querySelectorAll("nextjs-portal"))) {
      if (element.shadowRoot !== null) {
        candidates.push(
          ...Array.from(element.shadowRoot.querySelectorAll(devChromeSelectors.join(","))),
        );
      }
    }

    return candidates.filter(isVisibleDevElement).map((element) => ({
      className: String((element as HTMLElement).className ?? ""),
      id: (element as HTMLElement).id,
      tagName: element.tagName.toLowerCase(),
      text: (element.textContent ?? "").trim().slice(0, 80),
    }));

    function isVisibleDevElement(element: Element): boolean {
      const htmlElement = element as HTMLElement;
      const style = window.getComputedStyle(htmlElement);
      const rect = htmlElement.getBoundingClientRect();

      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0" &&
        rect.width > 0 &&
        rect.height > 0
      );
    }
  });

  expect(visibleDevElements).toEqual([]);
}

function renderIndex(entries: ManifestEntry[]): string {
  const rows = entries
    .sort((left, right) =>
      `${left.scenario}.${left.viewport}`.localeCompare(`${right.scenario}.${right.viewport}`),
    )
    .map(
      (entry) =>
        `| ${entry.scenario} | ${entry.view} | ${entry.viewport} | ${entry.route} | ${entry.operatorState} | [${entry.file}](./${entry.file}) |`,
    );

  return [
    "# v4 Audit Screenshot Archive",
    "",
    `Generated: ${new Date().toISOString()}`,
    `Git revision: ${gitRevision}`,
    "",
    "| Scenario | View | Viewport | Route | Operator State | Screenshot |",
    "| --- | --- | --- | --- | --- | --- |",
    ...rows,
    "",
  ].join("\n");
}
