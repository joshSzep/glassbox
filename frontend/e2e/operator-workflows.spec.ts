import { expect, test } from "@playwright/test";

import {
  defaultChildSessionId,
  defaultSessionId,
  installGlassboxApiFixture,
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
  await expect(page.getByRole("heading", { name: "Transcript" })).not.toBeVisible();

  await page.goto(`/app/sessions/${sessionId}?queue=active&compare=parent-session&tab=compare`);
  await expect(page.getByRole("heading", { name: "Compare" })).toBeVisible();
  await expect(page.getByText("parent-session")).toBeVisible();
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
