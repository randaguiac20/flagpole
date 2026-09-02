// US3 — operators change state and create flags; viewers cannot. Spec: 002-flagpole-web.
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("US3-1 an operator toggles a flag and sets its rollout", async ({ page }) => {
  await signIn(page, "operator");
  const toggle = page.getByTestId("flag-enabled-new_banner");
  const rollout = page.getByTestId("flag-rollout-new_banner");

  await toggle.check();
  await rollout.fill("40");
  await expect(page.getByTestId("flag-dirty-new_banner")).toBeVisible();
  await page.getByTestId("flag-save-new_banner").click();

  await expect(page.getByTestId("notice-success")).toContainText("new_banner");
  await expect(page.getByTestId("flag-dirty-new_banner")).toHaveCount(0);
  await expect(toggle).toBeChecked();
  await expect(rollout).toHaveValue("40");

  // The change is visible in the audit log (US4-1 from the operator's side).
  await page.getByTestId("nav-audit").click();
  await expect(page.locator('[data-testid^="audit-row-"]').first()).toContainText("new_banner");
});

test("US3-5 an operator creates a flag; a duplicate key shows the conflict message", async ({ page }) => {
  await signIn(page, "operator");
  // Fixed, not clock-derived: the suite starts from a fresh database, so the key is free every run.
  const key = "demo_created_by_e2e";
  await page.getByTestId("create-key").fill(key);
  await page.getByTestId("create-description").fill("created by the e2e suite");
  await page.getByTestId("create-submit").click();

  await expect(page.getByTestId(`flag-row-${key}`)).toBeVisible();
  await expect(page.getByTestId(`flag-enabled-${key}`)).not.toBeChecked();
  await expect(page.getByTestId(`flag-rollout-${key}`)).toHaveValue("0");

  await page.getByTestId("create-key").fill(key);
  await page.getByTestId("create-submit").click();
  await expect(page.getByTestId("create-error")).toContainText("flag already exists");
});

test("US3-3/6 every write control is disabled for a viewer", async ({ page }) => {
  await signIn(page, "viewer");
  await expect(page.getByTestId("viewer-hint")).toHaveCount(1);
  await expect(page.getByTestId("flag-enabled-new_banner")).toBeDisabled();
  await expect(page.getByTestId("flag-rollout-new_banner")).toBeDisabled();
  await expect(page.getByTestId("flag-save-new_banner")).toBeDisabled();
  await expect(page.getByTestId("create-key")).toBeDisabled();
  await expect(page.getByTestId("create-submit")).toBeDisabled();
});
