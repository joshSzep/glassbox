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
  viewport: string;
  viewportSize: { height: number; width: number };
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

  for (const viewport of viewports) {
    test(`v4 screenshot archive: ${scenario} ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ height: viewport.height, width: viewport.width });
      await installGlassboxApiFixture(page, scenario);

      const route = scenarioRoute(scenario);
      await page.goto(route);
      await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
      await expectNoDevOnlyChrome(page);
      await page.screenshot({
        fullPage: true,
        path: path.join(archiveRoot, `${scenario}.${viewport.name}.png`),
      });

      manifest.push({
        file: `${scenario}.${viewport.name}.png`,
        gitRevision,
        operatorState: scenarioFixtures[scenario].summary,
        route,
        scenario,
        viewport: viewport.name,
        viewportSize: { height: viewport.height, width: viewport.width },
      });
    });
  }
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
        `| ${entry.scenario} | ${entry.viewport} | ${entry.route} | ${entry.operatorState} | [${entry.file}](./${entry.file}) |`,
    );

  return [
    "# v4 Audit Screenshot Archive",
    "",
    `Generated: ${new Date().toISOString()}`,
    `Git revision: ${gitRevision}`,
    "",
    "| Scenario | Viewport | Route | Operator State | Screenshot |",
    "| --- | --- | --- | --- | --- |",
    ...rows,
    "",
  ].join("\n");
}
