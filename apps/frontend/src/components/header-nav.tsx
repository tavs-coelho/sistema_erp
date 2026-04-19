"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";

import { readCookie } from "@/lib/auth";

type Session = { username: string; role: string };

const NAV_ITEMS = [
  { href: "/", label: "Painel", roles: [] as string[] },
  { href: "/fase-2", label: "Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/rh", label: "RH", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "Portal Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/auditoria", label: "Auditoria", roles: ["admin", "read_only"] },
  { href: "/public", label: "Transparência", roles: [] as string[] },
];

export default function HeaderNav() {
  const pathname = usePathname();
  const getSessionSnapshot = useCallback(() => ({ username: readCookie("username"), role: readCookie("role") }), []);
  const session = useSyncExternalStore<Session>(
    (onStoreChange) => {
      if (typeof window === "undefined") return () => {};
      const handler = () => onStoreChange();
      window.addEventListener("storage", handler);
      return () => window.removeEventListener("storage", handler);
    },
    getSessionSnapshot,
    () => ({ username: "", role: "" }),
  );

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
