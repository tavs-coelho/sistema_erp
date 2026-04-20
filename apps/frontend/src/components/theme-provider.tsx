"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { applyTheme, BrandingTheme, resolveTheme, saveTheme } from "@/lib/theme";

type ThemeContextValue = {
  theme: BrandingTheme;
  updateTheme: (next: Partial<BrandingTheme>) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<BrandingTheme>(resolveTheme);

  useEffect(() => {
    applyTheme(theme);
    saveTheme(theme);
  }, [theme]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      updateTheme: (next) => setTheme((prev) => ({ ...prev, ...next })),
    }),
    [theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
