import type { Metadata } from "next";
import Link from "next/link";
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
            <nav className="app-header-nav">
              <Link href="/">Painel</Link>
              <Link href="/fase-2">Contábil</Link>
              <Link href="/rh">RH</Link>
              <Link href="/portal-servidor">Portal Servidor</Link>
              <Link href="/patrimonio">Patrimônio</Link>
              <Link href="/public">Transparência</Link>
            </nav>
          </header>
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  );
}
