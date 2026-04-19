"use client";

import Link from "next/link";

const NAV_ITEMS = [
  { href: "/", label: "Painel" },
  { href: "/fase-2", label: "Contábil" },
  { href: "/rh", label: "RH" },
  { href: "/portal-servidor", label: "Portal Servidor" },
  { href: "/patrimonio", label: "Patrimônio" },
  { href: "/auditoria", label: "Auditoria" },
  { href: "/public", label: "Transparência" },
];

export default function HeaderNav() {
  return (
    <nav className="app-header-nav">
      {NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
