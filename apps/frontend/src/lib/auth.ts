"use client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const entry = document.cookie.split(";").find((item) => item.trim().startsWith(`${name}=`));
  if (!entry) return "";
  return decodeURIComponent(entry.trim().slice(name.length + 1));
}

function isHttps(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.protocol === "https:";
}

function cookieFlags(maxAge?: number): string {
  const secure = isHttps() ? "; Secure" : "";
  const age = typeof maxAge === "number" ? `; Max-Age=${maxAge}` : "";
  return `path=/; SameSite=Lax${age}${secure}`;
}

function writeCookie(name: string, value: string, maxAge?: number) {
  document.cookie = `${name}=${encodeURIComponent(value)}; ${cookieFlags(maxAge)}`;
}

function clearCookieBothSchemes(name: string) {
  document.cookie = `${name}=; Max-Age=0; path=/; SameSite=Lax`;
  document.cookie = `${name}=; Max-Age=0; path=/; SameSite=Lax; Secure`;
}

export function setSessionCookies(role: string, username: string) {
  if (typeof document === "undefined") return;
  writeCookie("session", "active");
  writeCookie("role", role);
  writeCookie("username", username);
}

export function clearSessionCookies() {
  if (typeof document === "undefined") return;
  for (const name of ["session", "role", "username", "access_token"]) {
    clearCookieBothSchemes(name);
  }
}

function readStorage(name: string): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(name) || "";
}

export function authToken() {
  return readStorage("access_token") || readCookie("access_token");
}

export async function authJson(path: string, options?: RequestInit) {
  const token = authToken();
  const headers: HeadersInit = {
    Authorization: `Bearer ${token}`,
    ...(options?.headers || {}),
  };
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.detail || data?.message || "Falha na operação";
    throw new Error(message);
  }
  return data;
}

export async function authDownload(path: string, fileName: string) {
  const token = authToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data?.detail || data?.message || "Falha no download");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
