"use client";

import { useEffect, useState } from "react";

import { API_URL, authJson, readCookie } from "@/lib/auth";

type Dashboard = {
  total_empenhado: number;
  total_pago: number;
  total_receita: number;
};

type Inventory = { total: number; ativos: number };
type PublicList = { total: number };

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [publicCommitments, setPublicCommitments] = useState<PublicList | null>(null);
  const [publicPayments, setPublicPayments] = useState<PublicList | null>(null);
  const [message, setMessage] = useState<string>("");
  const [token] = useState(() => readCookie("access_token"));
  const [role] = useState(() => readCookie("role"));

  useEffect(() => {
    if (!token) return;
    Promise.all([
      authJson("/accounting/dashboard"),
      authJson("/patrimony/inventory"),
      fetch(`${API_URL}/public/commitments?page=1&size=1`).then((r) => r.json()),
      fetch(`${API_URL}/public/payments?page=1&size=1`).then((r) => r.json()),
    ])
      .then(([d, inv, commitments, payments]) => {
        setDashboard(d);
        setInventory(inv);
        setPublicCommitments({ total: commitments.total || 0 });
        setPublicPayments({ total: payments.total || 0 });
      })
      .catch(() => setMessage("Não foi possível carregar os painéis de resumo."));
  }, [token]);

  const logout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST" });
    document.cookie = "access_token=; Max-Age=0; path=/";
    document.cookie = "role=; Max-Age=0; path=/";
    window.location.href = "/login";
  };

  return (
    <main style={{ padding: 16, fontFamily: "Arial, sans-serif", display: "grid", gap: 14 }}>
      <h1>Painel Geral</h1>
      <p>
        Perfil logado: <strong suppressHydrationWarning>{role || "desconhecido"}</strong>
      </p>
      <nav style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <a href="/fase-2">Contábil (Fase 2)</a>
        <a href="/rh">RH e Folha</a>
        <a href="/portal-servidor">Portal do Servidor</a>
        <a href="/patrimonio">Patrimônio</a>
        <a href="/public">Transparência</a>
        <button onClick={logout}>Sair</button>
      </nav>
      {message && <p>{message}</p>}
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
      </section>
    </main>
  );
}
