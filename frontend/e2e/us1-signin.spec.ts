// US1 — sign in, roles, sign out. Spec: 002-flagpole-web.
import { expect, test } from "@playwright/test";
import { USERS, signIn } from "./helpers";

test("US1-1 a signed-out visitor sees only sign in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("sign-in")).toBeVisible();
  await expect(page.getByTestId("identity")).toHaveCount(0);
  await expect(page.getByTestId("nav-flags")).toHaveCount(0);
});

test("US1-2 an operator signs in and sees their identity and role", async ({ page }) => {
  await signIn(page, "operator");
  await expect(page.getByTestId("identity")).toHaveText(USERS.operator.email);
  await expect(page.getByTestId("role")).toHaveText("operator");
});

test("US1-3 a viewer sees the viewer role", async ({ page }) => {
  await signIn(page, "viewer");
  await expect(page.getByTestId("role")).toHaveText("viewer");
});

test("US1-4 signing out returns to the signed-out screen and survives a reload", async ({ page }) => {
  await signIn(page, "operator");
  await page.getByTestId("sign-out").click();
  await expect(page.getByTestId("sign-in")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("sign-in")).toBeVisible();
  await expect(page.getByTestId("identity")).toHaveCount(0);
});
