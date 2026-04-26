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
  await expect(page.getByText("Live SSE update received by the browser.")).toBeVisible();

  await page.getByLabel("Continue session").fill("Please continue with the next check");
  await page.getByRole("button", { name: "Send prompt" }).click();

  await page.getByLabel("Answer pending question").fill("Use the main branch");
  await page.getByRole("button", { name: "Submit answer" }).click();

  await page.getByRole("button", { name: "Approve" }).click();
  await page.getByRole("button", { name: "Deny" }).click();

  await page.getByLabel("Create fork").fill("retry with narrower context");
  await page.getByRole("button", { name: "Fork Continue from tool result" }).click();

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
