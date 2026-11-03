/** Real browser → Next/Nginx → FastAPI → PostgreSQL functional integration. */
import { expect, test, type Page } from "@playwright/test";

const USER = "admin2";  // CI/demo only, never a production account
const PASS = "demo123";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/usuário/i).fill(USER);
  await page.getByLabel(/senha/i).fill(PASS);
  await page.getByRole("button", { name: /^entrar$/i }).click();
  await expect(page).toHaveURL("/", { timeout: 30000 });
  await expect(page.getByRole("heading", { name: /painel geral/i })).toBeVisible();
}

test("unauthenticated user is sent to login and can see public transparency", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/public");
  await expect(page.getByRole("heading", { name: /portal da transparência/i })).toBeVisible();
});

test("login creates HttpOnly cookies, not JavaScript bearer storage", async ({ page }) => {
  await login(page);
  const cookies = await page.context().cookies();
  expect(cookies.find((cookie) => cookie.name === "erp_access")?.httpOnly).toBe(true);
  expect(cookies.find((cookie) => cookie.name === "erp_refresh")?.httpOnly).toBe(true);
  const access = await page.evaluate(() => window.localStorage.getItem("access_token"));
  expect(access).toBeNull();
  const me = await page.evaluate(async () => {
    const result = await fetch("/api/auth/browser/me", { credentials: "same-origin" });
    return result.status;
  });
  expect(me).toBe(200);
});

test("protected mutations require signed same-origin CSRF", async ({ page }) => {
  await login(page);
  const response = await page.evaluate(async () => {
    const result = await fetch("/api/core/departments", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Must fail because CSRF is absent" }),
    });
    return result.status;
  });
  expect(response).toBe(403);
});

test("session refresh rotates HttpOnly credential and keeps dashboard active", async ({ page }) => {
  await login(page);
  const initial = (await page.context().cookies()).find((c) => c.name === "erp_refresh")?.value;
  const status = await page.evaluate(async () => {
    const csrf = document.cookie.split("; ").find((x) => x.startsWith("erp_csrf="))?.split("=")[1];
    const result = await fetch("/api/auth/browser/refresh", {
      method: "POST", credentials: "same-origin",
      headers: { "X-CSRF-Token": decodeURIComponent(csrf || "") },
    });
    const payload = await result.json();
    return { status: result.status, leaked: Boolean(payload.access_token || payload.refresh_token) };
  });
  expect(status).toEqual({ status: 200, leaked: false });
  const rotated = (await page.context().cookies()).find((c) => c.name === "erp_refresh")?.value;
  expect(rotated).not.toBe(initial);
  await page.reload();
  await expect(page.getByRole("heading", { name: /painel geral/i })).toBeVisible();
});

test("full accounting cycle persists and appears in transparency", async ({ page }) => {
  await login(page);
  await page.goto("/fase-2");
  await expect(page.getByRole("heading", { name: /execução orçamentária e financeira/i })).toBeVisible();
  const result = await page.evaluate(async () => {
    const csrf = document.cookie.split("; ").find((x) => x.startsWith("erp_csrf="))?.split("=")[1];
    const unique = Date.now().toString();
    const get = async (path: string) => {
      const response = await fetch(`/api${path}`, { credentials: "same-origin" });
      if (!response.ok) throw new Error(`GET ${path}: ${response.status}`);
      return response.json();
    };
    const post = async (path: string, payload?: object) => {
      const response = await fetch(`/api${path}`, {
        method: "POST", credentials: "same-origin",
        headers: {
          "X-CSRF-Token": decodeURIComponent(csrf || ""),
          ...(payload ? { "Content-Type": "application/json" } : {}),
        },
        body: payload ? JSON.stringify(payload) : undefined,
      });
      if (!response.ok) throw new Error(`POST ${path}: ${response.status} ${await response.text()}`);
      return response.json();
    };
    const year = await post("/core/fiscal-years", { year: 2043 });
    const department = await post("/core/departments", { name: `Departamento E2E ${unique}` });
    const vendor = await post("/accounting/vendors", { name: `Fornecedor E2E ${unique}`, document: `E2E-${unique}` });
    const budget = await post("/accounting/budget-allocations", {
      code: `E2E-${unique.slice(-12)}`, description: "Dotação de teste E2E",
      amount: 1200, fiscal_year_id: year.id,
    });
    const commitment = await post("/accounting/commitments", {
      number: `EMP-${unique.slice(-12)}`, description: "Serviço de teste E2E",
      amount: 1000, fiscal_year_id: year.id, department_id: department.id, vendor_id: vendor.id,
    });
    await post(`/accounting/liquidate/${commitment.id}`);
    await post("/accounting/payments", {
      commitment_id: commitment.id, amount: 1000, payment_date: "2026-11-03",
    });
    const paid = await get(`/accounting/commitments?status=pago&page=1&size=100`);
    const publicStats = await get("/public/stats");
    return {
      budgetCreated: budget.id > 0,
      paid: paid.items.some((x: { id: number }) => x.id === commitment.id),
      published: publicStats.empenhos.total > 0,
    };
  });
  expect(result).toEqual({ budgetCreated: true, paid: true, published: true });
});

test("logout revokes browser session and clears HttpOnly cookies", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: /sair/i }).first().click();
  await expect(page).toHaveURL(/\/login/);
  const cookies = await page.context().cookies();
  expect(cookies.some((c) => c.name === "erp_access" || c.name === "erp_refresh")).toBe(false);
  await page.goto("/compras");
  await expect(page).toHaveURL(/\/login/);
});
