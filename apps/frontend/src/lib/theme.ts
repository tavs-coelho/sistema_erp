import { API_URL } from "@/lib/auth";

export type BrandingTheme = {
  org_name: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  favicon_url: string;
  app_title: string;
};

const BRANDING_STORAGE_KEY = process.env.NEXT_PUBLIC_BRANDING_STORAGE_KEY || "erp:branding";

const defaults: BrandingTheme = {
  org_name: process.env.NEXT_PUBLIC_ORG_NAME || "Prefeitura Municipal",
  logo_url: process.env.NEXT_PUBLIC_LOGO_URL || "",
  primary_color: process.env.NEXT_PUBLIC_PRIMARY_COLOR || "#1d4ed8",
  secondary_color: process.env.NEXT_PUBLIC_SECONDARY_COLOR || "#0f172a",
  accent_color: process.env.NEXT_PUBLIC_ACCENT_COLOR || "#0ea5e9",
  favicon_url: process.env.NEXT_PUBLIC_FAVICON_URL || "/favicon.ico",
  app_title: process.env.NEXT_PUBLIC_APP_TITLE || "Sistema ERP Municipal",
};

function parseTheme(raw: string | null): Partial<BrandingTheme> {
  if (!raw) return {};
  try {
    const value = JSON.parse(raw) as Partial<BrandingTheme>;
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

/** Synchronous resolve from localStorage — used during SSR/initial render. */
export function resolveTheme(): BrandingTheme {
  if (typeof window === "undefined") return defaults;
  const fromStorage = parseTheme(window.localStorage.getItem(BRANDING_STORAGE_KEY));
  return { ...defaults, ...fromStorage };
}

/** Persist theme to localStorage (client-side cache for offline/fast loads). */
export function saveTheme(theme: BrandingTheme) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(BRANDING_STORAGE_KEY, JSON.stringify(theme));
}

/** Apply theme CSS variables and meta tags to the document. */
export function applyTheme(theme: BrandingTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.style.setProperty("--theme-primary", theme.primary_color);
  root.style.setProperty("--theme-secondary", theme.secondary_color);
  root.style.setProperty("--theme-accent", theme.accent_color);
  document.title = theme.app_title;

  let favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!favicon) {
    favicon = document.createElement("link");
    favicon.rel = "icon";
    document.head.appendChild(favicon);
  }
  favicon.href = theme.favicon_url;
}

/**
 * Fetch the current branding config from the backend API.
 * Falls back silently to defaults if the request fails (e.g. server not running).
 */
export async function fetchBrandingFromApi(): Promise<BrandingTheme> {
  try {
    const response = await fetch(`${API_URL}/branding`);
    if (!response.ok) return defaults;
    const data = (await response.json()) as Partial<BrandingTheme>;
    return { ...defaults, ...data };
  } catch {
    return defaults;
  }
}

/**
 * Persist branding to the backend API (admin-only).
 * Throws on HTTP error so the caller can surface a status message.
 */
export async function saveBrandingToApi(theme: BrandingTheme, accessToken: string): Promise<BrandingTheme> {
  const response = await fetch(`${API_URL}/branding`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(theme),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = (data as { detail?: string })?.detail || "Falha ao salvar branding";
    throw new Error(message);
  }
  return { ...defaults, ...(data as Partial<BrandingTheme>) };
}

// ── WCAG contrast helpers ────────────────────────────────────────────────────

/** Convert a hex colour string to linear sRGB relative luminance (0–1). */
function hexToLuminance(hex: string): number {
  const clean = hex.replace("#", "");
  const full = clean.length === 3
    ? clean.split("").map((c) => c + c).join("")
    : clean;
  const r = parseInt(full.slice(0, 2), 16) / 255;
  const g = parseInt(full.slice(2, 4), 16) / 255;
  const b = parseInt(full.slice(4, 6), 16) / 255;
  const linearize = (c: number) =>
    c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

/**
 * Returns the WCAG 2.1 contrast ratio between two hex colours.
 * Ratio ranges from 1 (same) to 21 (black/white).
 */
export function contrastRatio(colorA: string, colorB: string): number {
  const lA = hexToLuminance(colorA);
  const lB = hexToLuminance(colorB);
  const lighter = Math.max(lA, lB);
  const darker = Math.min(lA, lB);
  return (lighter + 0.05) / (darker + 0.05);
}

/** WCAG AA thresholds: 4.5:1 for normal text, 3:1 for large/bold text. */
export type ContrastLevel = "AAA" | "AA" | "AA-large" | "fail";

export function wcagLevel(ratio: number): ContrastLevel {
  if (ratio >= 7) return "AAA";
  if (ratio >= 4.5) return "AA";
  if (ratio >= 3) return "AA-large";
  return "fail";
}

