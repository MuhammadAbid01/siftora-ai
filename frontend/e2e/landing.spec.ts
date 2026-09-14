import { test, expect } from "@playwright/test";

test.describe("landing page", () => {
  test("shows the hero, demo data badge, and footer CTA", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toContainText("Siftora");
    await expect(page.getByText("Demo data").first()).toBeVisible();
    await expect(page.getByRole("link", { name: "GitHub" })).toBeVisible();
  });

  test("Start Campaign CTA navigates to sign-up", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Start Campaign" }).first().click();
    await expect(page).toHaveURL(/\/sign-up$/);
  });

  test("View Demo CTA scrolls to the demo section", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "View Demo" }).click();
    await expect(page).toHaveURL(/#demo$/);
  });

  test("mobile menu opens and exposes navigation links", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    const toggle = page.getByRole("button", { name: /open menu/i });
    await toggle.click();

    await expect(page.getByRole("navigation", { name: "Mobile" })).toBeVisible();
    await expect(page.getByRole("button", { name: /close menu/i })).toBeVisible();
  });
});
