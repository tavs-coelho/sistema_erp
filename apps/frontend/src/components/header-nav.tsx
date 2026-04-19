"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

import { readCookie } from "@/lib/auth";

type Session = { username: string; role: string };

const NAV_ITEMS = [
  { href: "/", label: "Painel", roles: [] as string[] },
  { href: "/fase-2", label: "Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/orcamento", label: "Orçamento", roles: ["admin", "accountant", "read_only"] },
  { href: "/compras", label: "Compras", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/protocolo", label: "Protocolo", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/convenios", label: "Convênios", roles: ["admin", "accountant", "read_only"] },
  { href: "/tributario", label: "Tributário", roles: ["admin", "accountant", "read_only"] },
  { href: "/rh", label: "RH", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "Portal Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/almoxarifado", label: "Almoxarifado", roles: ["admin", "procurement", "read_only"] },
  { href: "/frota", label: "Frota", roles: ["admin", "procurement", "read_only"] },
  { href: "/relatorios", label: "Relatórios", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/auditoria", label: "Auditoria", roles: ["admin", "read_only"] },
  { href: "/public", label: "Transparência", roles: [] as string[] },
];

export default function HeaderNav() {
  const pathname = usePathname();
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

  return (
    <>
      <nav className="app-header-nav">
        {visibleItems.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} className={active ? "active" : ""}>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="app-header-right">
        <span className="demo-badge">Ambiente de Demonstração</span>
        <span className="header-user" suppressHydrationWarning>
          {session.username || "usuário"} · {session.role || "perfil"}
        </span>
      </div>
    </>
  );
}
