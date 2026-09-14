import { test, expect } from "@playwright/test";

// This spec exercises real Supabase Auth (to sign in) plus the FastAPI
// backend's campaign endpoints, so it requires both a live Supabase project
// and the backend running at NEXT_PUBLIC_API_BASE_URL. It is skipped unless
// E2E_SUPABASE_LIVE=1 is set — see specs/phase-2-campaigns.md, Testing
// checklist, and specs/phase-1-foundation.md, Risks and Assumptions, for why
// this can't run in this environment.
const liveSupabaseConfigured = process.env.E2E_SUPABASE_LIVE === "1";

test.describe("campaign creation through plan approval", () => {
  test.skip(
    !liveSupabaseConfigured,
    "Requires a live Supabase project and a running backend (set E2E_SUPABASE_LIVE=1)",
  );

  test("a signed-in user can create a campaign, generate a plan, and approve it", async ({
    page,
  }) => {
    const email = `siftora-e2e-${Date.now()}@example.com`;
    const password = "correct horse battery staple";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });

    await page.getByRole("link", { name: "Campaigns" }).click();
    await expect(page).toHaveURL(/\/dashboard\/campaigns$/);

    await page.getByRole("link", { name: "New campaign" }).click();
    await page
      .getByLabel("Campaign brief")
      .fill("Find design agencies in Dubai with 5-50 employees and an active website.");
    await page.getByRole("button", { name: /create campaign/i }).click();

    await expect(page).toHaveURL(/\/dashboard\/campaigns\/[^/]+$/, { timeout: 15_000 });

    await page.getByRole("button", { name: /generate plan/i }).click();
    await expect(page.getByText("Awaiting approval")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: /confirm plan/i }).click();
    await expect(page.getByText("Plan approved")).toBeVisible();

    await page.getByRole("button", { name: /start run/i }).click();
    await expect(page.getByText("Queued")).toBeVisible();
  });
});
