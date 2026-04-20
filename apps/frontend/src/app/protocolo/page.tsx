"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Protocolo = {
  id: number; numero: string; tipo: string; assunto: string; interessado: string;
  status: string; prioridade: string; data_entrada: string; prazo: string | null;
  destino_department_id: number | null;
};
type Tramitacao = {
  id: number; protocolo_id: number; acao: string; despacho: string;
  para_department_id: number; created_at: string;
};
type Department = { id: number; name: string };
type Estatisticas = Record<string, number>;

const TIPOS = ["", "requerimento", "oficio", "recurso", "processo", "denuncia", "outro"];
const PRIORIDADES = ["", "normal", "urgente", "sigiloso"];
const STATUS_LIST = ["", "protocolado", "em_tramitacao", "deferido", "indeferido", "arquivado"];
const ACOES = ["encaminhado", "deferido", "indeferido", "arquivado", "devolvido"];

function messageFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

export default function ProtocoloPage() {
  const { toast } = useToast();

  const [tab, setTab] = useState<"lista" | "novo" | "tramitar">("lista");

  // Lista
  const [protocolos, setProtocolos] = useState<ListResponse<Protocolo> | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [tipoFilter, setTipoFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Novo protocolo
  const [numero, setNumero] = useState("PROT-2026-001");
  const [tipo, setTipo] = useState("requerimento");
  const [assunto, setAssunto] = useState("");
  const [interessado, setInteressado] = useState("");
  const [interessadoDoc, setInteressadoDoc] = useState("");
  const [prioridade, setPrioridade] = useState("normal");
  const [dataEntrada, setDataEntrada] = useState("2026-01-01");
  const [prazo, setPrazo] = useState("");
  const [originDeptId, setOriginDeptId] = useState<number>(1);
  const [destDeptId, setDestDeptId] = useState<number>(1);

  // Tramitar
  const [selectedProt, setSelectedProt] = useState<number | "">("");
  const [tramitacoes, setTramitacoes] = useState<Tramitacao[]>([]);
  const [acao, setAcao] = useState("encaminhado");
  const [despacho, setDespacho] = useState("");
  const [paraDeptId, setParaDeptId] = useState<number>(1);

  // Estatísticas + departamentos
  const [stats, setStats] = useState<Estatisticas>({});
  const [departments, setDepartments] = useState<Department[]>([]);

  const loadProtocolos = async () => {
    const qs = new URLSearchParams({ page: String(page), size: "8" });
    if (statusFilter) qs.set("status", statusFilter);
    if (tipoFilter) qs.set("tipo", tipoFilter);
    if (search) qs.set("search", search);
    const data = await authJson(`/protocolo/protocolos?${qs}`);
    setProtocolos(data);
  };

  const loadStats = async () => {
    const data = await authJson("/protocolo/estatisticas");
    setStats(data || {});
  };

  const loadDepts = async () => {
    const data = await authJson("/core/departments");
    const items = data?.items || data || [];
    setDepartments(items);
    if (items[0]?.id) { setOriginDeptId(items[0].id); setDestDeptId(items[0].id); setParaDeptId(items[0].id); }
  };

  const loadTramitacoes = async (pid: number) => {
    const data = await authJson(`/protocolo/protocolos/${pid}/tramitacoes`);
    setTramitacoes(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    const t = setTimeout(() => {
      Promise.all([loadProtocolos(), loadStats(), loadDepts()]).catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = setTimeout(() => { loadProtocolos().catch((e) => toast(messageFrom(e), "error")); }, 0);
    return () => clearTimeout(t);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectProt = async (id: number | "") => {
    setSelectedProt(id);
    if (id) await loadTramitacoes(Number(id));
    else setTramitacoes([]);
  };

  const submitProtocolo = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/protocolo/protocolos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          numero, tipo, assunto, interessado, interessado_doc: interessadoDoc || null,
          prioridade, data_entrada: dataEntrada, prazo: prazo || null,
          origem_department_id: originDeptId || null,
          destino_department_id: destDeptId || null,
        }),
      });
      toast(`Protocolo ${numero} registrado.`);
      setNumero(""); setAssunto(""); setInteressado(""); setInteressadoDoc(""); setPrazo("");
      await loadProtocolos(); await loadStats();
      setTab("lista");
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const submitTramitacao = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedProt) { toast("Selecione um protocolo.", "error"); return; }
    try {
      await authJson(`/protocolo/protocolos/${selectedProt}/tramitar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ para_department_id: paraDeptId, acao, despacho }),
      });
      toast(`Protocolo ${selectedProt} — ação "${acao}" registrada.`);
      setDespacho("");
      await loadTramitacoes(Number(selectedProt));
      await loadProtocolos();
      await loadStats();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const deptName = (id: number | null) => departments.find((d) => d.id === id)?.name || (id ? String(id) : "—");

  const STATUS_CHIP: Record<string, string> = {
    protocolado: "empenhado",
    em_tramitacao: "pendente",
    deferido: "pago",
    indeferido: "baixado",
    arquivado: "baixado",
  };

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Protocolo e Processos Administrativos</h1>
      <p className="muted">Registro, tramitação e acompanhamento de processos administrativos municipais.</p>

      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/convenios">Convênios</Link>
        <Link className="btn" href="/compras">Compras</Link>
      </div>

      {/* KPI */}
      <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 8 }}>
        {Object.entries(stats).map(([s, count]) => (
          <div key={s} className="card kpi-card" style={{ padding: "12px 16px" }}>
            <p className="muted" style={{ fontSize: 12, marginBottom: 4 }}>{s.replace("_", " ")}</p>
            <p className="kpi-value" style={{ fontSize: 28 }}>{count}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="toolbar" style={{ borderBottom: "2px solid var(--border)", paddingBottom: 0, gap: 0, marginTop: 12 }}>
        {(["lista", "novo", "tramitar"] as const).map((t) => (
          <button key={t} className="btn" style={{
            borderBottomLeftRadius: 0, borderBottomRightRadius: 0,
            borderBottom: tab === t ? "3px solid var(--primary)" : "3px solid transparent",
            background: tab === t ? "var(--primary-soft)" : "#fff",
            fontWeight: tab === t ? 700 : 400,
            textTransform: "capitalize",
          }} onClick={() => setTab(t)}>
            {t === "lista" ? "Lista" : t === "novo" ? "Novo protocolo" : "Tramitar"}
          </button>
        ))}
      </div>

      {/* ─── Lista ─── */}
      {tab === "lista" && (
        <section className="card section-stack">
          <div className="toolbar">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar número, assunto ou interessado" style={{ flex: 1 }} />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {STATUS_LIST.map((s) => <option key={s} value={s}>{s || "Todos os status"}</option>)}
            </select>
            <select value={tipoFilter} onChange={(e) => setTipoFilter(e.target.value)}>
              {TIPOS.map((t) => <option key={t} value={t}>{t || "Todos os tipos"}</option>)}
            </select>
            <button className="btn" onClick={() => { setPage(1); loadProtocolos().catch((e) => toast(messageFrom(e), "error")); }}>
              Filtrar
            </button>
          </div>

          <table>
            <thead>
              <tr><th>Número</th><th>Tipo</th><th>Assunto</th><th>Interessado</th><th>Destino</th><th>Status</th><th>Prioridade</th><th>Entrada</th></tr>
            </thead>
            <tbody>
              {(protocolos?.items || []).length > 0 ? (
                (protocolos?.items || []).map((p) => (
                  <tr key={p.id} style={{ cursor: "pointer" }} onClick={() => { setSelectedProt(p.id); loadTramitacoes(p.id); setTab("tramitar"); }}>
                    <td><strong>{p.numero}</strong></td>
                    <td>{p.tipo}</td>
                    <td>{p.assunto}</td>
                    <td>{p.interessado}</td>
                    <td>{deptName(p.destino_department_id)}</td>
                    <td><span className={`chip ${STATUS_CHIP[p.status] || "empenhado"}`}>{p.status}</span></td>
                    <td><span className={`chip ${p.prioridade === "urgente" ? "pendente" : ""}`}>{p.prioridade}</span></td>
                    <td>{p.data_entrada}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={8} className="empty-state">Nenhum protocolo encontrado.</td></tr>
              )}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
            <span>Página {protocolos?.page || 1} · Total: {protocolos?.total || 0}</span>
            <button className="btn" disabled={(protocolos?.items?.length || 0) < 8} onClick={() => setPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ─── Novo Protocolo ─── */}
      {tab === "novo" && (
        <section className="card">
          <h2>Registrar novo protocolo</h2>
          <form onSubmit={submitProtocolo} style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
            <label className="field-group">Número<input value={numero} onChange={(e) => setNumero(e.target.value)} required /></label>
            <label className="field-group">
              Tipo
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                {TIPOS.filter(Boolean).map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label className="field-group" style={{ gridColumn: "1 / -1" }}>
              Assunto
              <input value={assunto} onChange={(e) => setAssunto(e.target.value)} required />
            </label>
            <label className="field-group">Interessado / Solicitante<input value={interessado} onChange={(e) => setInteressado(e.target.value)} required /></label>
            <label className="field-group">CPF/CNPJ (opcional)<input value={interessadoDoc} onChange={(e) => setInteressadoDoc(e.target.value)} /></label>
            <label className="field-group">
              Prioridade
              <select value={prioridade} onChange={(e) => setPrioridade(e.target.value)}>
                {PRIORIDADES.filter(Boolean).map((p) => <option key={p}>{p}</option>)}
              </select>
            </label>
            <label className="field-group">Data de entrada<input type="date" value={dataEntrada} onChange={(e) => setDataEntrada(e.target.value)} required /></label>
            <label className="field-group">Prazo (opcional)<input type="date" value={prazo} onChange={(e) => setPrazo(e.target.value)} /></label>
            <label className="field-group">
              Departamento de origem
              <select value={originDeptId} onChange={(e) => setOriginDeptId(Number(e.target.value))}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </label>
            <label className="field-group">
              Departamento de destino
              <select value={destDeptId} onChange={(e) => setDestDeptId(Number(e.target.value))}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </label>
            <div style={{ gridColumn: "1 / -1" }}>
              <button className="btn btn-primary" type="submit">Registrar protocolo</button>
            </div>
          </form>
        </section>
      )}

      {/* ─── Tramitar ─── */}
      {tab === "tramitar" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
          <section className="card">
            <h2>Tramitar protocolo</h2>
            <form onSubmit={submitTramitacao} className="section-stack">
              <label className="field-group">
                Protocolo
                <select value={selectedProt} onChange={(e) => handleSelectProt(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione o protocolo</option>
                  {(protocolos?.items || []).map((p) => (
                    <option key={p.id} value={p.id}>{p.numero} — {p.assunto.slice(0, 40)} [{p.status}]</option>
                  ))}
                </select>
              </label>
              <label className="field-group">
                Ação
                <select value={acao} onChange={(e) => setAcao(e.target.value)}>
                  {ACOES.map((a) => <option key={a}>{a}</option>)}
                </select>
              </label>
              <label className="field-group">
                Encaminhar para departamento
                <select value={paraDeptId} onChange={(e) => setParaDeptId(Number(e.target.value))}>
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </label>
              <label className="field-group">
                Despacho
                <textarea value={despacho} onChange={(e) => setDespacho(e.target.value)} rows={3} style={{ resize: "vertical", width: "100%" }} />
              </label>
              <button className="btn btn-primary" type="submit">Registrar tramitação</button>
            </form>
          </section>

          <section className="card section-stack">
            <h2>Histórico de tramitações{selectedProt ? ` — Protocolo #${selectedProt}` : ""}</h2>
            {tramitacoes.length > 0 ? (
              <table>
                <thead><tr><th>Ação</th><th>Para</th><th>Despacho</th><th>Data</th></tr></thead>
                <tbody>
                  {tramitacoes.map((t) => (
                    <tr key={t.id}>
                      <td><span className={`chip ${t.acao === "deferido" ? "pago" : t.acao === "indeferido" ? "baixado" : "empenhado"}`}>{t.acao}</span></td>
                      <td>{deptName(t.para_department_id)}</td>
                      <td style={{ maxWidth: 240, wordBreak: "break-word" }}>{t.despacho || "—"}</td>
                      <td>{new Date(t.created_at).toLocaleString("pt-BR")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state">{selectedProt ? "Nenhuma tramitação registrada." : "Selecione um protocolo para ver o histórico."}</p>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
