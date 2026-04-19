import type { Metadata } from "next";
import HeaderNav from "@/components/header-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "ERP Municipal Demo",
  description: "MVP de gestão pública municipal",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <strong>Sistema ERP Municipal</strong>
            <HeaderNav />
          </header>
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  );
}
