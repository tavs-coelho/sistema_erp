"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { useTheme } from "@/components/theme-provider";
import { readCookie } from "@/lib/auth";
import { cn } from "@/lib/cn";

type Session = { username: string; role: string };

const NAV_ITEMS = [
  { href: "/", label: "Painel", roles: [] as string[] },
  { href: "/fase-2", label: "Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/orcamento", label: "Orçamento", roles: ["admin", "accountant", "read_only"] },
  { href: "/compras", label: "Compras", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/protocolo", label: "Protocolo", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/convenios", label: "Convênios", roles: ["admin", "accountant", "read_only"] },
  { href: "/tributario", label: "Tributário", roles: ["admin", "accountant", "read_only"] },
  { href: "/nfse-itbi", label: "NFS-e/ITBI", roles: ["admin", "accountant", "read_only"] },
  { href: "/ponto", label: "Ponto", roles: ["admin", "hr", "read_only"] },
  { href: "/depreciacao", label: "Depreciação", roles: ["admin", "patrimony", "read_only"] },
  { href: "/integracao-ponto-folha", label: "Ponto→Folha", roles: ["admin", "hr"] },
  { href: "/rh", label: "RH", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "Portal Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/almoxarifado", label: "Almoxarifado", roles: ["admin", "procurement", "read_only"] },
  { href: "/frota", label: "Frota", roles: ["admin", "procurement", "read_only"] },
  { href: "/relatorios", label: "Relatórios", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/lrf", label: "LRF", roles: ["admin", "accountant", "read_only"] },
  { href: "/conciliacao", label: "Banco", roles: ["admin", "accountant", "read_only"] },
  { href: "/auditoria", label: "Auditoria", roles: ["admin", "read_only"] },
  { href: "/public", label: "Transparência", roles: [] as string[] },
];

export default function HeaderNav({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const sessionRaw = useSyncExternalStore<string>(
    (onStoreChange) => {
      if (typeof window === "undefined") return () => {};
      const handler = () => onStoreChange();
      window.addEventListener("storage", handler);
      return () => window.removeEventListener("storage", handler);
    },
    () => `${readCookie("username")}|${readCookie("role")}`,
    () => "|",
  );
  const [username = "", role = ""] = sessionRaw.split("|");
  const session: Session = { username, role };

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.length === 0 || item.roles.includes(session.role));
  const isItemActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const currentLabel = visibleItems.find((item) => isItemActive(item.href))?.label || "Sistema ERP";
  const initials = theme.org_name
    .split(" ")
    .map((token) => token[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();

  if (pathname.startsWith("/login")) {
    return <div className="auth-shell">{children}</div>;
  }

  return (
    <div className="app-shell">
      <aside className={cn("app-sidebar", sidebarOpen && "open")}>
        <Link href="/" className="brand-block" onClick={() => setSidebarOpen(false)}>
          {theme.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={theme.logo_url} alt={theme.org_name} className="brand-logo" />
          ) : (
            <span className="brand-monogram">{initials}</span>
          )}
          <span className="brand-copy">
            <strong>{theme.org_name}</strong>
            <small>ERP institucional</small>
          </span>
        </Link>

        <nav className="sidebar-nav">
          {visibleItems.map((item) => {
            const active = isItemActive(item.href);
            return (
              <Link key={item.href} href={item.href} className={cn("nav-link", active && "active")} onClick={() => setSidebarOpen(false)}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-left">
            <button type="button" className="btn btn-ghost sidebar-toggle" onClick={() => setSidebarOpen((prev) => !prev)} aria-label="Abrir menu">
              ☰
            </button>
            <div className="topbar-title">
              <strong>{currentLabel}</strong>
              <small>Painel administrativo institucional</small>
            </div>
          </div>
          <div className="topbar-right">
            <span className="demo-badge">Ambiente de Demonstração</span>
            <span className="header-user" suppressHydrationWarning>
              {session.username || "usuário"} · {session.role || "perfil"}
            </span>
          </div>
        </header>
        <div className="app-content">{children}</div>
      </div>

      {sidebarOpen ? <button type="button" className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu" /> : null}
    </div>
  );
}
