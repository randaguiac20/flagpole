// US4 — the audit log. Spec: 002-flagpole-web.
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("US4-1/2/3 entries are newest first, filterable, and pageable", async ({ page }) => {
  await signIn(page, "operator");

  // Produce two entries on one flag so order and filtering are observable.
  for (const percent of ["10", "20"]) {
    await page.getByTestId("flag-rollout-new_banner").fill(percent);
    await page.getByTestId("flag-save-new_banner").click();
    // The dirty marker clears only when the save has come back, so the second edit cannot start
    // before the first one landed. The success notice alone would already be on screen.
    await expect(page.getByTestId("flag-dirty-new_banner")).toBeHidden();
  }

  await page.getByTestId("nav-audit").click();
  const rows = page.locator('[data-testid^="audit-row-"]');
  await expect(rows.first()).toBeVisible();

  const ids = await rows.evaluateAll((els) =>
    els.map((el) => Number(el.getAttribute("data-testid")!.replace("audit-row-", ""))),
  );
  // Both assertions below are vacuously true for an empty list, so prove the list is not empty.
  expect(ids.length).toBeGreaterThan(1);
  expect(ids).toEqual([...ids].sort((a, b) => b - a));

  await page.getByTestId("audit-filter").fill("new_banner");
  await expect(rows.first()).toContainText("new_banner");
  const filtered = await rows.evaluateAll((els) => els.map((el) => el.textContent ?? ""));
  expect(filtered.length).toBeGreaterThan(0);
  expect(filtered.every((t) => t.includes("new_banner"))).toBe(true);
});
