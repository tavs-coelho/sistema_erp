"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { apiFetch, authDownload } from "@/lib/auth";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Department = { id: number; name: string };
type Vendor = { id: number; name: string; document: string };
type FiscalYear = { id: number; year: number; active: boolean };
type Commitment = { id: number; number: string; description: string; amount: number; status: string; vendor_id: number };
type Payment = { id: number; commitment_id: number; amount: number; payment_date: string };

export default function Fase2Page() {
  const { toast } = useToast();

  const [departments, setDepartments] = useState<Department[]>([]);
  const [fiscalYears, setFiscalYears] = useState<FiscalYear[]>([]);
  const [vendors, setVendors] = useState<ListResponse<Vendor> | null>(null);
  const [commitments, setCommitments] = useState<ListResponse<Commitment> | null>(null);
  const [payments, setPayments] = useState<ListResponse<Payment> | null>(null);

  const [vendorSearch, setVendorSearch] = useState("");
  const [commitmentStatus, setCommitmentStatus] = useState("");
  const [commitmentPage, setCommitmentPage] = useState(1);
  const [paymentPage, setPaymentPage] = useState(1);

  const [departmentName, setDepartmentName] = useState("");
  const [newFiscalYear, setNewFiscalYear] = useState(new Date().getFullYear());
  const [vendorName, setVendorName] = useState("");
  const [vendorDocument, setVendorDocument] = useState("");
  const [allocationCode, setAllocationCode] = useState("");
  const [allocationDescription, setAllocationDescription] = useState("");
  const [allocationAmount, setAllocationAmount] = useState(0);
  const [selectedFiscalYear, setSelectedFiscalYear] = useState<number>(1);

  const [commitmentNumber, setCommitmentNumber] = useState("");
  const [commitmentDescription, setCommitmentDescription] = useState("");
  const [commitmentAmount, setCommitmentAmount] = useState(0);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<number>(1);
  const [selectedVendorId, setSelectedVendorId] = useState<number>(1);

  const [paymentCommitmentId, setPaymentCommitmentId] = useState<number>(1);
  const [paymentAmount, setPaymentAmount] = useState(12000);
  const [paymentDate, setPaymentDate] = useState("");

  const authHeaders = { "Content-Type": "application/json" };

  const loadCore = async () => {
    const [depRes, fyRes] = await Promise.all([
      apiFetch(`/core/departments`, {}),
      apiFetch(`/core/fiscal-years`, {}),
    ]);
    const depJson = await depRes.json();
    const fyJson = await fyRes.json();
    setDepartments(depJson || []);
    setFiscalYears(fyJson || []);
    if (depJson?.[0]?.id) setSelectedDepartmentId(depJson[0].id);
    if (fyJson?.[0]?.id) setSelectedFiscalYear(fyJson[0].id);
  };

  const loadVendors = async () => {
    const res = await apiFetch(`/accounting/vendors?search=${encodeURIComponent(vendorSearch)}&page=1&size=10`, {
      
    });
    const data = await res.json();
    setVendors(data);
    if (data?.items?.[0]?.id) setSelectedVendorId(data.items[0].id);
  };

  const loadCommitments = async () => {
    const res = await apiFetch(
      `/accounting/commitments?status=${encodeURIComponent(commitmentStatus)}&page=${commitmentPage}&size=5`,
      {},
    );
    const data = await res.json();
    setCommitments(data);
    if (data?.items?.[0]?.id) setPaymentCommitmentId(data.items[0].id);
  };

  const loadPayments = async () => {
    const res = await apiFetch(`/accounting/payments?page=${paymentPage}&size=5`, {
      
    });
    setPayments(await res.json());
  };

  const submitFiscalYear = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiFetch("/core/fiscal-years", {
        method: "POST", body: JSON.stringify({ year: newFiscalYear, active: true }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Falha ao criar exercício");
      toast("Exercício financeiro cadastrado", "success");
      await loadCore();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Erro ao criar exercício", "error");
    }
  };

  const submitDepartment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await apiFetch(`/core/departments`, { method: "POST", headers: authHeaders, body: JSON.stringify({ name: departmentName }) });
    if (!res.ok) { toast("Falha ao criar departamento", "error"); return; }
    toast("Departamento criado");
    await loadCore();
  };

  const submitVendor = async (e: FormEvent) => {
    e.preventDefault();
    const res = await apiFetch(`/accounting/vendors`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ name: vendorName, document: vendorDocument }),
    });
    if (!res.ok) { toast("Falha ao criar fornecedor", "error"); return; }
    toast("Fornecedor criado");
    await loadVendors();
  };

  const submitAllocation = async (e: FormEvent) => {
    e.preventDefault();
    const res = await apiFetch(`/accounting/budget-allocations`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({
        code: allocationCode,
        description: allocationDescription,
        amount: Number(allocationAmount),
        fiscal_year_id: selectedFiscalYear,
      }),
    });
    if (!res.ok) { toast("Falha ao criar dotação", "error"); return; }
    toast("Dotação orçamentária criada");
  };

  const submitCommitment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await apiFetch(`/accounting/commitments`, {
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
    if (!res.ok) { toast("Falha ao criar empenho", "error"); return; }
    toast("Empenho criado");
    await loadCommitments();
  };

  const liquidateCommitment = async (id: number) => {
    const res = await apiFetch(`/accounting/liquidate/${id}`, { method: "POST",  });
    if (!res.ok) { toast("Falha ao liquidar empenho", "error"); return; }
    toast(`Empenho ${id} liquidado`);
    await loadCommitments();
  };

  const submitPayment = async (e: FormEvent) => {
    e.preventDefault();
    const res = await apiFetch(`/accounting/payments`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ commitment_id: paymentCommitmentId, amount: Number(paymentAmount), payment_date: paymentDate }),
    });
    if (!res.ok) { toast("Falha ao registrar pagamento", "error"); return; }
    toast("Pagamento registrado");
    await Promise.all([loadCommitments(), loadPayments()]);
  };

  useEffect(() => {
    const task = setTimeout(() => {
      void Promise.all([loadCore(), loadVendors(), loadCommitments(), loadPayments()])
        .catch(() => toast("Não foi possível carregar os registros. Verifique a sessão.", "error"));
    }, 0);
    return () => clearTimeout(task);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="module-page">
      <h1>Execução orçamentária e financeira</h1>
      <p>Admin: departamento → fornecedor → dotação → empenho → liquidação → pagamento.</p>
      <div className="toolbar">
        <Link className="btn" href="/">Voltar ao painel</Link>
        <Link className="btn" href="/public">Transparência</Link>
        <Link className="btn" href="/rh">RH</Link>
        <Link className="btn" href="/patrimonio">Patrimônio</Link>
      </div>

      <button className="btn"
        onClick={() => {
          Promise.all([loadCore(), loadVendors(), loadCommitments(), loadPayments()])
            .catch(() => toast("Falha ao carregar listas", "error"));
        }}
      >
        Carregar / atualizar listas
      </button>

      <section className="auto-grid section-top">
        <form onSubmit={submitFiscalYear} className="card section-stack">
          <h2>0) Exercício financeiro</h2>
          <label className="field-group">Ano
            <input type="number" min={2000} max={2100}
              value={newFiscalYear}
              onChange={(e) => setNewFiscalYear(Number(e.target.value))} required />
          </label>
          <button className="btn btn-primary" type="submit">Cadastrar exercício</button>
          <p className="muted">Cadastre o exercício antes de incluir dotações e empenhos.</p>
        </form>
        <form onSubmit={submitDepartment} className="card section-stack">
          <h2>1) Criar departamento</h2>
          <label className="field-group">Nome do departamento
            <input value={departmentName} onChange={(e) => setDepartmentName(e.target.value)} required />
          </label>
          <button className="btn btn-primary" type="submit">Salvar</button>
        </form>

        <form onSubmit={submitVendor} className="card section-stack">
          <h2>2) Criar fornecedor</h2>
          <label className="field-group">Nome do fornecedor
            <input value={vendorName} onChange={(e) => setVendorName(e.target.value)} required />
          </label>
          <label className="field-group">Documento
            <input value={vendorDocument} onChange={(e) => setVendorDocument(e.target.value)} required />
          </label>
          <button className="btn btn-primary" type="submit">Salvar</button>
        </form>

        <form onSubmit={submitAllocation} className="card section-stack">
          <h2>3) Criar dotação orçamentária</h2>
          <label className="field-group">Código
            <input value={allocationCode} onChange={(e) => setAllocationCode(e.target.value)} required />
          </label>
          <label className="field-group">Descrição
            <input value={allocationDescription} onChange={(e) => setAllocationDescription(e.target.value)} required />
          </label>
          <label className="field-group">Valor
            <input type="number" value={allocationAmount} onChange={(e) => setAllocationAmount(Number(e.target.value))} required />
          </label>
          <label className="field-group">Exercício
            <select value={selectedFiscalYear} onChange={(e) => setSelectedFiscalYear(Number(e.target.value))}>
              {fiscalYears.map((fy) => <option key={fy.id} value={fy.id}>{fy.year}</option>)}
            </select>
          </label>
          <button className="btn btn-primary" type="submit">Salvar</button>
        </form>

        <form onSubmit={submitCommitment} className="card section-stack">
          <h2>4) Criar empenho</h2>
          <label className="field-group">Número
            <input value={commitmentNumber} onChange={(e) => setCommitmentNumber(e.target.value)} required />
          </label>
          <label className="field-group">Descrição
            <input value={commitmentDescription} onChange={(e) => setCommitmentDescription(e.target.value)} required />
          </label>
          <label className="field-group">Valor
            <input type="number" value={commitmentAmount} onChange={(e) => setCommitmentAmount(Number(e.target.value))} required />
          </label>
          <label className="field-group">Departamento
            <select value={selectedDepartmentId} onChange={(e) => setSelectedDepartmentId(Number(e.target.value))}>
              {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
            </select>
          </label>
          <label className="field-group">Fornecedor
            <select value={selectedVendorId} onChange={(e) => setSelectedVendorId(Number(e.target.value))}>
              {(vendors?.items || []).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </label>
          <button className="btn btn-primary" type="submit">Salvar</button>
        </form>

        <form onSubmit={submitPayment} className="card section-stack">
          <h2>5) Registrar pagamento</h2>
          <label className="field-group">Empenho
            <select value={paymentCommitmentId} onChange={(e) => setPaymentCommitmentId(Number(e.target.value))}>
              {(commitments?.items || []).map((c) => <option key={c.id} value={c.id}>{c.number}</option>)}
            </select>
          </label>
          <label className="field-group">Valor
            <input type="number" value={paymentAmount} onChange={(e) => setPaymentAmount(Number(e.target.value))} required />
          </label>
          <label className="field-group">Data de pagamento
            <input value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} required />
          </label>
          <button className="btn btn-primary" type="submit">Salvar</button>
        </form>
      </section>

      <section className="card section-stack">
        <h2>Lista interna de fornecedores (busca + paginação)</h2>
        <input
          placeholder="Buscar fornecedor"
          value={vendorSearch}
          onChange={(e) => {
            setVendorSearch(e.target.value);
            setTimeout(() => {
              loadVendors().catch(() => toast("Erro ao carregar fornecedores", "error"));
            }, 0);
          }}
        />
        <ul className="list-indent">
          {(vendors?.items || []).length > 0 ? (vendors?.items || []).map((v) => <li key={v.id}>{v.name} ({v.document})</li>) : <li className="empty-state">Nenhum fornecedor encontrado.</li>}
        </ul>
      </section>

      <section className="card section-stack">
        <h2>Lista interna de empenhos (filtro + paginação)</h2>
        <label className="field-group">Status
        <select
          value={commitmentStatus}
          onChange={(e) => {
            setCommitmentStatus(e.target.value);
            setCommitmentPage(1);
            setTimeout(() => {
              loadCommitments().catch(() => toast("Erro ao carregar empenhos", "error"));
            }, 0);
          }}
        >
          <option value="">Todos</option>
          <option value="empenhado">Empenhado</option>
          <option value="liquidado">Liquidado</option>
          <option value="pago">Pago</option>
        </select>
        </label>
        <button className="btn" type="button" onClick={() => { void authDownload(`/accounting/reports/commitments?status=${encodeURIComponent(commitmentStatus)}&export=csv`, "empenhos.csv").catch(() => toast("Erro ao exportar empenhos", "error")); }}>Exportar CSV</button>
        <table className="mt-2">
          <thead>
            <tr><th>Número</th><th>Descrição</th><th>Valor</th><th>Status</th><th>Ação</th></tr>
          </thead>
          <tbody>
            {(commitments?.items || []).length > 0 ? (
              (commitments?.items || []).map((c) => (
                <tr key={c.id}>
                  <td>{c.number}</td><td>{c.description}</td><td>R$ {c.amount.toFixed(2)}</td><td><span className={`chip ${c.status}`}>{c.status}</span></td>
                  <td>{c.status === "empenhado" ? <button className="btn" onClick={() => liquidateCommitment(c.id)}>Liquidar</button> : "-"}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={5} className="empty-state">Nenhum empenho encontrado para o filtro atual.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
        <button className="btn"
          disabled={commitmentPage <= 1}
          onClick={() => {
            setCommitmentPage((p) => p - 1);
            setTimeout(() => {
              loadCommitments().catch(() => toast("Erro ao carregar empenhos", "error"));
            }, 0);
          }}
        >
          Anterior
        </button>
        <span> Página {commitments?.page || 1} </span>
        <button className="btn"
          disabled={(commitments?.items?.length || 0) < 5}
          onClick={() => {
            setCommitmentPage((p) => p + 1);
            setTimeout(() => {
              loadCommitments().catch(() => toast("Erro ao carregar empenhos", "error"));
            }, 0);
          }}
        >
          Próxima
        </button>
        </div>
      </section>

      <section className="card section-stack">
        <h2>Lista interna de pagamentos (paginação)</h2>
        <table>
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
        <div className="pagination">
        <button className="btn"
          disabled={paymentPage <= 1}
          onClick={() => {
            setPaymentPage((p) => p - 1);
            setTimeout(() => {
              loadPayments().catch(() => toast("Erro ao carregar pagamentos", "error"));
            }, 0);
          }}
        >
          Anterior
        </button>
        <span> Página {payments?.page || 1} </span>
        <button className="btn"
          disabled={(payments?.items?.length || 0) < 5}
          onClick={() => {
            setPaymentPage((p) => p + 1);
            setTimeout(() => {
              loadPayments().catch(() => toast("Erro ao carregar pagamentos", "error"));
            }, 0);
          }}
        >
          Próxima
        </button>
        </div>
      </section>
    </main>
  );
}
