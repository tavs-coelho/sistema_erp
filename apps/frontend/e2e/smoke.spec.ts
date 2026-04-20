/**
 * Smoke tests: login → dashboard → logout (and dark mode toggle).
 *
 * Prerequisites:
 *   1. Backend running.
 *   2. `npm run dev` in apps/frontend (or set PLAYWRIGHT_BASE_URL).
 *
 * Run: npx playwright test
 */

import { expect, test } from "@playwright/test";

const USER = "admin1";
const PASS = "demo123";

test.describe("Smoke – Login / Dashboard / Logout", () => {
  test("unauthenticated visit redirects to /login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login page renders form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /acesso ao sistema/i })).toBeVisible();
    await expect(page.getByLabel(/usuário/i)).toBeVisible();
    await expect(page.getByLabel(/senha/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /entrar/i })).toBeVisible();
  });

  test("invalid credentials show error toast", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usuário/i).fill("wrong");
    await page.getByLabel(/senha/i).fill("wrong");
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(
      page.locator(".toast-stack-item.error, .notice.error, .alert.error").first(),
    ).toBeVisible({ timeout: 6000 });
  });

  test("login with valid credentials lands on dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usuário/i).fill(USER);
    await page.getByLabel(/senha/i).fill(PASS);
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10000 });
    await expect(page.getByRole("heading", { name: /painel geral/i })).toBeVisible();
    await expect(page.locator(".app-sidebar")).toBeVisible();
  });

  test("logout returns to /login", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usuário/i).fill(USER);
    await page.getByLabel(/senha/i).fill(PASS);
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10000 });
    await page.getByRole("button", { name: /sair/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 6000 });
  });

  test("dark mode toggle cycles system → dark → light → system", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usuário/i).fill(USER);
    await page.getByLabel(/senha/i).fill(PASS);
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10000 });

    const toggle = page.getByRole("button", { name: /alternar modo escuro/i });
    await expect(toggle).toBeVisible();

    const html = page.locator("html");
    await expect(html).not.toHaveAttribute("data-color-scheme");

    await toggle.click();
    await expect(html).toHaveAttribute("data-color-scheme", "dark");

    await toggle.click();
    await expect(html).toHaveAttribute("data-color-scheme", "light");

    await toggle.click();
    await expect(html).not.toHaveAttribute("data-color-scheme");
  });

  test("authenticated user navigates to a module page", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/usuário/i).fill(USER);
    await page.getByLabel(/senha/i).fill(PASS);
    await page.getByRole("button", { name: /entrar/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10000 });
    await page.locator(".nav-link", { hasText: "Compras" }).click();
    await expect(page).toHaveURL(/\/compras/);
    await expect(page.getByRole("heading", { name: /compras/i }).first()).toBeVisible();
  });
});
