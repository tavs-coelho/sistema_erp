"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Convenio = {
  id: number; numero: string; objeto: string; tipo: string; concedente: string;
  valor_total: number; contrapartida: number; data_inicio: string; data_fim: string;
  status: string; department_id: number | null;
};
type Desembolso = {
  id: number; convenio_id: number; numero_parcela: number; valor: number;
  data_prevista: string; data_efetiva: string | null; status: string;
};
type Saldo = {
  convenio_id: number; numero: string; valor_total: number; contrapartida: number;
  total_previsto_parcelas: number; total_recebido: number; saldo_pendente: number; percentual_recebido: number;
};
type Department = { id: number; name: string };

const STATUS_LIST = ["", "rascunho", "vigente", "encerrado", "suspenso", "rescindido"];
const TIPOS = ["", "recebimento", "repasse"];

function messageFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

export default function ConveniosPage() {
  const { toast } = useToast();

  const [tab, setTab] = useState<"lista" | "novo" | "desembolsos">("lista");

  // Lista
  const [convenios, setConvenios] = useState<ListResponse<Convenio> | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [tipoFilter, setTipoFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [vencendo, setVencendo] = useState<Convenio[]>([]);

  // Novo convênio
  const [numero, setNumero] = useState("CONV-2026-001");
  const [objeto, setObjeto] = useState("");
  const [tipo, setTipo] = useState("recebimento");
  const [concedente, setConcedente] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [valorTotal, setValorTotal] = useState(500000);
  const [contrapartida, setContrapartida] = useState(0);
  const [dataAssinatura, setDataAssinatura] = useState("2026-01-01");
  const [dataInicio, setDataInicio] = useState("2026-02-01");
  const [dataFim, setDataFim] = useState("2027-01-31");
  const [convDeptId, setConvDeptId] = useState<number>(1);

  // Desembolsos
  const [selectedConv, setSelectedConv] = useState<number | "">("");
  const [desembolsos, setDesembolsos] = useState<Desembolso[]>([]);
  const [saldo, setSaldo] = useState<Saldo | null>(null);
  const [parcela, setParcela] = useState(1);
  const [valorParcela, setValorParcela] = useState(0);
  const [dataPrevista, setDataPrevista] = useState("2026-06-01");
  const [dataEfetiva, setDataEfetiva] = useState("");
  const [desembRecebeId, setDesembRecebeId] = useState<number | "">("");

  const [departments, setDepartments] = useState<Department[]>([]);

  const loadConvenios = async () => {
    const qs = new URLSearchParams({ page: String(page), size: "8" });
    if (statusFilter) qs.set("status", statusFilter);
    if (tipoFilter) qs.set("tipo", tipoFilter);
    if (search) qs.set("search", search);
    const data = await authJson(`/convenios?${qs}`);
    setConvenios(data);
  };

  const loadVencendo = async () => {
    try {
      const data = await authJson("/convenios/vencendo");
      setVencendo(Array.isArray(data) ? data : []);
    } catch { setVencendo([]); }
  };

  const loadDepts = async () => {
    const data = await authJson("/core/departments");
    const items = data?.items || data || [];
    setDepartments(items);
    if (items[0]?.id) setConvDeptId(items[0].id);
  };

  const loadDesembolsos = async (cid: number) => {
    const data = await authJson(`/convenios/${cid}/desembolsos`);
    setDesembolsos(Array.isArray(data) ? data : []);
  };

  const loadSaldo = async (cid: number) => {
    try {
      const data = await authJson(`/convenios/${cid}/saldo`);
      setSaldo(data);
    } catch { setSaldo(null); }
  };

  useEffect(() => {
    const t = setTimeout(() => {
      Promise.all([loadConvenios(), loadVencendo(), loadDepts()]).catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = setTimeout(() => { loadConvenios().catch((e) => toast(messageFrom(e), "error")); }, 0);
    return () => clearTimeout(t);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectConv = async (id: number | "") => {
    setSelectedConv(id);
    if (id) { await loadDesembolsos(Number(id)); await loadSaldo(Number(id)); }
    else { setDesembolsos([]); setSaldo(null); }
  };

  const submitConvenio = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/convenios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          numero, objeto, tipo, concedente, cnpj_concedente: cnpj || null,
          valor_total: valorTotal, contrapartida,
          data_assinatura: dataAssinatura, data_inicio: dataInicio, data_fim: dataFim,
          department_id: convDeptId || null,
        }),
      });
      toast(`Convênio ${numero} criado.`);
      setNumero(""); setObjeto(""); setConcedente(""); setCnpj("");
      await loadConvenios(); await loadVencendo();
      setTab("lista");
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const addDesembolso = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedConv) { toast("Selecione um convênio.", "error"); return; }
    try {
      await authJson(`/convenios/${selectedConv}/desembolsos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ numero_parcela: parcela, valor: valorParcela, data_prevista: dataPrevista }),
      });
      toast(`Parcela ${parcela} registrada.`);
      setParcela((p) => p + 1);
      await loadDesembolsos(Number(selectedConv));
      await loadSaldo(Number(selectedConv));
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const registrarRecebimento = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedConv || !desembRecebeId) { toast("Selecione a parcela.", "error"); return; }
    try {
      const qs = new URLSearchParams({ data_efetiva: dataEfetiva || new Date().toISOString().slice(0, 10), status: "recebido" });
      await authJson(`/convenios/${selectedConv}/desembolsos/${desembRecebeId}?${qs}`, { method: "PATCH" });
      toast("Recebimento registrado.");
      setDataEfetiva(""); setDesembRecebeId("");
      await loadDesembolsos(Number(selectedConv));
      await loadSaldo(Number(selectedConv));
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const STATUS_CHIP: Record<string, string> = {
    vigente: "pago", encerrado: "baixado", suspenso: "pendente",
    rescindido: "baixado", rascunho: "empenhado",
  };

  const DESEMB_CHIP: Record<string, string> = {
    recebido: "pago", previsto: "empenhado", pendente: "pendente",
  };

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Módulo de Convênios</h1>
      <p className="muted">Gestão de convênios, controle de parcelas/desembolsos e monitoramento de vencimentos.</p>

      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/protocolo">Protocolo</Link>
        <Link className="btn" href="/compras">Compras</Link>
      </div>

      {/* Alerta de convênios vencendo */}
      {vencendo.length > 0 && (
        <div className="card" style={{ borderLeft: "4px solid #e09a00", background: "#fff8e6" }}>
          <h2>⚠ Convênios vencendo em 90 dias ({vencendo.length})</h2>
          <ul style={{ marginLeft: 16, marginTop: 8 }}>
            {vencendo.map((c) => (
              <li key={c.id}><strong>{c.numero}</strong> — {c.objeto.slice(0, 60)} · vence em <strong>{c.data_fim}</strong> · R$ {c.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tabs */}
      <div className="toolbar" style={{ borderBottom: "2px solid var(--border)", paddingBottom: 0, gap: 0, marginTop: 12 }}>
        {(["lista", "novo", "desembolsos"] as const).map((t) => (
          <button key={t} className="btn" style={{
            borderBottomLeftRadius: 0, borderBottomRightRadius: 0,
            borderBottom: tab === t ? "3px solid var(--primary)" : "3px solid transparent",
            background: tab === t ? "var(--primary-soft)" : "#fff",
            fontWeight: tab === t ? 700 : 400,
          }} onClick={() => setTab(t)}>
            {t === "lista" ? "Lista" : t === "novo" ? "Novo convênio" : "Desembolsos"}
          </button>
        ))}
      </div>

      {/* ─── Lista ─── */}
      {tab === "lista" && (
        <section className="card section-stack">
          <div className="toolbar">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar número, objeto ou concedente" style={{ flex: 1 }} />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {STATUS_LIST.map((s) => <option key={s} value={s}>{s || "Todos os status"}</option>)}
            </select>
            <select value={tipoFilter} onChange={(e) => setTipoFilter(e.target.value)}>
              {TIPOS.map((t) => <option key={t} value={t}>{t || "Todos os tipos"}</option>)}
            </select>
            <button className="btn" onClick={() => { setPage(1); loadConvenios().catch((e) => toast(messageFrom(e), "error")); }}>Filtrar</button>
          </div>

          <table>
            <thead>
              <tr><th>Número</th><th>Objeto</th><th>Tipo</th><th>Concedente</th><th>Valor total</th><th>Início</th><th>Término</th><th>Status</th></tr>
            </thead>
            <tbody>
              {(convenios?.items || []).length > 0 ? (
                (convenios?.items || []).map((c) => (
                  <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => { setSelectedConv(c.id); loadDesembolsos(c.id); loadSaldo(c.id); setTab("desembolsos"); }}>
                    <td><strong>{c.numero}</strong></td>
                    <td>{c.objeto.slice(0, 50)}</td>
                    <td>{c.tipo}</td>
                    <td>{c.concedente.slice(0, 40)}</td>
                    <td>R$ {c.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                    <td>{c.data_inicio}</td>
                    <td>{c.data_fim}</td>
                    <td><span className={`chip ${STATUS_CHIP[c.status] || "empenhado"}`}>{c.status}</span></td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={8} className="empty-state">Nenhum convênio encontrado.</td></tr>
              )}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
            <span>Página {convenios?.page || 1} · Total: {convenios?.total || 0}</span>
            <button className="btn" disabled={(convenios?.items?.length || 0) < 8} onClick={() => setPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ─── Novo Convênio ─── */}
      {tab === "novo" && (
        <section className="card">
          <h2>Cadastrar novo convênio</h2>
          <form onSubmit={submitConvenio} style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
            <label className="field-group">Número<input value={numero} onChange={(e) => setNumero(e.target.value)} required /></label>
            <label className="field-group">
              Tipo
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                {TIPOS.filter(Boolean).map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label className="field-group" style={{ gridColumn: "1 / -1" }}>
              Objeto / Finalidade
              <input value={objeto} onChange={(e) => setObjeto(e.target.value)} required />
            </label>
            <label className="field-group">Concedente / Convenente<input value={concedente} onChange={(e) => setConcedente(e.target.value)} required /></label>
            <label className="field-group">CNPJ do concedente<input value={cnpj} onChange={(e) => setCnpj(e.target.value)} /></label>
            <label className="field-group">Valor total (R$)<input type="number" value={valorTotal} onChange={(e) => setValorTotal(Number(e.target.value))} required /></label>
            <label className="field-group">Contrapartida (R$)<input type="number" value={contrapartida} onChange={(e) => setContrapartida(Number(e.target.value))} /></label>
            <label className="field-group">Data de assinatura<input type="date" value={dataAssinatura} onChange={(e) => setDataAssinatura(e.target.value)} required /></label>
            <label className="field-group">Início da vigência<input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} required /></label>
            <label className="field-group">Término da vigência<input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} required /></label>
            <label className="field-group">
              Secretaria/Departamento responsável
              <select value={convDeptId} onChange={(e) => setConvDeptId(Number(e.target.value))}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </label>
            <div style={{ gridColumn: "1 / -1" }}>
              <button className="btn btn-primary" type="submit">Salvar convênio</button>
            </div>
          </form>
        </section>
      )}

      {/* ─── Desembolsos ─── */}
      {tab === "desembolsos" && (
        <div style={{ display: "grid", gap: 12 }}>
          {/* Saldo */}
          {saldo && (
            <div className="card" style={{ borderLeft: "4px solid var(--primary)", background: "var(--primary-soft)" }}>
              <h2>Saldo — {saldo.numero}</h2>
              <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", marginTop: 8 }}>
                <div><p className="muted">Valor total</p><p className="kpi-value">R$ {saldo.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p></div>
                <div><p className="muted">Recebido</p><p className="kpi-value">R$ {saldo.total_recebido.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p></div>
                <div><p className="muted">Saldo pendente</p><p className="kpi-value">R$ {saldo.saldo_pendente.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p></div>
                <div><p className="muted">Execução</p><p className="kpi-value">{saldo.percentual_recebido}%</p></div>
              </div>
            </div>
          )}

          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
            {/* Registrar desembolso */}
            <section className="card">
              <h2>Adicionar parcela de desembolso</h2>
              <label className="field-group" style={{ marginBottom: 8 }}>
                Convênio
                <select value={selectedConv} onChange={(e) => handleSelectConv(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione o convênio</option>
                  {(convenios?.items || []).map((c) => <option key={c.id} value={c.id}>{c.numero} — {c.objeto.slice(0, 40)}</option>)}
                </select>
              </label>
              <form onSubmit={addDesembolso} className="section-stack">
                <label className="field-group">Nº da parcela<input type="number" value={parcela} onChange={(e) => setParcela(Number(e.target.value))} required /></label>
                <label className="field-group">Valor da parcela (R$)<input type="number" value={valorParcela} onChange={(e) => setValorParcela(Number(e.target.value))} required /></label>
                <label className="field-group">Data prevista<input type="date" value={dataPrevista} onChange={(e) => setDataPrevista(e.target.value)} required /></label>
                <button className="btn btn-primary" type="submit">Adicionar parcela</button>
              </form>
            </section>

            {/* Registrar recebimento */}
            <section className="card">
              <h2>Confirmar recebimento</h2>
              <form onSubmit={registrarRecebimento} className="section-stack">
                <label className="field-group">
                  Parcela a confirmar
                  <select value={desembRecebeId} onChange={(e) => setDesembRecebeId(e.target.value ? Number(e.target.value) : "")}>
                    <option value="">Selecione a parcela</option>
                    {desembolsos.filter((d) => d.status !== "recebido").map((d) => (
                      <option key={d.id} value={d.id}>Parcela {d.numero_parcela} — R$ {d.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} (previsto: {d.data_prevista})</option>
                    ))}
                  </select>
                </label>
                <label className="field-group">Data efetiva de recebimento<input type="date" value={dataEfetiva} onChange={(e) => setDataEfetiva(e.target.value)} /></label>
                <button className="btn btn-primary" type="submit">Confirmar recebimento</button>
              </form>
            </section>
          </div>

          {/* Tabela de desembolsos */}
          <section className="card section-stack">
            <h2>Parcelas do convênio{selectedConv ? ` #${selectedConv}` : ""}</h2>
            {desembolsos.length > 0 ? (
              <table>
                <thead><tr><th>Parcela</th><th>Valor</th><th>Data prevista</th><th>Data efetiva</th><th>Status</th></tr></thead>
                <tbody>
                  {desembolsos.map((d) => (
                    <tr key={d.id}>
                      <td>{d.numero_parcela}</td>
                      <td>R$ {d.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                      <td>{d.data_prevista}</td>
                      <td>{d.data_efetiva || "—"}</td>
                      <td><span className={`chip ${DESEMB_CHIP[d.status] || "empenhado"}`}>{d.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state">{selectedConv ? "Nenhuma parcela cadastrada." : "Selecione um convênio para ver as parcelas."}</p>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
