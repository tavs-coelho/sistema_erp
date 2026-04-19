"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Department = { id: number; name: string };
type Vendor = { id: number; name: string; document: string };
type FiscalYear = { id: number; year: number; active: boolean };
type Commitment = { id: number; number: string; description: string; amount: number; status: string; vendor_id: number };
type Payment = { id: number; commitment_id: number; amount: number; payment_date: string };

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const entry = document.cookie.split(";").find((item) => item.trim().startsWith(`${name}=`));
  if (!entry) return "";
  return decodeURIComponent(entry.trim().slice(name.length + 1));
}

export default function Fase2Page() {
  const [token] = useState(() => readCookie("access_token"));
  const [statusMsg, setStatusMsg] = useState("");

  const [departments, setDepartments] = useState<Department[]>([]);
  const [fiscalYears, setFiscalYears] = useState<FiscalYear[]>([]);
  const [vendors, setVendors] = useState<ListResponse<Vendor> | null>(null);
  const [commitments, setCommitments] = useState<ListResponse<Commitment> | null>(null);
  const [payments, setPayments] = useState<ListResponse<Payment> | null>(null);

  const [vendorSearch, setVendorSearch] = useState("");
  const [commitmentStatus, setCommitmentStatus] = useState("");
  const [commitmentPage, setCommitmentPage] = useState(1);
  const [paymentPage, setPaymentPage] = useState(1);

  const [departmentName, setDepartmentName] = useState("Secretaria de Planejamento");
  const [vendorName, setVendorName] = useState("Fornecedor Demo Fase 2");
  const [vendorDocument, setVendorDocument] = useState("45.123.987/0001-65");
  const [allocationCode, setAllocationCode] = useState("BA-F2-001");
  const [allocationDescription, setAllocationDescription] = useState("Dotação Fase 2");
  const [allocationAmount, setAllocationAmount] = useState(90000);
  const [selectedFiscalYear, setSelectedFiscalYear] = useState<number>(1);

  const [commitmentNumber, setCommitmentNumber] = useState("EMP-F2-001");
  const [commitmentDescription, setCommitmentDescription] = useState("Empenho para fluxo fase 2");
  const [commitmentAmount, setCommitmentAmount] = useState(12000);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<number>(1);
  const [selectedVendorId, setSelectedVendorId] = useState<number>(1);

  const [paymentCommitmentId, setPaymentCommitmentId] = useState<number>(1);
  const [paymentAmount, setPaymentAmount] = useState(12000);
  const [paymentDate, setPaymentDate] = useState("2026-04-19");

  const authHeaders = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

  const loadCore = async () => {
    const [depRes, fyRes] = await Promise.all([
      fetch(`${API_URL}/core/departments`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API_URL}/core/fiscal-years`, { headers: { Authorization: `Bearer ${token}` } }),
    ]);
    const depJson = await depRes.json();
    const fyJson = await fyRes.json();
    setDepartments(depJson || []);
    setFiscalYears(fyJson || []);
    if (depJson?.[0]?.id) setSelectedDepartmentId(depJson[0].id);
    if (fyJson?.[0]?.id) setSelectedFiscalYear(fyJson[0].id);
  };

  const loadVendors = async () => {
    const res = await fetch(`${API_URL}/accounting/vendors?search=${encodeURIComponent(vendorSearch)}&page=1&size=10`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setVendors(data);
    if (data?.items?.[0]?.id) setSelectedVendorId(data.items[0].id);
  };

  const loadCommitments = async () => {
    const res = await fetch(
      `${API_URL}/accounting/commitments?status=${encodeURIComponent(commitmentStatus)}&page=${commitmentPage}&size=5`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const data = await res.json();
    setCommitments(data);
    if (data?.items?.[0]?.id) setPaymentCommitmentId(data.items[0].id);
  };

  const loadPayments = async () => {
    const res = await fetch(`${API_URL}/accounting/payments?page=${paymentPage}&size=5`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setPayments(await res.json());
  };

  const submitDepartment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/core/departments`, { method: "POST", headers: authHeaders, body: JSON.stringify({ name: departmentName }) });
    if (!res.ok) return setStatusMsg("Falha ao criar departamento");
    setStatusMsg("Departamento criado");
    await loadCore();
  };

  const submitVendor = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/accounting/vendors`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ name: vendorName, document: vendorDocument }),
    });
    if (!res.ok) return setStatusMsg("Falha ao criar fornecedor");
    setStatusMsg("Fornecedor criado");
    await loadVendors();
  };

  const submitAllocation = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/accounting/budget-allocations`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({
        code: allocationCode,
        description: allocationDescription,
        amount: Number(allocationAmount),
        fiscal_year_id: selectedFiscalYear,
      }),
    });
    if (!res.ok) return setStatusMsg("Falha ao criar dotação");
    setStatusMsg("Dotação orçamentária criada");
  };

  const submitCommitment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/accounting/commitments`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({
        number: commitmentNumber,
        description: commitmentDescription,
        amount: Number(commitmentAmount),
        fiscal_year_id: selectedFiscalYear,
        department_id: selectedDepartmentId,
        vendor_id: selectedVendorId,
      }),
    });
    if (!res.ok) return setStatusMsg("Falha ao criar empenho");
    setStatusMsg("Empenho criado");
    await loadCommitments();
  };

  const liquidateCommitment = async (id: number) => {
    const res = await fetch(`${API_URL}/accounting/liquidate/${id}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return setStatusMsg("Falha ao liquidar empenho");
    setStatusMsg(`Empenho ${id} liquidado`);
    await loadCommitments();
  };

  const submitPayment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/accounting/payments`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ commitment_id: paymentCommitmentId, amount: Number(paymentAmount), payment_date: paymentDate }),
    });
    if (!res.ok) return setStatusMsg("Falha ao registrar pagamento");
    setStatusMsg("Pagamento registrado");
    await Promise.all([loadCommitments(), loadPayments()]);
  };

  return (
    <main className="module-page" style={{ padding: 24, fontFamily: "Arial, sans-serif" }}>
      <h1>Fluxo demonstrável — Fase 2</h1>
      <p>Admin: departamento → fornecedor → dotação → empenho → liquidação → pagamento.</p>
      <p className="muted">Cenário seeded para busca rápida: <strong>Fornecedor Demo Integrado</strong> e <strong>EMP-DEMO-001</strong>.</p>
      <p><Link href="/">Voltar ao painel</Link> | <Link href="/public">Transparência pública</Link> | <Link href="/rh">RH</Link> | <Link href="/patrimonio">Patrimônio</Link></p>
      {statusMsg && <p className={statusMsg.toLowerCase().includes("falha") || statusMsg.toLowerCase().includes("erro") ? "notice error" : "notice"}><strong>{statusMsg}</strong></p>}
      <button
        onClick={() => {
          Promise.all([loadCore(), loadVendors(), loadCommitments(), loadPayments()])
            .catch(() => setStatusMsg("Falha ao carregar listas"));
        }}
      >
        Carregar / atualizar listas
      </button>

      <section style={{ display: "grid", gap: 8, marginBottom: 20 }}>
        <form onSubmit={submitDepartment}>
          <h2>1) Criar departamento</h2>
          <input value={departmentName} onChange={(e) => setDepartmentName(e.target.value)} required />
          <button type="submit">Salvar</button>
        </form>

        <form onSubmit={submitVendor}>
          <h2>2) Criar fornecedor</h2>
          <input value={vendorName} onChange={(e) => setVendorName(e.target.value)} required />
          <input value={vendorDocument} onChange={(e) => setVendorDocument(e.target.value)} required />
          <button type="submit">Salvar</button>
        </form>

        <form onSubmit={submitAllocation}>
          <h2>3) Criar dotação orçamentária</h2>
          <input value={allocationCode} onChange={(e) => setAllocationCode(e.target.value)} required />
          <input value={allocationDescription} onChange={(e) => setAllocationDescription(e.target.value)} required />
          <input type="number" value={allocationAmount} onChange={(e) => setAllocationAmount(Number(e.target.value))} required />
          <select value={selectedFiscalYear} onChange={(e) => setSelectedFiscalYear(Number(e.target.value))}>
            {fiscalYears.map((fy) => <option key={fy.id} value={fy.id}>{fy.year}</option>)}
          </select>
          <button type="submit">Salvar</button>
        </form>

        <form onSubmit={submitCommitment}>
          <h2>4) Criar empenho</h2>
          <input value={commitmentNumber} onChange={(e) => setCommitmentNumber(e.target.value)} required />
          <input value={commitmentDescription} onChange={(e) => setCommitmentDescription(e.target.value)} required />
          <input type="number" value={commitmentAmount} onChange={(e) => setCommitmentAmount(Number(e.target.value))} required />
          <select value={selectedDepartmentId} onChange={(e) => setSelectedDepartmentId(Number(e.target.value))}>
            {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
          </select>
          <select value={selectedVendorId} onChange={(e) => setSelectedVendorId(Number(e.target.value))}>
            {(vendors?.items || []).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          <button type="submit">Salvar</button>
        </form>

        <form onSubmit={submitPayment}>
          <h2>5) Registrar pagamento</h2>
          <select value={paymentCommitmentId} onChange={(e) => setPaymentCommitmentId(Number(e.target.value))}>
            {(commitments?.items || []).map((c) => <option key={c.id} value={c.id}>{c.number}</option>)}
          </select>
          <input type="number" value={paymentAmount} onChange={(e) => setPaymentAmount(Number(e.target.value))} required />
          <input value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} required />
          <button type="submit">Salvar</button>
        </form>
      </section>

      <section>
        <h2>Lista interna de fornecedores (busca + paginação)</h2>
        <input
          placeholder="Buscar fornecedor"
          value={vendorSearch}
          onChange={(e) => {
            setVendorSearch(e.target.value);
            setTimeout(() => {
              loadVendors().catch(() => setStatusMsg("Erro ao carregar fornecedores"));
            }, 0);
          }}
        />
        <ul>
          {(vendors?.items || []).length > 0 ? (vendors?.items || []).map((v) => <li key={v.id}>{v.name} ({v.document})</li>) : <li className="empty-state">Nenhum fornecedor encontrado.</li>}
        </ul>
      </section>

      <section>
        <h2>Lista interna de empenhos (filtro + paginação)</h2>
        <label>Status: </label>
        <select
          value={commitmentStatus}
          onChange={(e) => {
            setCommitmentStatus(e.target.value);
            setCommitmentPage(1);
            setTimeout(() => {
              loadCommitments().catch(() => setStatusMsg("Erro ao carregar empenhos"));
            }, 0);
          }}
        >
          <option value="">Todos</option>
          <option value="empenhado">Empenhado</option>
          <option value="liquidado">Liquidado</option>
          <option value="pago">Pago</option>
        </select>
        <a href={`${API_URL}/accounting/reports/commitments?status=${encodeURIComponent(commitmentStatus)}&export=csv`} target="_blank"> Exportar CSV</a>
        <table border={1} cellPadding={6} style={{ marginTop: 8 }}>
          <thead>
            <tr><th>Número</th><th>Descrição</th><th>Valor</th><th>Status</th><th>Ação</th></tr>
          </thead>
          <tbody>
            {(commitments?.items || []).length > 0 ? (
              (commitments?.items || []).map((c) => (
                <tr key={c.id}>
                  <td>{c.number}</td><td>{c.description}</td><td>R$ {c.amount.toFixed(2)}</td><td>{c.status}</td>
                  <td>{c.status === "empenhado" ? <button onClick={() => liquidateCommitment(c.id)}>Liquidar</button> : "-"}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={5} className="empty-state">Nenhum empenho encontrado para o filtro atual.</td></tr>
            )}
          </tbody>
        </table>
        <button
          disabled={commitmentPage <= 1}
          onClick={() => {
            setCommitmentPage((p) => p - 1);
            setTimeout(() => {
              loadCommitments().catch(() => setStatusMsg("Erro ao carregar empenhos"));
            }, 0);
          }}
        >
          Anterior
        </button>
        <span> Página {commitments?.page || 1} </span>
        <button
          disabled={(commitments?.items?.length || 0) < 5}
          onClick={() => {
            setCommitmentPage((p) => p + 1);
            setTimeout(() => {
              loadCommitments().catch(() => setStatusMsg("Erro ao carregar empenhos"));
            }, 0);
          }}
        >
          Próxima
        </button>
      </section>

      <section>
        <h2>Lista interna de pagamentos (paginação)</h2>
        <table border={1} cellPadding={6}>
          <thead><tr><th>ID</th><th>Empenho</th><th>Valor</th><th>Data</th></tr></thead>
          <tbody>
            {(payments?.items || []).length > 0 ? (
              (payments?.items || []).map((p) => (
                <tr key={p.id}><td>{p.id}</td><td>{p.commitment_id}</td><td>R$ {p.amount.toFixed(2)}</td><td>{p.payment_date}</td></tr>
              ))
            ) : (
              <tr><td colSpan={4} className="empty-state">Nenhum pagamento encontrado.</td></tr>
            )}
          </tbody>
        </table>
        <button
          disabled={paymentPage <= 1}
          onClick={() => {
            setPaymentPage((p) => p - 1);
            setTimeout(() => {
              loadPayments().catch(() => setStatusMsg("Erro ao carregar pagamentos"));
            }, 0);
          }}
        >
          Anterior
        </button>
        <span> Página {payments?.page || 1} </span>
        <button
          disabled={(payments?.items?.length || 0) < 5}
          onClick={() => {
            setPaymentPage((p) => p + 1);
            setTimeout(() => {
              loadPayments().catch(() => setStatusMsg("Erro ao carregar pagamentos"));
            }, 0);
          }}
        >
          Próxima
        </button>
      </section>
    </main>
  );
}
