"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

// ── Types ─────────────────────────────────────────────────────────────────────
type Paged<T> = { total: number; page: number; size: number; items: T[] };
type Commitment  = { id: number; number: string; description: string; amount: number; status: string };
type Contract    = { id: number; number: string; start_date: string; end_date: string; amount: number; status: string };
type Licitacao   = { id: number; number: string; object_description: string; status: string };
type Convenio    = { id: number; numero: string; objeto: string; concedente: string; tipo: string; valor_total: number; data_assinatura: string; status: string };
type Arrecadacao = { id: number; tributo: string; competencia: string; exercicio: number; valor_total: number; data_pagamento: string };
type DividaItem  = { numero_inscricao: string; tributo: string; exercicio: number; valor_original: number; valor_atualizado: number; data_inscricao: string; status: string };
type Stats = {
  empenhos: { total: number; valor: number };
  contratos: { total: number; valor: number };
  licitacoes: { total: number };
  convenios: { total: number; valor: number };
  arrecadacao_tributaria: { arrecadado: number; divida_ativa: number };
};

type Tab = "inicio" | "empenhos" | "contratos" | "licitacoes" | "convenios" | "arrecadacao" | "divida";

function fmt(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

function csvUrl(base: string, params: Record<string, string>): string {
  const qs = new URLSearchParams({ ...params, export: "csv" });
  return `${API_URL}${base}?${qs.toString()}`;
}

async function publicFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

const TABS: { key: Tab; label: string }[] = [
  { key: "inicio",      label: "Painel Geral" },
  { key: "empenhos",    label: "Empenhos" },
  { key: "contratos",   label: "Contratos" },
  { key: "licitacoes",  label: "Licitações" },
  { key: "convenios",   label: "Convênios" },
  { key: "arrecadacao", label: "Arrecadação" },
  { key: "divida",      label: "Dívida Ativa" },
];

// ── Main component ─────────────────────────────────────────────────────────────
export default function PublicPage() {
  const [tab, setTab] = useState<Tab>("inicio");

  // Global stats
  const [stats, setStats] = useState<Stats | null>(null);

  // Empenhos
  const [empenhos, setEmpenhos]   = useState<Paged<Commitment> | null>(null);
  const [empSearch, setEmpSearch] = useState("");
  const [empPage, setEmpPage]     = useState(1);

  // Contratos
  const [contratos, setContratos]     = useState<Paged<Contract> | null>(null);
  const [ctSearch, setCtSearch]       = useState("");
  const [ctStatus, setCtStatus]       = useState("");
  const [ctPage, setCtPage]           = useState(1);

  // Licitações
  const [licitacoes, setLicitacoes]   = useState<Paged<Licitacao> | null>(null);
  const [lcSearch, setLcSearch]       = useState("");
  const [lcStatus, setLcStatus]       = useState("");
  const [lcPage, setLcPage]           = useState(1);

  // Convênios
  const [convenios, setConvenios]     = useState<Paged<Convenio> | null>(null);
  const [cvSearch, setCvSearch]       = useState("");
  const [cvTipo, setCvTipo]           = useState("");
  const [cvPage, setCvPage]           = useState(1);

  // Arrecadação
  const [arrecadacao, setArrecadacao] = useState<Paged<Arrecadacao> | null>(null);
  const [arTributo, setArTributo]     = useState("");
  const [arPage, setArPage]           = useState(1);

  // Dívida ativa
  const [dividas, setDividas]         = useState<Paged<DividaItem> | null>(null);
  const [dvTributo, setDvTributo]     = useState("");
  const [dvPage, setDvPage]           = useState(1);

  useEffect(() => {
    const t = setTimeout(() => {
      publicFetch<Stats>("/public/stats").then(setStats).catch(() => {});
    }, 0);
    return () => clearTimeout(t);
  }, []);

  const loadEmpenhos = () =>
    publicFetch<Paged<Commitment>>(`/public/commitments?search=${encodeURIComponent(empSearch)}&page=${empPage}&size=10`)
      .then(setEmpenhos).catch(() => {});

  const loadContratos = () =>
    publicFetch<Paged<Contract>>(`/public/contracts?search=${encodeURIComponent(ctSearch)}&status=${ctStatus}&page=${ctPage}&size=10`)
      .then(setContratos).catch(() => {});

  const loadLicitacoes = () =>
    publicFetch<Paged<Licitacao>>(`/public/licitacoes?search=${encodeURIComponent(lcSearch)}&status=${lcStatus}&page=${lcPage}&size=10`)
      .then(setLicitacoes).catch(() => {});

  const loadConvenios = () =>
    publicFetch<Paged<Convenio>>(`/public/convenios?search=${encodeURIComponent(cvSearch)}&tipo=${cvTipo}&page=${cvPage}&size=10`)
      .then(setConvenios).catch(() => {});

  const loadArrecadacao = () =>
    publicFetch<Paged<Arrecadacao>>(`/public/arrecadacao?tributo=${arTributo}&page=${arPage}&size=10`)
      .then(setArrecadacao).catch(() => {});

  const loadDividas = () =>
    publicFetch<Paged<DividaItem>>(`/public/divida-ativa?tributo=${dvTributo}&page=${dvPage}&size=10`)
      .then(setDividas).catch(() => {});

  // Load data on tab change
  useEffect(() => {
    const t = setTimeout(() => {
      if (tab === "empenhos")    loadEmpenhos();
      if (tab === "contratos")   loadContratos();
      if (tab === "licitacoes")  loadLicitacoes();
      if (tab === "convenios")   loadConvenios();
      if (tab === "arrecadacao") loadArrecadacao();
      if (tab === "divida")      loadDividas();
    }, 0);
    return () => clearTimeout(t);
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reload on pagination
  useEffect(() => { const t = setTimeout(() => loadEmpenhos(), 0); return () => clearTimeout(t); }, [empPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => loadContratos(), 0); return () => clearTimeout(t); }, [ctPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => loadLicitacoes(), 0); return () => clearTimeout(t); }, [lcPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => loadConvenios(), 0); return () => clearTimeout(t); }, [cvPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => loadArrecadacao(), 0); return () => clearTimeout(t); }, [arPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setTimeout(() => loadDividas(), 0); return () => clearTimeout(t); }, [dvPage]); // eslint-disable-line react-hooks/exhaustive-deps


  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Portal da Transparência Municipal</h1>
      <p className="muted">Consulta pública irrestrita de despesas, contratos, licitações, convênios e arrecadação. Não requer autenticação.</p>

      {/* Tabs */}
      <div className="toolbar" style={{ borderBottom: "2px solid var(--border)", paddingBottom: 0, gap: 0, marginTop: 12 }}>
        {TABS.map((t) => (
          <button key={t.key} className="btn" style={{
            borderBottomLeftRadius: 0, borderBottomRightRadius: 0,
            borderBottom: tab === t.key ? "3px solid var(--primary)" : "3px solid transparent",
            background: tab === t.key ? "var(--primary-soft)" : "#fff",
            fontWeight: tab === t.key ? 700 : 400,
          }} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Painel Geral ─────────────────────────────────────────────────────── */}
      {tab === "inicio" && (
        <section className="section-stack">
          <p style={{ marginTop: 12 }}>Indicadores consolidados do município — atualizados em tempo real a partir dos sistemas internos.</p>
          {stats ? (
            <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", marginTop: 8 }}>
              <div className="card kpi-card"><p className="muted">Empenhos registrados</p><p className="kpi-value">{stats.empenhos.total}</p><p className="muted">{fmt(stats.empenhos.valor)}</p></div>
              <div className="card kpi-card"><p className="muted">Contratos vigentes</p><p className="kpi-value">{stats.contratos.total}</p><p className="muted">{fmt(stats.contratos.valor)}</p></div>
              <div className="card kpi-card"><p className="muted">Processos licitatórios</p><p className="kpi-value">{stats.licitacoes.total}</p></div>
              <div className="card kpi-card"><p className="muted">Convênios publicados</p><p className="kpi-value">{stats.convenios.total}</p><p className="muted">{fmt(stats.convenios.valor)}</p></div>
              <div className="card kpi-card"><p className="muted">Arrecadação tributária</p><p className="kpi-value">{fmt(stats.arrecadacao_tributaria.arrecadado)}</p></div>
              <div className="card kpi-card"><p className="muted">Dívida ativa ativa/ajuizada</p><p className="kpi-value">{fmt(stats.arrecadacao_tributaria.divida_ativa)}</p></div>
            </div>
          ) : <p className="notice">Carregando indicadores...</p>}
          <div className="card" style={{ marginTop: 12 }}>
            <h2>Como navegar</h2>
            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
              <li><strong>Empenhos</strong> — consulte empenhos de despesas com filtro e exportação CSV.</li>
              <li><strong>Contratos</strong> — todos os contratos firmados com fornecedores.</li>
              <li><strong>Licitações</strong> — processos licitatórios e respectivos status.</li>
              <li><strong>Convênios</strong> — convênios de repasse/recebimento e desembolsos.</li>
              <li><strong>Arrecadação</strong> — lançamentos tributários pagos (IPTU, ISS, ITBI, taxas).</li>
              <li><strong>Dívida Ativa</strong> — inscrições em dívida ativa municipal (sem dados pessoais).</li>
            </ul>
          </div>
        </section>
      )}

      {/* ── Empenhos ─────────────────────────────────────────────────────────── */}
      {tab === "empenhos" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <div className="toolbar">
            <input placeholder="Buscar descrição ou número" value={empSearch} onChange={(e) => { setEmpSearch(e.target.value); setEmpPage(1); }} style={{ flex: 1 }} />
            <button className="btn" onClick={() => { setEmpPage(1); loadEmpenhos(); }}>Buscar</button>
            <a className="btn" href={csvUrl("/public/commitments", { search: empSearch })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Número</th><th>Descrição</th><th>Valor</th><th>Status</th></tr></thead>
            <tbody>
              {(empenhos?.items || []).length > 0 ? empenhos!.items.map((r) => (
                <tr key={r.id}><td>{r.number}</td><td>{r.description}</td><td>{fmt(r.amount)}</td><td><span className={`chip ${r.status}`}>{r.status}</span></td></tr>
              )) : <tr><td colSpan={4} className="empty-state">Nenhum empenho encontrado.</td></tr>}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={empPage <= 1} onClick={() => setEmpPage((p) => p - 1)}>Anterior</button>
            <span>Pág {empenhos?.page || 1} · Total: {empenhos?.total || 0}</span>
            <button className="btn" disabled={(empenhos?.items?.length || 0) < 10} onClick={() => setEmpPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ── Contratos ────────────────────────────────────────────────────────── */}
      {tab === "contratos" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <div className="toolbar">
            <input placeholder="Número do contrato" value={ctSearch} onChange={(e) => setCtSearch(e.target.value)} style={{ flex: 1 }} />
            <select value={ctStatus} onChange={(e) => setCtStatus(e.target.value)}>
              <option value="">Todos os status</option>
              <option value="vigente">Vigente</option>
              <option value="encerrado">Encerrado</option>
              <option value="rescindido">Rescindido</option>
            </select>
            <button className="btn" onClick={() => { setCtPage(1); loadContratos(); }}>Filtrar</button>
            <a className="btn" href={csvUrl("/public/contracts", { search: ctSearch, status: ctStatus })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Número</th><th>Início</th><th>Fim</th><th>Valor</th><th>Status</th></tr></thead>
            <tbody>
              {(contratos?.items || []).length > 0 ? contratos!.items.map((r) => (
                <tr key={r.id}><td>{r.number}</td><td>{r.start_date}</td><td>{r.end_date}</td><td>{fmt(r.amount)}</td><td><span className={`chip ${r.status}`}>{r.status}</span></td></tr>
              )) : <tr><td colSpan={5} className="empty-state">Nenhum contrato encontrado.</td></tr>}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={ctPage <= 1} onClick={() => setCtPage((p) => p - 1)}>Anterior</button>
            <span>Pág {contratos?.page || 1} · Total: {contratos?.total || 0}</span>
            <button className="btn" disabled={(contratos?.items?.length || 0) < 10} onClick={() => setCtPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ── Licitações ───────────────────────────────────────────────────────── */}
      {tab === "licitacoes" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <div className="toolbar">
            <input placeholder="Número ou objeto" value={lcSearch} onChange={(e) => setLcSearch(e.target.value)} style={{ flex: 1 }} />
            <select value={lcStatus} onChange={(e) => setLcStatus(e.target.value)}>
              <option value="">Todos os status</option>
              <option value="aberto">Aberto</option>
              <option value="homologado">Homologado</option>
              <option value="cancelado">Cancelado</option>
            </select>
            <button className="btn" onClick={() => { setLcPage(1); loadLicitacoes(); }}>Filtrar</button>
            <a className="btn" href={csvUrl("/public/licitacoes", { search: lcSearch, status: lcStatus })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Número</th><th>Objeto</th><th>Status</th></tr></thead>
            <tbody>
              {(licitacoes?.items || []).length > 0 ? licitacoes!.items.map((r) => (
                <tr key={r.id}><td>{r.number}</td><td>{r.object_description}</td><td><span className={`chip ${r.status}`}>{r.status}</span></td></tr>
              )) : <tr><td colSpan={3} className="empty-state">Nenhum processo encontrado.</td></tr>}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={lcPage <= 1} onClick={() => setLcPage((p) => p - 1)}>Anterior</button>
            <span>Pág {licitacoes?.page || 1} · Total: {licitacoes?.total || 0}</span>
            <button className="btn" disabled={(licitacoes?.items?.length || 0) < 10} onClick={() => setLcPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ── Convênios ────────────────────────────────────────────────────────── */}
      {tab === "convenios" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <div className="toolbar">
            <input placeholder="Número, objeto ou concedente" value={cvSearch} onChange={(e) => setCvSearch(e.target.value)} style={{ flex: 1 }} />
            <select value={cvTipo} onChange={(e) => setCvTipo(e.target.value)}>
              <option value="">Todos os tipos</option>
              <option value="recebimento">Recebimento</option>
              <option value="repasse">Repasse</option>
            </select>
            <button className="btn" onClick={() => { setCvPage(1); loadConvenios(); }}>Filtrar</button>
            <a className="btn" href={csvUrl("/public/convenios", { search: cvSearch, tipo: cvTipo })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Número</th><th>Objeto</th><th>Concedente</th><th>Tipo</th><th>Valor total</th><th>Assinatura</th><th>Status</th></tr></thead>
            <tbody>
              {(convenios?.items || []).length > 0 ? convenios!.items.map((r) => (
                <tr key={r.id}>
                  <td>{r.numero}</td>
                  <td>{r.objeto}</td>
                  <td>{r.concedente}</td>
                  <td>{r.tipo}</td>
                  <td>{fmt(r.valor_total)}</td>
                  <td>{r.data_assinatura}</td>
                  <td><span className={`chip ${r.status}`}>{r.status}</span></td>
                </tr>
              )) : <tr><td colSpan={7} className="empty-state">Nenhum convênio publicado encontrado.</td></tr>}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={cvPage <= 1} onClick={() => setCvPage((p) => p - 1)}>Anterior</button>
            <span>Pág {convenios?.page || 1} · Total: {convenios?.total || 0}</span>
            <button className="btn" disabled={(convenios?.items?.length || 0) < 10} onClick={() => setCvPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ── Arrecadação Tributária ────────────────────────────────────────────── */}
      {tab === "arrecadacao" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <div className="toolbar">
            <select value={arTributo} onChange={(e) => setArTributo(e.target.value)}>
              <option value="">Todos os tributos</option>
              {["IPTU","ISS","ITBI","TAXA_LIXO","TAXA_ILUMINACAO","TAXA_OBRAS"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <button className="btn" onClick={() => { setArPage(1); loadArrecadacao(); }}>Filtrar</button>
            <a className="btn" href={csvUrl("/public/arrecadacao", { tributo: arTributo })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Tributo</th><th>Competência</th><th>Exercício</th><th>Valor</th><th>Data pagamento</th></tr></thead>
          <tbody>
            {(arrecadacao?.items || []).length > 0 ? arrecadacao!.items.map((r) => (
              <tr key={r.id}>
                <td>{r.tributo}</td>
                <td>{r.competencia}</td>
                <td>{r.exercicio}</td>
                <td>{fmt(r.valor_total)}</td>
                <td>{r.data_pagamento}</td>
              </tr>
            )) : <tr><td colSpan={5} className="empty-state">Nenhum registro de arrecadação encontrado.</td></tr>}
          </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={arPage <= 1} onClick={() => setArPage((p) => p - 1)}>Anterior</button>
            <span>Pág {arrecadacao?.page || 1} · Total: {arrecadacao?.total || 0}</span>
            <button className="btn" disabled={(arrecadacao?.items?.length || 0) < 10} onClick={() => setArPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}

      {/* ── Dívida Ativa ─────────────────────────────────────────────────────── */}
      {tab === "divida" && (
        <section className="section-stack" style={{ marginTop: 12 }}>
          <p className="muted">Inscrições ativas ou ajuizadas — dados de identificação pessoal não são exibidos publicamente.</p>
          <div className="toolbar">
            <select value={dvTributo} onChange={(e) => setDvTributo(e.target.value)}>
              <option value="">Todos os tributos</option>
              {["IPTU","ISS","ITBI","TAXA_LIXO","TAXA_ILUMINACAO","TAXA_OBRAS"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <button className="btn" onClick={() => { setDvPage(1); loadDividas(); }}>Filtrar</button>
            <a className="btn" href={csvUrl("/public/divida-ativa", { tributo: dvTributo })} target="_blank" rel="noreferrer">Exportar CSV</a>
          </div>
          <table>
            <thead><tr><th>Inscrição</th><th>Tributo</th><th>Exercício</th><th>Valor original</th><th>Valor atualizado</th><th>Data inscrição</th><th>Status</th></tr></thead>
          <tbody>
            {(dividas?.items || []).length > 0 ? dividas!.items.map((r, i) => (
              <tr key={i}>
                <td>{r.numero_inscricao}</td>
                <td>{r.tributo}</td>
                <td>{r.exercicio}</td>
                <td>{fmt(r.valor_original)}</td>
                <td>{fmt(r.valor_atualizado)}</td>
                <td>{r.data_inscricao}</td>
                <td><span className="chip pendente">{r.status}</span></td>
              </tr>
            )) : <tr><td colSpan={7} className="empty-state">Nenhuma inscrição ativa encontrada.</td></tr>}
          </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={dvPage <= 1} onClick={() => setDvPage((p) => p - 1)}>Anterior</button>
            <span>Pág {dividas?.page || 1} · Total: {dividas?.total || 0}</span>
            <button className="btn" disabled={(dividas?.items?.length || 0) < 10} onClick={() => setDvPage((p) => p + 1)}>Próxima</button>
          </div>
        </section>
      )}
    </main>
  );
}

