"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Process = { id: number; number: string; object_description: string; status: string };
type Contract = { id: number; number: string; process_id: number; vendor_id: number; start_date: string; end_date: string; amount: number; status: string };
type Addendum = { id: number; contract_id: number; description: string; amount_delta: number };
type Vendor = { id: number; name: string; document: string };

const PROCESS_STATUSES = ["", "aberto", "em_andamento", "homologado", "cancelado"];
const CONTRACT_STATUSES = ["", "vigente", "encerrado", "suspenso"];

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function ComprasPage() {
  const { toast } = useToast();

  // Processos
  const [processes, setProcesses] = useState<ListResponse<Process> | null>(null);
  const [procStatusFilter, setProcStatusFilter] = useState("");
  const [procSearch, setProcSearch] = useState("");
  const [procPage, setProcPage] = useState(1);

  // Formulário novo processo
  const [procNumber, setProcNumber] = useState("");
  const [procDescription, setProcDescription] = useState("");

  // Contratos
  const [contracts, setContracts] = useState<ListResponse<Contract> | null>(null);
  const [contractStatusFilter, setContractStatusFilter] = useState("");
  const [contractPage, setContractPage] = useState(1);

  // Formulário novo contrato
  const [ctNumber, setCtNumber] = useState("");
  const [ctProcessId, setCtProcessId] = useState<number>(0);
  const [ctVendorId, setCtVendorId] = useState<number>(1);
  const [ctStartDate, setCtStartDate] = useState("2026-01-01");
  const [ctEndDate, setCtEndDate] = useState("2026-12-31");
  const [ctAmount, setCtAmount] = useState(50000);

  // Aditivos
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | "">("");
  const [addenda, setAddenda] = useState<Addendum[]>([]);
  const [addDescription, setAddDescription] = useState("");
  const [addAmountDelta, setAddAmountDelta] = useState(0);

  // Contratos vencendo
  const [expiring, setExpiring] = useState<Contract[]>([]);

  const loadProcesses = async () => {
    const qs = new URLSearchParams({ page: String(procPage), size: "8" });
    if (procStatusFilter) qs.set("status", procStatusFilter);
    if (procSearch) qs.set("search", procSearch);
    const data = await authJson(`/procurement/processes?${qs}`);
    setProcesses(data);
    if (data?.items?.[0]?.id && !ctProcessId) setCtProcessId(data.items[0].id);
  };

  const loadContracts = async () => {
    const qs = new URLSearchParams({ page: String(contractPage), size: "8" });
    if (contractStatusFilter) qs.set("status", contractStatusFilter);
    const data = await authJson(`/procurement/contracts?${qs}`);
    setContracts(data);
  };

  const loadVendors = async () => {
    const data = await authJson("/accounting/vendors?page=1&size=100");
    setVendors(data?.items || []);
    if (data?.items?.[0]?.id) setCtVendorId(data.items[0].id);
  };

  const loadExpiring = async () => {
    const data = await authJson("/procurement/contracts/expiring?days=90");
    setExpiring(Array.isArray(data) ? data : []);
  };

  const loadAddenda = async (contractId: number) => {
    try {
      const data = await authJson(`/procurement/contracts/${contractId}/addenda`);
      setAddenda(Array.isArray(data) ? data : []);
    } catch {
      setAddenda([]);
    }
  };

  const refreshAll = async () => {
    try {
      await Promise.all([loadProcesses(), loadContracts(), loadVendors(), loadExpiring()]);
    } catch (e) {
      toast(messageFrom(e), "error");
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      refreshAll();
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadProcesses().catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [procPage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadContracts().catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contractPage]);

  const createProcess = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/procurement/processes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ number: procNumber, object_description: procDescription, status: "aberto" }),
      });
      toast("Processo licitatório criado.");
      setProcNumber(""); setProcDescription("");
      await loadProcesses();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const awardProcess = async (id: number) => {
    try {
      await authJson(`/procurement/processes/${id}/award`, { method: "POST" });
      toast(`Processo ${id} homologado.`);
      await loadProcesses();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const createContract = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/procurement/contracts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          number: ctNumber,
          process_id: Number(ctProcessId),
          vendor_id: Number(ctVendorId),
          start_date: ctStartDate,
          end_date: ctEndDate,
          amount: Number(ctAmount),
          status: "vigente",
        }),
      });
      toast("Contrato criado.");
      setCtNumber("");
      await loadContracts();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const handleSelectContract = async (id: number | "") => {
    setSelectedContractId(id);
    if (id) await loadAddenda(Number(id));
    else setAddenda([]);
  };

  const addAddendumSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedContractId) { toast("Selecione um contrato.", "error"); return; }
    try {
      const qs = new URLSearchParams({ description: addDescription, amount_delta: String(addAmountDelta) });
      await authJson(`/procurement/contracts/${selectedContractId}/addenda?${qs}`, { method: "POST" });
      toast("Aditivo registrado.");
      setAddDescription(""); setAddAmountDelta(0);
      await loadAddenda(Number(selectedContractId));
      await loadContracts();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  return (
    <main className="module-page">
      <h1>Módulo de Compras e Contratos</h1>
      <p className="muted">Processos licitatórios, contratos, aditivos e alertas de vencimento.</p>

      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/fase-2">Contábil</Link>
        <Link className="btn" href="/orcamento">Orçamento (PPA/LDO/LOA)</Link>
      </div>

      {/* ─── KPI de contratos vencendo ─── */}
      {expiring.length > 0 && (
        <div className="card card-warn">
          <h2>⚠ Contratos vencendo em 90 dias ({expiring.length})</h2>
          <ul className="list-indent">
            {expiring.map((c) => (
              <li key={c.id}>
                <strong>{c.number}</strong> — vence em <strong>{c.end_date}</strong> · R$ {c.amount.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="auto-grid-lg">

        {/* ─── Novo processo ─── */}
        <section className="card">
          <h2>1) Criar processo licitatório</h2>
          <form onSubmit={createProcess} className="section-stack">
            <label className="field-group">
              Número do processo
              <input value={procNumber} onChange={(e) => setProcNumber(e.target.value)} placeholder="PROC-2026-001" required />
            </label>
            <label className="field-group">
              Objeto / descrição
              <input value={procDescription} onChange={(e) => setProcDescription(e.target.value)} placeholder="Aquisição de..." required />
            </label>
            <button className="btn btn-primary" type="submit">Salvar processo</button>
          </form>
        </section>

        {/* ─── Novo contrato ─── */}
        <section className="card">
          <h2>2) Criar contrato</h2>
          <form onSubmit={createContract} className="section-stack">
            <label className="field-group">
              Número do contrato
              <input value={ctNumber} onChange={(e) => setCtNumber(e.target.value)} placeholder="CT-2026-001" required />
            </label>
            <label className="field-group">
              Processo vinculado
              <select value={ctProcessId} onChange={(e) => setCtProcessId(Number(e.target.value))}>
                {(processes?.items || []).map((p) => (
                  <option key={p.id} value={p.id}>{p.number} — {p.object_description.slice(0, 40)}</option>
                ))}
              </select>
            </label>
            <label className="field-group">
              Fornecedor
              <select value={ctVendorId} onChange={(e) => setCtVendorId(Number(e.target.value))}>
                {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </label>
            <label className="field-group">
              Início
              <input type="date" value={ctStartDate} onChange={(e) => setCtStartDate(e.target.value)} required />
            </label>
            <label className="field-group">
              Término
              <input type="date" value={ctEndDate} onChange={(e) => setCtEndDate(e.target.value)} required />
            </label>
            <label className="field-group">
              Valor (R$)
              <input type="number" value={ctAmount} onChange={(e) => setCtAmount(Number(e.target.value))} required />
            </label>
            <button className="btn btn-primary" type="submit">Salvar contrato</button>
          </form>
        </section>

        {/* ─── Aditivo ─── */}
        <section className="card">
          <h2>3) Registrar aditivo contratual</h2>
          <form onSubmit={addAddendumSubmit} className="section-stack">
            <label className="field-group">
              Contrato
              <select value={selectedContractId} onChange={(e) => handleSelectContract(e.target.value ? Number(e.target.value) : "")}>
                <option value="">Selecione um contrato</option>
                {(contracts?.items || []).map((c) => (
                  <option key={c.id} value={c.id}>{c.number} (R$ {c.amount.toFixed(2)})</option>
                ))}
              </select>
            </label>
            <label className="field-group">
              Descrição do aditivo
              <input value={addDescription} onChange={(e) => setAddDescription(e.target.value)} placeholder="Prorrogação de prazo..." required />
            </label>
            <label className="field-group">
              Acréscimo de valor (R$)
              <input type="number" value={addAmountDelta} onChange={(e) => setAddAmountDelta(Number(e.target.value))} />
            </label>
            <button className="btn btn-primary" type="submit">Salvar aditivo</button>
          </form>

          {addenda.length > 0 && (
            <div className="mt-2">
              <p className="muted">Aditivos do contrato selecionado:</p>
              <ul className="list-indent">
                {addenda.map((a) => (
                  <li key={a.id}>{a.description} · R$ {a.amount_delta >= 0 ? "+" : ""}{a.amount_delta.toFixed(2)}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      {/* ─── Lista de processos ─── */}
      <section className="card section-stack">
        <h2>Processos licitatórios</h2>
        <div className="toolbar">
          <input
            value={procSearch}
            onChange={(e) => setProcSearch(e.target.value)}
            placeholder="Buscar objeto"
          />
          <select value={procStatusFilter} onChange={(e) => setProcStatusFilter(e.target.value)}>
            {PROCESS_STATUSES.map((s) => <option key={s} value={s}>{s || "Todos os status"}</option>)}
          </select>
          <button className="btn" onClick={() => { setProcPage(1); loadProcesses().catch((e) => toast(messageFrom(e), "error")); }}>
            Filtrar
          </button>
        </div>
        <table>
          <thead>
            <tr><th>Número</th><th>Objeto</th><th>Status</th><th>Ações</th></tr>
          </thead>
          <tbody>
            {(processes?.items || []).length > 0 ? (
              (processes?.items || []).map((p) => (
                <tr key={p.id}>
                  <td>{p.number}</td>
                  <td>{p.object_description}</td>
                  <td><span className={`chip ${p.status === "homologado" ? "pago" : p.status === "cancelado" ? "baixado" : "empenhado"}`}>{p.status}</span></td>
                  <td>
                    {p.status === "aberto" || p.status === "em_andamento" ? (
                      <button className="btn" onClick={() => awardProcess(p.id)}>Homologar</button>
                    ) : "—"}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={4} className="empty-state">Nenhum processo encontrado.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={procPage <= 1} onClick={() => setProcPage((p) => p - 1)}>Anterior</button>
          <span>Página {processes?.page || 1} · Total: {processes?.total || 0}</span>
          <button className="btn" disabled={(processes?.items?.length || 0) < 8} onClick={() => setProcPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      {/* ─── Lista de contratos ─── */}
      <section className="card section-stack">
        <h2>Contratos</h2>
        <div className="toolbar">
          <select value={contractStatusFilter} onChange={(e) => setContractStatusFilter(e.target.value)}>
            {CONTRACT_STATUSES.map((s) => <option key={s} value={s}>{s || "Todos os status"}</option>)}
          </select>
          <button className="btn" onClick={() => { setContractPage(1); loadContracts().catch((e) => toast(messageFrom(e), "error")); }}>
            Filtrar
          </button>
        </div>
        <table>
          <thead>
            <tr><th>Número</th><th>Processo</th><th>Fornecedor</th><th>Início</th><th>Término</th><th>Valor</th><th>Status</th></tr>
          </thead>
          <tbody>
            {(contracts?.items || []).length > 0 ? (
              (contracts?.items || []).map((c) => (
                <tr key={c.id}>
                  <td>{c.number}</td>
                  <td>{c.process_id}</td>
                  <td>{vendors.find((v) => v.id === c.vendor_id)?.name || c.vendor_id}</td>
                  <td>{c.start_date}</td>
                  <td>{c.end_date}</td>
                  <td>R$ {c.amount.toFixed(2)}</td>
                  <td><span className={`chip ${c.status === "vigente" ? "pago" : c.status === "encerrado" ? "baixado" : "empenhado"}`}>{c.status}</span></td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={7} className="empty-state">Nenhum contrato encontrado.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={contractPage <= 1} onClick={() => setContractPage((p) => p - 1)}>Anterior</button>
          <span>Página {contracts?.page || 1} · Total: {contracts?.total || 0}</span>
          <button className="btn" disabled={(contracts?.items?.length || 0) < 8} onClick={() => setContractPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>
    </main>
  );
}
