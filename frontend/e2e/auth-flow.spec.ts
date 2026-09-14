import { test, expect } from "@playwright/test";

// These specs exercise real Supabase Auth (sign-up, session persistence,
// sign-out) and therefore require a live Supabase project. They are skipped
// unless E2E_SUPABASE_LIVE=1 is set, so CI and offline runs do not silently
// pass without ever contacting Supabase — see specs/phase-1-foundation.md,
// Risks and Assumptions.
const liveSupabaseConfigured = process.env.E2E_SUPABASE_LIVE === "1";

test.describe("sign-up to dashboard", () => {
  test.skip(!liveSupabaseConfigured, "Requires a live Supabase project (set E2E_SUPABASE_LIVE=1)");

  test("a new user can sign up, land on the dashboard, and sign out", async ({ page }) => {
    const email = `siftora-e2e-${Date.now()}@example.com`;
    const password = "correct horse battery staple";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
    await expect(page.getByText(email)).toBeVisible();

    await page.reload();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page).toHaveURL("/");
  });
});
