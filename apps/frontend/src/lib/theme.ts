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

export function resolveTheme(): BrandingTheme {
  if (typeof window === "undefined") return defaults;
  const fromStorage = parseTheme(window.localStorage.getItem(BRANDING_STORAGE_KEY));
  return { ...defaults, ...fromStorage };
}

export function saveTheme(theme: BrandingTheme) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(BRANDING_STORAGE_KEY, JSON.stringify(theme));
}

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
