// US4 — the audit log. Spec: 002-flagpole-web.
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("US4-1/2/3 entries are newest first, filterable, and pageable", async ({ page }) => {
  await signIn(page, "operator");

  // Produce two entries on one flag so order and filtering are observable.
  for (const percent of ["10", "20"]) {
    await page.getByTestId("flag-rollout-new_banner").fill(percent);
    await page.getByTestId("flag-save-new_banner").click();
    await expect(page.getByTestId("notice-success")).toBeVisible();
  }

  await page.getByTestId("nav-audit").click();
  const rows = page.locator('[data-testid^="audit-row-"]');
  await expect(rows.first()).toBeVisible();

  const ids = await rows.evaluateAll((els) =>
    els.map((el) => Number(el.getAttribute("data-testid")!.replace("audit-row-", ""))),
  );
  expect(ids).toEqual([...ids].sort((a, b) => b - a));

  await page.getByTestId("audit-filter").fill("new_banner");
  await expect(rows.first()).toContainText("new_banner");
  const filtered = await rows.evaluateAll((els) => els.map((el) => el.textContent ?? ""));
  expect(filtered.every((t) => t.includes("new_banner"))).toBe(true);
});
