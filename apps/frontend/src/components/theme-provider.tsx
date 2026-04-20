"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { applyTheme, BrandingTheme, fetchBrandingFromApi, resolveTheme, saveTheme } from "@/lib/theme";

export type ColorScheme = "system" | "light" | "dark";
const COLOR_SCHEME_KEY = "erp:color-scheme";

type ThemeContextValue = {
  theme: BrandingTheme;
  updateTheme: (next: Partial<BrandingTheme>) => void;
  colorScheme: ColorScheme;
  setColorScheme: (s: ColorScheme) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function resolveColorScheme(): ColorScheme {
  if (typeof window === "undefined") return "system";
  const s = window.localStorage.getItem(COLOR_SCHEME_KEY);
  return s === "light" || s === "dark" || s === "system" ? s : "system";
}

function applyColorScheme(scheme: ColorScheme) {
  if (typeof document === "undefined") return;
  if (scheme === "system") document.documentElement.removeAttribute("data-color-scheme");
  else document.documentElement.setAttribute("data-color-scheme", scheme);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<BrandingTheme>(resolveTheme);
  const [colorScheme, setColorSchemeState] = useState<ColorScheme>(resolveColorScheme);

  useEffect(() => { applyTheme(theme); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  useEffect(() => {
    fetchBrandingFromApi().then((t) => { setTheme(t); applyTheme(t); saveTheme(t); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { applyTheme(theme); saveTheme(theme); }, [theme]);
  useEffect(() => { applyColorScheme(colorScheme); }, [colorScheme]);

  const setColorScheme = (s: ColorScheme) => {
    setColorSchemeState(s);
    if (typeof window !== "undefined") window.localStorage.setItem(COLOR_SCHEME_KEY, s);
  };

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, updateTheme: (next) => setTheme((prev) => ({ ...prev, ...next })), colorScheme, setColorScheme }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [theme, colorScheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
