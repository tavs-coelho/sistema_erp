"use client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const entry = document.cookie.split(";").find((item) => item.trim().startsWith(`${name}=`));
  if (!entry) return "";
  return decodeURIComponent(entry.trim().slice(name.length + 1));
}

export function authToken() {
  return readCookie("access_token");
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
