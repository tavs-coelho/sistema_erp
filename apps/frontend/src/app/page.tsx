"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
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

const QUICK_LINKS = [
  { href: "/fase-2", label: "Contábil", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/orcamento", label: "Orçamento (PPA/LDO/LOA)", roles: ["admin", "accountant", "read_only"] },
  { href: "/compras", label: "Compras e Contratos", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/protocolo", label: "Protocolo / Processos", roles: ["admin", "accountant", "procurement", "read_only"] },
  { href: "/convenios", label: "Convênios", roles: ["admin", "accountant", "read_only"] },
  { href: "/tributario", label: "Tributário", roles: ["admin", "accountant", "read_only"] },
  { href: "/public", label: "Transparência", roles: [] },
  { href: "/rh", label: "RH e Folha", roles: ["admin", "hr", "read_only"] },
  { href: "/portal-servidor", label: "Portal do Servidor", roles: ["admin", "hr", "employee", "read_only"] },
  { href: "/patrimonio", label: "Patrimônio", roles: ["admin", "patrimony", "read_only"] },
  { href: "/almoxarifado", label: "Almoxarifado", roles: ["admin", "procurement", "read_only"] },
  { href: "/auditoria", label: "Auditoria", roles: ["admin", "read_only"] },
  { href: "/siconfi-siop", label: "SICONFI / SIOP", roles: ["admin", "accountant", "read_only"] },
];

export default function Home() {
  const { toast } = useToast();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [publicCommitments, setPublicCommitments] = useState<PublicList | null>(null);
  const [publicPayments, setPublicPayments] = useState<PublicList | null>(null);
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
        toast("Não foi possível carregar os painéis de resumo.", "error");
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
      toast(`Copiado: ${value}`, "success");
    } catch {
      toast(`Não foi possível copiar ${value}.`, "error");
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
    <main className="module-page">
      <div>
        <h1>Painel Geral</h1>
        <p>
          Usuário logado: <strong suppressHydrationWarning>{session.username || "carregando..."}</strong> · Perfil:{" "}
          <strong suppressHydrationWarning>{session.role || "carregando..."}</strong>
        </p>
        {session.full_name ? <p className="muted">Nome: {session.full_name}</p> : null}
      </div>

      <nav className="toolbar">
        {quickLinks.map((link) => (
          <a key={link.href} className="btn" href={link.href}>
            {link.label}
          </a>
        ))}
        <Button variant="danger" onClick={logout}>Sair</Button>
      </nav>

      <section className="kpi-grid">
        <Card className="kpi-card">
          <h2>Contábil</h2>
          {loading ? (
            <Skeleton style={{ height: 34, marginTop: 8 }} />
          ) : (
            <p className="kpi-value">R$ {dashboard?.total_empenhado?.toFixed(2) ?? "0.00"}</p>
          )}
          <p className="muted">Total empenhado</p>
          <p>Pago: <strong>R$ {dashboard?.total_pago?.toFixed(2) ?? "—"}</strong></p>
          <p>Receita: <strong>R$ {dashboard?.total_receita?.toFixed(2) ?? "—"}</strong></p>
        </Card>

        <Card className="kpi-card">
          <h2>Patrimônio</h2>
          {loading ? (
            <Skeleton style={{ height: 34, marginTop: 8 }} />
          ) : (
            <p className="kpi-value">{inventory?.total ?? 0}</p>
          )}
          <p className="muted">Total de bens cadastrados</p>
          <p>Ativos: <strong>{inventory?.ativos ?? "—"}</strong></p>
        </Card>

        <Card className="kpi-card">
          <h2>Transparência pública</h2>
          {loading ? (
            <Skeleton style={{ height: 34, marginTop: 8 }} />
          ) : (
            <p className="kpi-value">{publicCommitments?.total ?? 0}</p>
          )}
          <p className="muted">Empenhos publicados</p>
          <p>Pagamentos publicados: <strong>{publicPayments?.total ?? "—"}</strong></p>
          <p className="muted">Registros internos de empenho/pagamento aparecem automaticamente no portal.</p>
        </Card>

        <Card>
          <h2>Modo demonstração</h2>
          <p><strong>Usuários:</strong> admin1, hr1, employee1, patrimony1 (senha: demo123)</p>
          <p><strong>Ordem:</strong> Contábil → Transparência → RH → Portal do Servidor → Patrimônio → Auditoria</p>
          <p><strong>Cenário seeded:</strong></p>
          <ul className="list-plain">
            <li>Departamento: <code>Secretaria Demo Integrada</code> <Button size="sm" className="btn-inline" onClick={() => copyText("Secretaria Demo Integrada")}>Copiar</Button></li>
            <li>Fornecedor: <code>Fornecedor Demo Integrado</code> <Button size="sm" className="btn-inline" onClick={() => copyText("Fornecedor Demo Integrado")}>Copiar</Button></li>
            <li>Empenho: <code>EMP-DEMO-001</code> <Button size="sm" className="btn-inline" onClick={() => copyText("EMP-DEMO-001")}>Copiar</Button></li>
            <li>Bem: <code>PAT-DEMO-001</code> <Button size="sm" className="btn-inline" onClick={() => copyText("PAT-DEMO-001")}>Copiar</Button></li>
            <li>Evento folha: <code>Evento Demo Integrado</code> <Button size="sm" className="btn-inline" onClick={() => copyText("Evento Demo Integrado")}>Copiar</Button></li>
          </ul>
        </Card>

        <Card>
          <h2>Atividade recente</h2>
          <ul className="list-plain">
            {recentAudit.length > 0 ? (
              recentAudit.map((row) => (
                <li key={row.id}>
                  <span className={`chip ${row.action}`}>{row.action}</span>{" "}
                  <strong>{row.entity}</strong> · {new Date(row.created_at).toLocaleString("pt-BR")}
                </li>
              ))
            ) : (
              <li className="empty-state">Sem eventos recentes visíveis para o perfil atual.</li>
            )}
          </ul>
        </Card>
      </section>
    </main>
  );
}
