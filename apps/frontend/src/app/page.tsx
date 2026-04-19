"use client";

import { useEffect, useMemo, useState } from "react";

import { API_URL, authJson, clearSessionCookies } from "@/lib/auth";

type Dashboard = {
  total_empenhado: number;
  total_pago: number;
  total_receita: number;
};

type Inventory = { total: number; ativos: number };
type PublicList = { total: number };
type Session = { username: string; full_name: string; role: string };
type RecentAuditEntry = { id: number; action: string; entity: string; created_at: string };
type MessageKind = "success" | "error" | "info";

const QUICK_LINKS = [
  { href: "/fase-2", label: "1) Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/orcamento", label: "2) Orçamento (PPA/LDO/LOA)", roles: ["admin", "accountant", "read_only"] },
  { href: "/compras", label: "3) Compras e Contratos", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/public", label: "4) Transparência", roles: [] },
  { href: "/rh", label: "5) RH e Folha", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "6) Portal do Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "7) Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/auditoria", label: "8) Auditoria", roles: ["admin", "read_only"] },
];

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [publicCommitments, setPublicCommitments] = useState<PublicList | null>(null);
  const [publicPayments, setPublicPayments] = useState<PublicList | null>(null);
  const [message, setMessage] = useState<string>("");
  const [messageKind, setMessageKind] = useState<MessageKind>("info");
  const [loading, setLoading] = useState(true);
  const [recentAudit, setRecentAudit] = useState<RecentAuditEntry[]>([]);
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
      authJson("/core/audit-logs?page=1&size=5").catch(() => ({ items: [] })),
      fetch(`${API_URL}/public/commitments?page=1&size=1`).then((r) => r.json()),
      fetch(`${API_URL}/public/payments?page=1&size=1`).then((r) => r.json()),
    ])
      .then(([me, d, inv, audit, commitments, payments]) => {
        setSession({
          username: me.username || "",
          full_name: me.full_name || "",
          role: me.role || "",
        });
        setDashboard(d);
        setInventory(inv);
        setRecentAudit(audit?.items || []);
        setPublicCommitments({ total: commitments.total || 0 });
        setPublicPayments({ total: payments.total || 0 });
      })
      .catch(() => {
        setMessage("Não foi possível carregar os painéis de resumo.");
        setMessageKind("error");
      })
      .finally(() => setLoading(false));
  }, []);

  const quickLinks = useMemo(
    () => QUICK_LINKS.filter((item) => item.roles.length === 0 || item.roles.includes(session.role)),
    [session.role],
  );

  const copyText = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(`Copiado: ${value}`);
      setMessageKind("success");
    } catch {
      setMessage(`Não foi possível copiar ${value}.`);
      setMessageKind("error");
    }
  };

  const logout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST" });
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("role");
    window.localStorage.removeItem("username");
    clearSessionCookies();
    window.location.href = "/login";
  };

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Painel Geral</h1>
      <p>
        Usuário logado: <strong suppressHydrationWarning>{session.username || "carregando..."}</strong> · Perfil:{" "}
        <strong suppressHydrationWarning>{session.role || "carregando..."}</strong>
      </p>
      {session.full_name ? <p className="muted">Nome: {session.full_name}</p> : null}
      <nav className="toolbar">
        {quickLinks.map((link) => (
          <a key={link.href} className="btn" href={link.href}>
            {link.label}
          </a>
        ))}
        <button className="btn btn-danger" onClick={logout}>Sair</button>
      </nav>
      {message ? <p className={messageKind === "error" ? "notice error" : messageKind === "success" ? "notice success" : "notice"}>{message}</p> : null}

      <section className="kpi-grid">
        <div className="card kpi-card">
          <h2>Contábil</h2>
          <p className="kpi-value">R$ {loading ? "..." : (dashboard?.total_empenhado?.toFixed(2) ?? "0.00")}</p>
          <p className="muted">Total empenhado</p>
          <p>Pago: <strong>R$ {dashboard?.total_pago?.toFixed(2) ?? "..."}</strong></p>
          <p>Receita: <strong>R$ {dashboard?.total_receita?.toFixed(2) ?? "..."}</strong></p>
        </div>
        <div className="card kpi-card">
          <h2>Patrimônio</h2>
          <p className="kpi-value">{loading ? "..." : (inventory?.total ?? 0)}</p>
          <p className="muted">Total de bens cadastrados</p>
          <p>Ativos: <strong>{inventory?.ativos ?? "..."}</strong></p>
        </div>
        <div className="card kpi-card">
          <h2>Transparência pública</h2>
          <p className="kpi-value">{loading ? "..." : (publicCommitments?.total ?? 0)}</p>
          <p className="muted">Empenhos publicados</p>
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
        <div className="card">
          <h2>Atividade recente</h2>
          <ul style={{ marginLeft: 18, display: "grid", gap: 4 }}>
            {(recentAudit || []).length > 0 ? (
              recentAudit.map((row) => (
                <li key={row.id}>
                  <span className={`chip ${row.action}`}>{row.action}</span> <strong>{row.entity}</strong> ·{" "}
                  {new Date(row.created_at).toLocaleString("pt-BR")}
                </li>
              ))
            ) : (
              <li className="empty-state">Sem eventos recentes visíveis para o perfil atual.</li>
            )}
          </ul>
        </div>
      </section>
    </main>
  );
}
