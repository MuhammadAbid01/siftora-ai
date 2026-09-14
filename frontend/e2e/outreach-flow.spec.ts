import { test, expect } from "@playwright/test";

// This spec exercises real Supabase Auth plus the FastAPI backend's
// outreach/approval endpoints (fixture providers, so no external API keys
// are needed once Supabase auth works). It requires both a live Supabase
// project and the backend running at NEXT_PUBLIC_API_BASE_URL, so it's
// skipped unless E2E_SUPABASE_LIVE=1 — see specs/phase-4-outreach.md,
// Testing checklist, and specs/phase-1-foundation.md, Risks and
// Assumptions, for why this can't run in this environment.
const liveSupabaseConfigured = process.env.E2E_SUPABASE_LIVE === "1";

test.describe("outreach draft generation and approval", () => {
  test.skip(
    !liveSupabaseConfigured,
    "Requires a live Supabase project and a running backend (set E2E_SUPABASE_LIVE=1)",
  );

  test("a signed-in user can generate, approve, and export an outreach draft", async ({ page }) => {
    const email = `siftora-e2e-${Date.now()}@example.com`;
    const password = "correct horse battery staple";

    await page.goto("/sign-up");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });

    await page.goto("/dashboard/campaigns/new");
    await page
      .getByLabel("Campaign brief")
      .fill("Find design agencies and animation studios in Dubai, UAE.");
    await page.getByRole("button", { name: /create campaign/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/campaigns\/[^/]+$/, { timeout: 15_000 });

    await page.getByRole("button", { name: /generate plan/i }).click();
    await expect(page.getByText("Awaiting approval")).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: /confirm plan/i }).click();
    await expect(page.getByText("Plan approved")).toBeVisible();

    await page.getByRole("button", { name: /start run/i }).click();
    await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 20_000 });

    await page.getByRole("link", { name: "View leads" }).click();
    await expect(page).toHaveURL(/\/leads$/);
    // Northbeam Studio is this brief's one deterministically-qualified
    // fixture company; navigate to whichever lead row shows "Qualified"
    // rather than relying on list order.
    await page.locator("li", { hasText: "Qualified" }).first().click();
    await expect(page.getByRole("heading", { name: "Score breakdown" })).toBeVisible();

    await page.getByRole("button", { name: /generate email draft/i }).click();
    await expect(page.getByRole("heading", { name: /email \(v1\)/i })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText("Approved")).toBeVisible();

    await page.getByRole("link", { name: "Approvals" }).click();
    await expect(page).toHaveURL(/\/dashboard\/approvals$/);
  });
});
