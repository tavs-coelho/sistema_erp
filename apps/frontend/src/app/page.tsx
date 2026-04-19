"use client";

import { useEffect, useMemo, useState } from "react";

import { API_URL, authJson } from "@/lib/auth";

type Dashboard = {
  total_empenhado: number;
  total_pago: number;
  total_receita: number;
};

type Inventory = { total: number; ativos: number };
type PublicList = { total: number };
type Session = { username: string; full_name: string; role: string };

const QUICK_LINKS = [
  { href: "/fase-2", label: "1) Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/public", label: "2) Transparência", roles: [] },
  { href: "/rh", label: "3) RH e Folha", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "4) Portal do Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "5) Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/auditoria", label: "6) Auditoria", roles: ["admin", "read_only"] },
];

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [publicCommitments, setPublicCommitments] = useState<PublicList | null>(null);
  const [publicPayments, setPublicPayments] = useState<PublicList | null>(null);
  const [message, setMessage] = useState<string>("");
  const [session, setSession] = useState<Session>({
    username: "",
    full_name: "",
    role: "",
  });

  useEffect(() => {
    Promise.all([
      authJson("/auth/me"),
      authJson("/accounting/dashboard"),
      authJson("/patrimony/inventory"),
      fetch(`${API_URL}/public/commitments?page=1&size=1`).then((r) => r.json()),
      fetch(`${API_URL}/public/payments?page=1&size=1`).then((r) => r.json()),
    ])
      .then(([me, d, inv, commitments, payments]) => {
        setSession({
          username: me.username || "",
          full_name: me.full_name || "",
          role: me.role || "",
        });
        setDashboard(d);
        setInventory(inv);
        setPublicCommitments({ total: commitments.total || 0 });
        setPublicPayments({ total: payments.total || 0 });
      })
      .catch(() => setMessage("Não foi possível carregar os painéis de resumo."));
  }, []);

  const quickLinks = useMemo(
    () => QUICK_LINKS.filter((item) => item.roles.length === 0 || item.roles.includes(session.role)),
    [session.role],
  );

  const copyText = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(`Copiado: ${value}`);
    } catch {
      setMessage(`Não foi possível copiar ${value}.`);
    }
  };

  const logout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST" });
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("role");
    window.localStorage.removeItem("username");
    document.cookie = "session=; Max-Age=0; path=/; SameSite=Lax; Secure";
    document.cookie = "role=; Max-Age=0; path=/; SameSite=Lax; Secure";
    document.cookie = "username=; Max-Age=0; path=/; SameSite=Lax; Secure";
    document.cookie = "access_token=; Max-Age=0; path=/; SameSite=Lax; Secure";
    window.location.href = "/login";
  };

  return (
    <main className="module-page" style={{ padding: 16, fontFamily: "Arial, sans-serif" }}>
      <h1>Painel Geral</h1>
      <p>
        Usuário logado: <strong suppressHydrationWarning>{session.username || "carregando..."}</strong> · Perfil:{" "}
        <strong suppressHydrationWarning>{session.role || "carregando..."}</strong>
      </p>
      {session.full_name ? <p className="muted">Nome: {session.full_name}</p> : null}
      <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {quickLinks.map((link) => (
          <a key={link.href} className="btn" href={link.href}>
            {link.label}
          </a>
        ))}
        <button className="btn btn-danger" onClick={logout}>Sair</button>
      </nav>
      {message ? <p className={message.toLowerCase().includes("não foi possível") ? "notice error" : "notice"}>{message}</p> : null}

      <section style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <div className="card">
          <h2>Contábil</h2>
          <p>Total empenhado: <strong>R$ {dashboard?.total_empenhado?.toFixed(2) ?? "..."}</strong></p>
          <p>Total pago: <strong>R$ {dashboard?.total_pago?.toFixed(2) ?? "..."}</strong></p>
          <p>Total receita: <strong>R$ {dashboard?.total_receita?.toFixed(2) ?? "..."}</strong></p>
        </div>
        <div className="card">
          <h2>Patrimônio</h2>
          <p>Total de bens: <strong>{inventory?.total ?? "..."}</strong></p>
          <p>Bens ativos: <strong>{inventory?.ativos ?? "..."}</strong></p>
        </div>
        <div className="card">
          <h2>Transparência pública</h2>
          <p>Empenhos publicados: <strong>{publicCommitments?.total ?? "..."}</strong></p>
          <p>Pagamentos publicados: <strong>{publicPayments?.total ?? "..."}</strong></p>
          <p className="muted">Registros internos de empenho/pagamento aparecem automaticamente no portal.</p>
        </div>
        <div className="card">
          <h2>Modo demonstração</h2>
          <p><strong>Usuários:</strong> admin1, hr1, employee1, patrimony1 (senha: demo123)</p>
          <p><strong>Ordem:</strong> Contábil → Transparência → RH → Portal do Servidor → Patrimônio → Auditoria</p>
          <p><strong>Cenário seeded:</strong></p>
          <ul style={{ marginLeft: 18, display: "grid", gap: 4 }}>
            <li>Departamento: <code>Secretaria Demo Integrada</code> <button className="btn btn-inline" onClick={() => copyText("Secretaria Demo Integrada")}>Copiar</button></li>
            <li>Fornecedor: <code>Fornecedor Demo Integrado</code> <button className="btn btn-inline" onClick={() => copyText("Fornecedor Demo Integrado")}>Copiar</button></li>
            <li>Empenho: <code>EMP-DEMO-001</code> <button className="btn btn-inline" onClick={() => copyText("EMP-DEMO-001")}>Copiar</button></li>
            <li>Bem: <code>PAT-DEMO-001</code> <button className="btn btn-inline" onClick={() => copyText("PAT-DEMO-001")}>Copiar</button></li>
            <li>Evento folha: <code>Evento Demo Integrado</code> <button className="btn btn-inline" onClick={() => copyText("Evento Demo Integrado")}>Copiar</button></li>
          </ul>
        </div>
      </section>
    </main>
  );
}
