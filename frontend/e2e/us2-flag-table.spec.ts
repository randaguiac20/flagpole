// US2 — the flag table per environment. Spec: 002-flagpole-web.
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("US2-1/2/3 rows show the selected environment and switch with the tabs", async ({ page }) => {
  await signIn(page, "operator");
  await expect(page.getByTestId("flag-row-new_banner")).toBeVisible();

  // Put dev into a known state through the UI, then compare the tabs.
  await page.getByTestId("flag-enabled-new_banner").check();
  await page.getByTestId("flag-rollout-new_banner").fill("25");
  await page.getByTestId("flag-save-new_banner").click();
  await expect(page.getByTestId("notice-success")).toBeVisible();

  await expect(page.getByTestId("env-tab-dev")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("flag-enabled-new_banner")).toBeChecked();
  await expect(page.getByTestId("flag-rollout-new_banner")).toHaveValue("25");

  await page.getByTestId("env-tab-prod").click();
  await expect(page.getByTestId("env-tab-prod")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("flag-enabled-new_banner")).not.toBeChecked();
  await expect(page.getByTestId("flag-rollout-new_banner")).toHaveValue("0");
});
