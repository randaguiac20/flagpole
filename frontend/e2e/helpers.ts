// Shared end-to-end helpers. Spec: 002-flagpole-web (each spec seeds its own state, SC-005).
import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";

export const USERS = {
  operator: { email: "alice@flagpole.local", username: "alice", password: "flagpole" },
  viewer: { email: "bob@flagpole.local", username: "bob", password: "flagpole" },
} as const;

/** Sign in through the real identity provider (US1). */
export async function signIn(page: Page, who: keyof typeof USERS): Promise<void> {
  const user = USERS[who];
  await page.goto("/");
  await page.getByTestId("sign-in").click();
  await page.getByLabel(/username|email/i).first().fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);
  await page.getByRole("button", { name: /login|sign in/i }).click();
  await expect(page.getByTestId("identity")).toHaveText(user.email);
}
