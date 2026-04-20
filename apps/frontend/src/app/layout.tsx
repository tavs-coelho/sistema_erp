import type { Metadata } from "next";
import HeaderNav from "@/components/header-nav";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sistema ERP Municipal",
  description: "MVP de gestão pública municipal",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <ThemeProvider>
          <HeaderNav>{children}</HeaderNav>
        </ThemeProvider>
      </body>
    </html>
  );
}
