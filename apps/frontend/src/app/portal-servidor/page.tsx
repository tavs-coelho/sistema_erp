"use client";

import { useEffect, useState } from "react";

import { authDownload, authJson, readCookie } from "@/lib/auth";

type Me = { id: number; username: string; name: string; role: string };
type Payslip = { id: number; month: string; gross_amount: number; deductions: number; net_amount: number };
type IncomeStatement = { employee: string; total_liquido: number; periodos: number };

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function PortalServidorPage() {
  const [role] = useState(() => readCookie("role"));
  const [status, setStatus] = useState("");
  const [me, setMe] = useState<Me | null>(null);
  const [slips, setSlips] = useState<Payslip[]>([]);
  const [income, setIncome] = useState<IncomeStatement | null>(null);

  useEffect(() => {
    Promise.all([authJson("/employee-portal/me"), authJson("/employee-portal/payslips"), authJson("/employee-portal/income-statement")])
      .then(([meData, slipsData, incomeData]) => {
        setMe(meData);
        setSlips(slipsData || []);
        setIncome(incomeData);
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : "Sem acesso ao portal do servidor"));
  }, []);

  return (
    <main className="module-page">
      <h1>Portal do Servidor</h1>
      <p className="muted">Perfil atual: <strong suppressHydrationWarning>{role || "não identificado"}</strong> | <a href="/rh">Voltar ao RH</a></p>
      {status && <p className={status.toLowerCase().includes("erro") || status.toLowerCase().includes("falha") ? "notice error" : "notice"}><strong>{status}</strong></p>}

      <section className="card">
        <h2>Meus dados</h2>
        <p>Nome: <strong>{me?.name || "-"}</strong></p>
        <p>Usuário: <strong>{me?.username || "-"}</strong></p>
        <p>Perfil: <strong>{me?.role || "-"}</strong></p>
      </section>

      <section className="card">
        <h2>Demonstrativo de rendimentos (demo)</h2>
        <p>Servidor: <strong>{income?.employee || "-"}</strong></p>
        <p>Total líquido acumulado: <strong>R$ {income?.total_liquido?.toFixed(2) || "0,00"}</strong></p>
        <p>Períodos contabilizados: <strong>{income?.periodos || 0}</strong></p>
      </section>

      <section className="card">
        <h2>Meus holerites</h2>
        <table>
          <thead><tr><th>ID</th><th>Mês</th><th>Bruto</th><th>Descontos</th><th>Líquido</th><th>Ação</th></tr></thead>
          <tbody>
            {slips.length > 0 ? (
              slips.map((slip) => (
                <tr key={slip.id}>
                  <td>{slip.id}</td><td>{slip.month}</td><td>R$ {slip.gross_amount.toFixed(2)}</td>
                  <td>R$ {slip.deductions.toFixed(2)}</td><td>R$ {slip.net_amount.toFixed(2)}</td>
                  <td><button className="btn" onClick={() => authDownload(`/hr/payslips/${slip.id}/pdf`, `meu-holerite-${slip.month}.pdf`).catch((e) => setStatus(messageFrom(e)))}>Baixar PDF</button></td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={6} className="empty-state">Nenhum holerite disponível para o servidor logado.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
