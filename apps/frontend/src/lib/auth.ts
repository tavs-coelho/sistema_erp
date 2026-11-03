"use client";

/** Same-origin browser transport. No JWT is exposed to JavaScript. */
export const API_URL = "/api";

export function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const prefix = `${name}=`;
  const found = document.cookie.split(";").map((entry) => entry.trim())
    .find((entry) => entry.startsWith(prefix));
  return found ? decodeURIComponent(found.slice(prefix.length)) : "";
}

function writeDisplayCookie(name: string, value: string) {
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; SameSite=Strict${secure}`;
}

export function setSessionCookies(role: string, username: string) {
  // These are display hints only, NEVER security credentials.
  if (typeof document === "undefined") return;
  writeDisplayCookie("role", role);
  writeDisplayCookie("username", username);
}

export function clearSessionCookies() {
  if (typeof document === "undefined") return;
  for (const name of ["session", "role", "username", "access_token"]) {
    document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Strict`;
  }
}

/** Remove tokens written by earlier frontend releases; cannot delete HttpOnly cookies. */
export function clearLegacyTokens() {
  if (typeof window === "undefined") return;
  for (const name of ["access_token", "refresh_token", "role", "username"]) {
    window.localStorage.removeItem(name);
    window.sessionStorage.removeItem(name);
  }
  clearSessionCookies();
}

let csrfBootstrap: Promise<string> | null = null;

async function csrfToken(): Promise<string> {
  const existing = readCookie("erp_csrf");
  if (existing) return existing;
  if (!csrfBootstrap) {
    csrfBootstrap = fetch(`${API_URL}/auth/browser/csrf`, {
      credentials: "same-origin", cache: "no-store",
    }).then(async (response) => {
      if (!response.ok) throw new Error("Falha ao preparar proteção CSRF");
      const result = await response.json() as { csrf_token: string };
      if (!result.csrf_token || result.csrf_token !== readCookie("erp_csrf")) {
        throw new Error("Cookie de proteção CSRF não disponível");
      }
      return result.csrf_token;
    }).finally(() => { csrfBootstrap = null; });
  }
  return csrfBootstrap;
}

function endpoint(path: string): string {
  // Only relative API routes are accepted; never forward tokens to arbitrary hosts.
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("://")) {
    throw new Error("Rota de API inválida");
  }
  return `${API_URL}${path}`;
}

function unsafe(method: string) { return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase()); }

async function cookieFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.delete("Authorization");
  if (unsafe(method)) {
    headers.set("X-CSRF-Token", await csrfToken());
    if (typeof options.body === "string" && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }
  return fetch(endpoint(path), {
    ...options, method, headers, credentials: "same-origin", cache: "no-store",
  });
}

async function refreshUnderLock(): Promise<boolean> {
  // A second tab may have rotated the refresh cookie while we waited.
  const me = await cookieFetch("/auth/browser/me").catch(() => null);
  if (me?.ok) return true;
  const refreshed = await cookieFetch("/auth/browser/refresh", { method: "POST" });
  return refreshed.ok;
}

let pendingRefresh: Promise<boolean> | null = null;
async function refreshOnce(): Promise<boolean> {
  if (!pendingRefresh) {
    pendingRefresh = (async () => {
      try {
        if (typeof navigator !== "undefined" && "locks" in navigator) {
          return await navigator.locks.request("erp-browser-refresh", refreshUnderLock);
        }
        return await refreshUnderLock();
      } catch { return false; }
    })().finally(() => { pendingRefresh = null; });
  }
  return pendingRefresh;
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  let response = await cookieFetch(path, options);
  if (response.status === 401 && !path.startsWith("/auth/browser/") && !path.startsWith("/public/")) {
    if (await refreshOnce()) response = await cookieFetch(path, options);
  }
  if (response.status === 401 && typeof window !== "undefined"
      && !window.location.pathname.startsWith("/login")
      && !path.startsWith("/public/")) {
    clearLegacyTokens();
    window.location.replace("/login?expired=1");
  }
  return response;
}

export async function authJson(path: string, options: RequestInit = {}) {
  const response = await apiFetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || data?.message || "Falha na operação");
  return data;
}

export async function browserAuthJson(path: string, options: RequestInit = {}) {
  const response = await cookieFetch(`/auth/browser${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || data?.message || "Falha na autenticação");
  return data;
}

export async function logoutBrowser(all = false) {
  try {
    await browserAuthJson(all ? "/logout-all" : "/logout", { method: "POST" });
  } catch {
    // Clear cookies even if access credentials have expired or been revoked.
    try { await browserAuthJson("/clear", { method: "POST" }); } catch { /* network unavailable */ }
  }
  clearLegacyTokens();
}

export async function clearBrowserCookies() {
  try { await browserAuthJson("/clear", { method: "POST" }); }
  finally { clearLegacyTokens(); }
}

export async function authDownload(path: string, fileName: string) {
  const response = await apiFetch(path);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data?.detail || data?.message || "Falha no download");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally { URL.revokeObjectURL(url); }
}
