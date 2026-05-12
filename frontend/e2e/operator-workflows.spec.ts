import { expect, type Page, test } from "@playwright/test";

import {
  defaultChildSessionId,
  defaultSessionId,
  installGlassboxApiFixture,
  scenarioRoute,
} from "./fixtures/glassbox-api";

const sessionId = defaultSessionId;
const childSessionId = defaultChildSessionId;
const sessionLink = new RegExp(sessionId);

test("operator can browse queues, open a session, stream updates, and resolve actions", async ({
  page,
}) => {
  const fixture = await installGlassboxApiFixture(page);

  await page.goto("/app");

  await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
  await expect(page.getByRole("link", { name: sessionLink })).toBeVisible();

  await page.getByRole("link", { name: /Questions/ }).click();
  await expect(page).toHaveURL(/\/app\/queues\/questions$/);
  await expect(page.getByRole("heading", { name: "Questions sessions" })).toBeVisible();

  await page.getByRole("link", { name: sessionLink }).click();
  await expect(page).toHaveURL(/\/app\/sessions\/session-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();
  await expect(page.getByText("awaiting approval")).toBeVisible();
  await expect(page.getByText("Live SSE update received by the browser.")).toBeVisible();

  await page.getByRole("tab", { name: "Transcript" }).click();
  await expect(page).toHaveURL(/tab=transcript/);
  await expect(page.getByLabel("Session narrative turns")).toBeVisible();
  await expect(page.getByText("Live SSE update received by the browser.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Pending action" })).toBeVisible();

  await page.getByRole("tab", { name: "Timeline" }).click();
  await expect(page).toHaveURL(/tab=timeline/);
  await expect(page.getByLabel("Timeline turns")).toBeVisible();
  await expect(page.getByRole("link", { name: "Active turn" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Fork boundary" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open fork flow for Continue from tool result" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Fork boundary" }).click();
  await expect(page).toHaveURL(/#narrative-turn-1$/);
  await page.getByRole("tab", { name: "Overview" }).click();

  await page.getByLabel("Continue session").fill("Please continue with the next check");
  await page.getByRole("button", { name: "Send prompt" }).click();

  await page.getByLabel("Answer pending question").fill("Use the main branch");
  await page.getByRole("button", { name: "Submit answer" }).click();

  await page.getByRole("button", { name: "Approve" }).click();
  await page.getByRole("button", { name: "Deny" }).click();

  await page.getByRole("button", { name: "Create fork" }).click();
  await page.getByLabel("Fork label").fill("retry with narrower context");
  await page.getByRole("button", { name: "Select Continue from tool result" }).click();
  await page.getByRole("button", { name: "Fork selected point" }).click();

  await expect(page).toHaveURL(/\/app\/sessions\/child-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: childSessionId })).toBeVisible();

  expect(fixture.actions.map((action) => action.url)).toEqual([
    `/sessions/${sessionId}/messages`,
    `/sessions/${sessionId}/questions/question-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/fork`,
  ]);
  expect(fixture.actions[0]?.body).toEqual({ text: "Please continue with the next check" });
  expect(fixture.actions[1]?.body).toEqual({ answer: "Use the main branch" });
  expect(fixture.actions[2]?.body).toEqual({ decision: "approved" });
  expect(fixture.actions[3]?.body).toEqual({ decision: "denied" });
  expect(fixture.actions[4]?.body).toEqual({
    branch_label: "retry with narrower context",
    turn_id: "turn-1",
  });
});

test("operator can complete the primary workflow from the keyboard", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);

  await page.goto("/app");

  await page.getByRole("link", { name: /Questions/ }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/app\/queues\/questions$/);

  await page.getByRole("link", { name: sessionLink }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/app\/sessions\/session-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: sessionId })).toBeFocused();

  await page.getByRole("tab", { name: "Transcript" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("tabpanel", { name: "Transcript tab panel" })).toBeVisible();
  await page.getByRole("link", { name: "Pending action" }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#narrative-turn-1$/);

  await page.getByRole("tab", { name: "Overview" }).focus();
  await page.keyboard.press("Enter");
  await page.getByLabel("Answer pending question").focus();
  await page.keyboard.type("Use the main branch");
  await page.getByRole("button", { name: "Submit answer" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("answer submitted", { exact: true })).toBeVisible();

  await expect(page.getByRole("button", { name: "Approve" })).toBeEnabled();
  await page.getByRole("button", { name: "Approve" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("approval resolved", { exact: true })).toBeVisible();

  await expect(page.getByRole("button", { name: "Create fork" })).toBeEnabled();
  await page.getByRole("button", { name: "Create fork" }).focus();
  await page.keyboard.press("Enter");
  await page.getByLabel("Fork label").focus();
  await page.keyboard.type("keyboard branch");
  await page.getByRole("button", { name: "Select Continue from tool result" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Fork selected point" }).focus();
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/app\/sessions\/child-1\?queue=questions$/);
  expect(fixture.actions.map((action) => action.url)).toEqual([
    `/sessions/${sessionId}/questions/question-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/fork`,
  ]);
});

test("operator console remains reachable in a narrow viewport", async ({ page }) => {
  await installGlassboxApiFixture(page);
  await page.setViewportSize({ height: 844, width: 390 });

  await page.goto("/app");

  await expect(page.getByRole("navigation", { name: "Action queues" })).toBeVisible();
  await expect(page.getByRole("link", { name: sessionLink })).toBeVisible();
});

test("mobile operator can drill into a session, act, and return to queues", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);
  await page.setViewportSize({ height: 844, width: 390 });

  await page.goto("/app");
  await page.getByRole("link", { name: /Questions/ }).click();
  await page.getByRole("link", { name: sessionLink }).click();

  await expect(page).toHaveURL(/\/app\/sessions\/session-1\?queue=questions$/);
  await expect(page.getByRole("link", { name: /Back to Questions queue/ })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Action queues" })).not.toBeVisible();
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();

  await page.getByLabel("Answer pending question").fill("Use the main branch");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await page.getByRole("button", { name: "Approve" }).click();
  await page.getByRole("button", { name: "Create fork" }).click();
  await page.getByLabel("Fork label").fill("mobile fork check");
  await page.getByRole("button", { name: "Select Continue from tool result" }).click();
  await page.getByRole("button", { name: "Fork selected point" }).click();

  await page.getByRole("link", { name: /Back to Questions queue/ }).click();
  await expect(page).toHaveURL(/\/app\/queues\/questions$/);
  await expect(page.getByRole("navigation", { name: "Action queues" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Questions sessions" })).toBeVisible();

  expect(fixture.actions.map((action) => action.url)).toEqual([
    `/sessions/${sessionId}/questions/question-1`,
    `/sessions/${sessionId}/approvals/approval-1`,
    `/sessions/${sessionId}/fork`,
  ]);
});

test("operator can use task controls and budget review from the keyboard", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);
  page.on("dialog", (dialog) => dialog.accept());

  await openClientRoute(page, "/app/tasks/task-1?taskQueue=blocked");

  await expect(page.getByRole("heading", { name: "Task Queue", exact: true })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Selected task inspector" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Task controls" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Why this action" })).toBeVisible();

  await page.getByRole("button", { name: "Continue" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(1);

  await expect(page.getByRole("button", { name: "Pause" })).toBeEnabled();
  await page.getByRole("button", { name: "Pause" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(2);

  await expect(page.getByRole("button", { name: "Resume" })).toBeEnabled();
  await page.getByRole("button", { name: "Resume" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(3);

  const budgetMode = page.getByLabel("Budget mode");
  await expect(page.getByRole("button", { name: "Adjust Budget" })).toBeEnabled();
  await expect(budgetMode).toHaveValue("inspect");
  await budgetMode.selectOption("test-driven");
  await expect(budgetMode).toHaveValue("test-driven");
  await page.getByRole("spinbutton", { name: "Steps" }).fill("3");
  await page.getByRole("button", { name: "Adjust Budget" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(4);

  await page.getByRole("button", { name: "Cancel", exact: true }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(5);

  expect(fixture.actions.map((action) => action.url)).toEqual([
    "/tasks/task-1/continue",
    "/tasks/task-1/pause",
    "/tasks/task-1/resume",
    "/tasks/task-1/budget",
    "/tasks/task-1/cancel",
  ]);
  expect(fixture.actions[3]?.body).toMatchObject({
    budget: { max_steps: 3 },
    mode: "test-driven",
  });
});

test("operator can review memory and repository inspectors from the keyboard", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);
  page.on("dialog", (dialog) => dialog.accept());

  await openClientRoute(page, "/app/memory");
  await expect(page.getByRole("heading", { name: "Memory Inspector" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Active" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByLabel("Search workspace memory").fill("frontend");
  await page.keyboard.press("Tab");
  await page.getByRole("link", { name: /Frontend checks use pnpm/ }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Workspace memory detail" })).toBeVisible();

  await page.getByRole("button", { name: "Confirm", exact: true }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(1);
  await page.getByRole("button", { name: "Invalidate", exact: true }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(2);
  await page.getByRole("button", { name: "Preview Prune", exact: true }).press("Enter");
  await expect(page.getByText("Prune preview")).toBeVisible();
  await expect.poll(() => fixture.actions.length).toBe(3);
  await page.getByRole("button", { name: "Prune", exact: true }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(4);

  await openClientRoute(page, "/app/repository-index");
  await expect(page.getByRole("heading", { name: "Repository Index" })).toBeVisible();
  await page.getByLabel("Search repository intelligence").fill("TaskAutonomyConsole");
  await page.keyboard.press("Tab");
  await page.getByRole("button", { name: "TaskAutonomyConsole" }).press("Enter");
  await expect(page.getByRole("region", { name: "Repository index detail" })).toBeVisible();
  await page.getByRole("button", { name: "Refresh Intelligence" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(5);

  expect(fixture.actions.map((action) => action.url)).toEqual([
    "/memory/memory-1/confirm",
    "/memory/memory-1/invalidate",
    "/memory/memory-1/prune-preview",
    "/memory/memory-1/prune",
    "/repo/index/rebuild",
  ]);
});

test("reviewer can inspect a changeset and generate a brief", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);
  page.on("dialog", (dialog) => dialog.accept());

  await openClientRoute(page, "/app/changesets/changeset-1");

  await expect(
    page.getByRole("heading", { name: "Review dashboard changeset evidence" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review Readiness" })).toBeVisible();
  await expect(page.getByText("deterministic changeset evidence is ready")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Changed Files" })).toBeVisible();
  await expect(page.getByText("4 changed paths")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Repository Intelligence" })).toBeVisible();
  await expect(page.getByText("Repository intelligence suggests:").first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: /frontend\/components\/console\/changeset-console\.tsx/ }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verification" })).toBeVisible();
  await expect(page.getByText("verification readiness passed")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Candidate Adoption" })).toBeVisible();
  await expect(page.getByText("Workspace mutation performed: false")).toBeVisible();
  await expect(page.getByText("Glassbox did not merge").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rejected Alternatives" })).toBeVisible();
  await expect(page.getByText("Try broader refactor")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Brief Artifacts" })).toBeVisible();
  await expect(page.getByText("brief-artifact-1").first()).toBeVisible();

  await page.getByRole("button", { name: "Brief" }).click();
  await expect
    .poll(() => fixture.actions.map((action) => action.url))
    .toContain("/changesets/changeset-1/brief");
  await expect(page.getByText("brief-artifact-2").first()).toBeVisible();

  await page
    .getByRole("link", { name: /frontend\/components\/console\/changeset-console\.tsx/ })
    .click();
  await expect(page).toHaveURL(
    /\/app\/repository-index\?path=frontend%2Fcomponents%2Fconsole%2Fchangeset-console\.tsx$/,
  );
  await expect(page.getByRole("heading", { name: "Repository Index" })).toBeVisible();
  await expect(page.getByLabel("Inspect repository path")).toHaveValue(
    "frontend/components/console/changeset-console.tsx",
  );
});

test("operator can inspect v16 cockpit evidence surfaces", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page, "projection-degraded");
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ height: 900, width: 1280 });

  await page.goto("/app");
  await expect(page.getByRole("region", { name: "Unified operator queue" })).toBeVisible();
  await expect(page.getByRole("listitem", { name: "Maintenance queue lane" })).toBeVisible();
  await expect(page.getByText("Inspect stale projection")).toBeVisible();
  await expect(page.getByText("Projection health is degraded")).toBeVisible();

  await openClientRoute(page, "/app/changesets/changeset-1");
  await expect(page.getByRole("heading", { name: "Evidence Graph Explorer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Changeset Evidence Graph" })).toBeVisible();
  await expect(page.getByLabel("Evidence graph summary")).toContainText("changeset");
  await expect(page.getByText("Review ready claim needs inspection")).toBeVisible();
  await expect(page.getByText("pytest rerun is missing for this claim.")).toBeVisible();
  await expect(page.getByText("Stale pytest result")).toBeVisible();

  await expect(page.getByText("Deterministic checks")).toBeVisible();
  await expect(page.locator("#verification-plan-entry-verification-1")).toContainText(
    "frontend checks",
  );
  await expect(page.getByText("1 skipped live", { exact: true })).toBeVisible();
  await expect(page.getByText("Screen-reader pairing was intentionally not run")).toBeVisible();
  await page.getByRole("button", { name: "Select" }).first().click();
  await expect
    .poll(() => fixture.actions.map((action) => action.url))
    .toContain("/changesets/changeset-1/record-verification");
  await expect(page.getByText("1 retained verification entry recorded.")).toBeVisible();

  await page.setViewportSize({ height: 844, width: 390 });
  await expect(page.getByRole("heading", { name: "Changeset Evidence Graph" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("mobile operator can select a branch-search candidate from the keyboard", async ({ page }) => {
  const fixture = await installGlassboxApiFixture(page);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ height: 844, width: 390 });

  await openClientRoute(page, "/app/branch-search");

  await expect(page.getByRole("heading", { name: "Branch Search" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Branch search list" })).toBeVisible();
  await page.getByRole("button", { name: /Compare repair options/ }).press("Enter");
  await expect(page.getByRole("region", { name: "Branch-search candidates" })).toBeVisible();
  await expect(page.getByText("Candidate selection records review metadata only.")).toBeVisible();

  await page.getByRole("button", { name: "Select Try minimal fix" }).press("Enter");
  await expect.poll(() => fixture.actions.length).toBe(1);
  expect(fixture.actions[0]?.url).toBe("/branch-searches/search-1/candidates/candidate-1/select");
  await expectNoHorizontalOverflow(page);
});

test("operator can switch queue filters and return to a selected session", async ({ page }) => {
  await installGlassboxApiFixture(page);

  await page.goto("/app");
  await page.getByRole("link", { name: /Failures/ }).click();
  await expect(page).toHaveURL(/\/app\/queues\/failures$/);
  await expect(page.getByRole("heading", { name: "Failures sessions" })).toBeVisible();
  await expect(page.getByText("Inspect retryable failure")).toBeVisible();

  await page.getByRole("link", { name: /All/ }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "All sessions" })).toBeVisible();

  await page.getByRole("link", { name: /Questions/ }).click();
  await page.getByRole("link", { name: sessionLink }).click();
  await expect(page).toHaveURL(/\/app\/sessions\/session-1\?queue=questions$/);
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Questions sessions" })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();
});

test("console frame loads from app, queue, and selected-session routes", async ({ page }) => {
  await installGlassboxApiFixture(page);

  for (const route of [
    "/",
    "/app",
    `/app?session=${sessionId}&queue=active`,
    "/app/queues/approvals",
    `/app/sessions/${sessionId}?queue=active`,
  ]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
    await expect(page.getByLabel("Workspace status rail")).toBeVisible();
    await expect(page.getByLabel("Console frame")).toBeVisible();
  }
});

test("operator can open selected-session tabs from direct URLs", async ({ page }) => {
  await installGlassboxApiFixture(page, "compare-view");

  await page.goto(`/app/sessions/${sessionId}?queue=active&tab=runtime`);
  await expect(page.getByRole("heading", { name: sessionId })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runtime context" })).toBeVisible();
  await expect(page.getByText("Working set")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Transcript" })).not.toBeVisible();

  await page.goto(`/app/sessions/${sessionId}?queue=active&tab=evidence`);
  await expect(page.getByRole("heading", { name: "Verification cues" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Event evidence" })).toBeVisible();
  await expect(page.getByLabel("Evidence overview")).toBeVisible();

  await page.goto(`/app/sessions/${sessionId}?queue=active&compare=parent-session&tab=compare`);
  await expect(page.getByRole("heading", { name: "Compare" })).toBeVisible();
  await expect(page.getByText("Difference summary")).toBeVisible();
  await expect(page.getByRole("heading", { name: "parent-session" })).toBeVisible();
  await page.getByRole("button", { name: "Open compared parent-session" }).click();
  await expect(page).toHaveURL(/\/app\/sessions\/parent-session\?queue=active$/);
  await expect(
    page
      .getByRole("complementary", { name: "Selected session inspector" })
      .getByRole("heading", { name: "parent-session" })
      .first(),
  ).toBeVisible();
});

test("operator can navigate lineage targets and compare child sessions", async ({ page }) => {
  await installGlassboxApiFixture(page, "branched-session");

  await page.goto(`/app/sessions/${sessionId}?queue=active&tab=lineage`);
  await expect(
    page
      .getByRole("complementary", { name: "Selected session inspector" })
      .getByRole("heading", { name: sessionId })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Child sessions", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Compare child-1" })).toBeVisible();

  await page.getByRole("button", { name: "Compare child-1" }).click();
  await expect(page).toHaveURL(/compare=child-1/);
  await expect(page).toHaveURL(/tab=compare/);
  await expect(page.getByRole("heading", { name: "Compare" })).toBeVisible();

  await page.getByRole("tab", { name: "Lineage" }).click();
  await page.getByRole("button", { name: "Open child-1" }).click();
  await expect(page).toHaveURL(/\/app\/sessions\/child-1\?queue=active$/);
  await expect(
    page
      .getByRole("complementary", { name: "Selected session inspector" })
      .getByRole("heading", { name: childSessionId })
      .first(),
  ).toBeVisible();

  await page.goBack();
  await expect(
    page
      .getByRole("complementary", { name: "Selected session inspector" })
      .getByRole("heading", { name: sessionId })
      .first(),
  ).toBeVisible();
});

test("operator can inspect artifact-backed verification cues", async ({ page }) => {
  await installGlassboxApiFixture(page, "artifact-drift");

  await page.goto("/app/sessions/artifact-session?queue=active&tab=evidence");
  await expect(page.getByRole("heading", { name: "Verification cues" })).toBeVisible();
  const summary = page.getByLabel("Verification summary");
  await expect(summary).toBeVisible();
  await expect(summary.getByText("Blocking evidence", { exact: true })).toBeVisible();
  await expect(summary.getByText("Advisory evidence", { exact: true })).toBeVisible();
  await expect(summary.getByText("Verified artifacts", { exact: true })).toBeVisible();
  await expect(page.getByLabel(/Copyable artifact path evals\/impact\.json/)).toBeVisible();
});

test("operator can review degraded projection without losing canonical evidence", async ({
  page,
}) => {
  await installGlassboxApiFixture(page, "projection-degraded");

  await page.goto(scenarioRoute("projection-degraded"));
  const inspector = page.getByRole("complementary", { name: "Selected session inspector" });
  await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "degraded-session" })).toBeVisible();
  await expect(
    page.getByText("Projection stale: canonical events remain authoritative."),
  ).toBeVisible();
  await expect(inspector.getByText("projection degraded", { exact: true }).first()).toBeVisible();

  await page.getByRole("tab", { name: "Evidence" }).click();
  await expect(page.getByLabel("Evidence overview")).toBeVisible();
  await expect(page.getByText("Projection details")).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("operator can review a historical session as inspect-only work", async ({ page }) => {
  await installGlassboxApiFixture(page, "historical-session");

  await page.goto(scenarioRoute("historical-session"));
  const inspector = page.getByRole("complementary", { name: "Selected session inspector" });
  await expect(page.getByRole("heading", { name: "historical-session" })).toBeVisible();
  await expect(page.getByText("historical snapshot", { exact: true })).toBeVisible();
  await expect(inspector.getByText("historical-only", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Send prompt" })).toBeDisabled();

  await page.getByRole("tab", { name: "Lineage" }).click();
  await expect(page.getByRole("heading", { name: "Lineage and turns" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("operator sees inline feedback for action failures", async ({ page }) => {
  await installGlassboxApiFixture(page);
  await page.route("**/sessions/*/approvals/*", (route) =>
    route.fulfill({ json: { detail: "approval conflict: already resolved" }, status: 409 }),
  );

  await page.goto(`/app/sessions/${sessionId}?queue=questions`);
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("conflict", { exact: true })).toBeVisible();
  await expect(page.getByText(/Refresh the snapshot before acting again/)).toBeVisible();

  await page.route("**/sessions/*/fork", (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Create fork" }).click();
  await page.getByLabel("Fork label").fill("network retry branch");
  await page.getByRole("button", { name: "Select Continue from tool result" }).click();
  await page.getByRole("button", { name: "Fork selected point" }).click();
  await expect(page.getByText("network error", { exact: true })).toBeVisible();
  await expect(page.getByText(/draft is preserved/i)).toBeVisible();
});

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

async function openClientRoute(page: Page, route: string) {
  await page.goto(route);
  await expect(page).toHaveURL(new RegExp(`${escapeRegExp(route)}$`));
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
