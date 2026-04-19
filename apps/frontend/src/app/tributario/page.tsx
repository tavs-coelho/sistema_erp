"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };
type Contribuinte = { id: number; cpf_cnpj: string; nome: string; tipo: string; municipio: string; uf: string; ativo: boolean };
type Imovel = { id: number; inscricao: string; contribuinte_id: number; logradouro: string; numero: string; bairro: string; valor_venal: number; uso: string; ativo: boolean };
type Lancamento = { id: number; contribuinte_id: number; imovel_id: number | null; tributo: string; competencia: string; exercicio: number; valor_total: number; vencimento: string; status: string };
type Guia = { id: number; lancamento_id: number; codigo_barras: string; valor: number; vencimento: string; status: string; data_pagamento: string | null };
type DividaAtiva = { id: number; numero_inscricao: string; tributo: string; exercicio: number; valor_original: number; valor_atualizado: number; data_inscricao: string; status: string };
type Dashboard = {
  total_contribuintes_ativos: number; total_imoveis_ativos: number;
  lancamentos_por_status: Record<string, number>;
  valor_aberto: number; valor_arrecadado: number; valor_divida_ativa: number;
  lancamentos_vencidos_abertos: number;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const TRIBUTOS = ["IPTU", "ISS", "ITBI", "TAXA_LIXO", "TAXA_ILUMINACAO", "TAXA_OBRAS"];
const USOS = ["residencial", "comercial", "industrial", "rural"];
const STATUS_LANC = ["", "aberto", "pago", "cancelado", "inscrito_divida"];
const STATUS_DA = ["ativa", "quitada", "parcelada", "ajuizada", "prescrita"];

function messageFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

function fmt(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

const CHIP_LANC: Record<string, string> = { aberto: "pendente", pago: "pago", cancelado: "baixado", inscrito_divida: "empenhado" };
const CHIP_DA: Record<string, string> = { ativa: "pendente", quitada: "pago", ajuizada: "baixado", parcelada: "empenhado", prescrita: "baixado" };
const CHIP_GUIA: Record<string, string> = { emitida: "empenhado", paga: "pago", cancelada: "baixado", vencida: "pendente" };

// ── Component ─────────────────────────────────────────────────────────────────

export default function TributarioPage() {
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");
  const [tab, setTab] = useState<"dashboard" | "contribuintes" | "imoveis" | "lancamentos" | "guias" | "divida">("dashboard");

  // Dashboard
  const [dash, setDash] = useState<Dashboard | null>(null);

  // Contribuintes
  const [contribuintes, setContribuintes] = useState<Paged<Contribuinte> | null>(null);
  const [cSearch, setCSearch] = useState("");
  const [cPage, setCPage] = useState(1);
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [cNome, setCNome] = useState("");
  const [cTipo, setCTipo] = useState("PF");
  const [cMunicipio, setCMunicipio] = useState("");
  const [cUf, setCUf] = useState("");

  // Imóveis
  const [imoveis, setImoveis] = useState<Paged<Imovel> | null>(null);
  const [iPage, setIPage] = useState(1);
  const [iContribId, setIContribId] = useState<number | "">("");
  const [iInscricao, setIInscricao] = useState("");
  const [iLogradouro, setILogradouro] = useState("");
  const [iNumero, setINumero] = useState("");
  const [iBairro, setIBairro] = useState("");
  const [iAreaT, setIAreaT] = useState(0);
  const [iAreaC, setIAreaC] = useState(0);
  const [iValorV, setIValorV] = useState(0);
  const [iUso, setIUso] = useState("residencial");

  // Lançamentos
  const [lancamentos, setLancamentos] = useState<Paged<Lancamento> | null>(null);
  const [lPage, setLPage] = useState(1);
  const [lStatusFilter, setLStatusFilter] = useState("");
  const [lTributoFilter, setLTributoFilter] = useState("");
  const [lContribId, setLContribId] = useState<number | "">("");
  const [lImovelId, setLImovelId] = useState<number | "">("");
  const [lTributo, setLTributo] = useState("IPTU");
  const [lCompetencia, setLCompetencia] = useState("2026-01");
  const [lExercicio, setLExercicio] = useState(2026);
  const [lPrincipal, setLPrincipal] = useState(0);
  const [lJuros, setLJuros] = useState(0);
  const [lMulta, setLMulta] = useState(0);
  const [lDesconto, setLDesconto] = useState(0);
  const [lVencimento, setLVencimento] = useState("2026-03-31");

  // Guias
  const [guias, setGuias] = useState<Paged<Guia> | null>(null);
  const [gPage, setGPage] = useState(1);
  const [gLancamentoId, setGLancamentoId] = useState<number | "">("");
  const [gBaixaId, setGBaixaId] = useState<number | "">("");
  const [gDataPagamento, setGDataPagamento] = useState("");
  const [gBanco, setGBanco] = useState("");

  // Dívida Ativa
  const [dividas, setDividas] = useState<Paged<DividaAtiva> | null>(null);
  const [daPage, setDaPage] = useState(1);
  const [daStatusFilter, setDaStatusFilter] = useState("");
  const [daLancId, setDaLancId] = useState<number | "">("");
  const [daNumeroInsc, setDaNumeroInsc] = useState("");
  const [daDataInsc, setDaDataInsc] = useState("2026-04-01");
  const [daValorAt, setDaValorAt] = useState(0);

  // Loaders
  const loadDash = async () => { try { setDash(await authJson("/tributario/dashboard")); } catch (e) { setMsg(messageFrom(e)); } };
  const loadContribuintes = async () => {
    const qs = new URLSearchParams({ page: String(cPage), size: "8" });
    if (cSearch) qs.set("search", cSearch);
    setContribuintes(await authJson(`/tributario/contribuintes?${qs}`));
  };
  const loadImoveis = async () => {
    const qs = new URLSearchParams({ page: String(iPage), size: "8" });
    if (iContribId) qs.set("contribuinte_id", String(iContribId));
    setImoveis(await authJson(`/tributario/imoveis?${qs}`));
  };
  const loadLancamentos = async () => {
    const qs = new URLSearchParams({ page: String(lPage), size: "8" });
    if (lStatusFilter) qs.set("status", lStatusFilter);
    if (lTributoFilter) qs.set("tributo", lTributoFilter);
    if (lContribId) qs.set("contribuinte_id", String(lContribId));
    setLancamentos(await authJson(`/tributario/lancamentos?${qs}`));
  };
  const loadGuias = async () => {
    const qs = new URLSearchParams({ page: String(gPage), size: "8" });
    if (gLancamentoId) qs.set("lancamento_id", String(gLancamentoId));
    setGuias(await authJson(`/tributario/guias?${qs}`));
  };
  const loadDividas = async () => {
    const qs = new URLSearchParams({ page: String(daPage), size: "8" });
    if (daStatusFilter) qs.set("status", daStatusFilter);
    setDividas(await authJson(`/tributario/divida-ativa?${qs}`));
  };

  useEffect(() => {
    const t = setTimeout(() => {
      Promise.all([loadDash(), loadContribuintes(), loadLancamentos(), loadGuias(), loadDividas()]).catch((e) =>
        setMsg(messageFrom(e))
      );
    }, 0);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = setTimeout(() => { loadContribuintes().catch(() => {}); }, 0);
    return () => clearTimeout(t);
  }, [cPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t = setTimeout(() => { loadImoveis().catch(() => {}); }, 0);
    return () => clearTimeout(t);
  }, [iPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t = setTimeout(() => { loadLancamentos().catch(() => {}); }, 0);
    return () => clearTimeout(t);
  }, [lPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t = setTimeout(() => { loadGuias().catch(() => {}); }, 0);
    return () => clearTimeout(t);
  }, [gPage]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t = setTimeout(() => { loadDividas().catch(() => {}); }, 0);
    return () => clearTimeout(t);
  }, [daPage]); // eslint-disable-line react-hooks/exhaustive-deps

  // Submits
  const submitContribuinte = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/tributario/contribuintes", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf_cnpj: cpfCnpj, nome: cNome, tipo: cTipo, municipio: cMunicipio, uf: cUf }),
      });
      setMsg(`Contribuinte ${cNome} cadastrado.`);
      setCpfCnpj(""); setCNome(""); setCMunicipio(""); setCUf("");
      await loadContribuintes(); await loadDash();
      setTab("contribuintes");
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const submitImovel = async (e: FormEvent) => {
    e.preventDefault();
    if (!iContribId) return setMsg("Informe o ID do contribuinte.");
    try {
      await authJson("/tributario/imoveis", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inscricao: iInscricao, contribuinte_id: iContribId, logradouro: iLogradouro, numero: iNumero, bairro: iBairro, area_terreno: iAreaT, area_construida: iAreaC, valor_venal: iValorV, uso: iUso }),
      });
      setMsg(`Imóvel ${iInscricao} cadastrado.`);
      setIInscricao(""); setILogradouro(""); setINumero(""); setIBairro(""); setIAreaT(0); setIAreaC(0); setIValorV(0);
      await loadImoveis(); await loadDash();
      setTab("imoveis");
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const submitLancamento = async (e: FormEvent) => {
    e.preventDefault();
    if (!lContribId) return setMsg("Informe o ID do contribuinte.");
    try {
      await authJson("/tributario/lancamentos", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contribuinte_id: lContribId, imovel_id: lImovelId || null,
          tributo: lTributo, competencia: lCompetencia, exercicio: lExercicio,
          valor_principal: lPrincipal, valor_juros: lJuros, valor_multa: lMulta, valor_desconto: lDesconto,
          vencimento: lVencimento,
        }),
      });
      setMsg(`Lançamento ${lTributo} registrado.`);
      setLPrincipal(0); setLJuros(0); setLMulta(0); setLDesconto(0);
      await loadLancamentos(); await loadDash();
      setTab("lancamentos");
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const emitirGuia = async (lancId: number) => {
    try {
      const guia = await authJson(`/tributario/lancamentos/${lancId}/emitir-guia`, { method: "POST" });
      setMsg(`Guia emitida: ${guia.codigo_barras}`);
      await loadGuias(); await loadLancamentos();
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const baixarGuia = async (e: FormEvent) => {
    e.preventDefault();
    if (!gBaixaId) return setMsg("Selecione a guia.");
    try {
      const qs = new URLSearchParams({ data_pagamento: gDataPagamento || new Date().toISOString().slice(0, 10) });
      if (gBanco) qs.set("banco", gBanco);
      await authJson(`/tributario/guias/${gBaixaId}/baixar?${qs}`, { method: "POST" });
      setMsg("Pagamento registrado.");
      setGBaixaId(""); setGDataPagamento(""); setGBanco("");
      await loadGuias(); await loadLancamentos(); await loadDash();
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const inscreverDivida = async (e: FormEvent) => {
    e.preventDefault();
    if (!daLancId) return setMsg("Informe o ID do lançamento.");
    try {
      await authJson("/tributario/divida-ativa", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lancamento_id: daLancId, numero_inscricao: daNumeroInsc, data_inscricao: daDataInsc, valor_atualizado: daValorAt }),
      });
      setMsg(`Inscrição ${daNumeroInsc} realizada em dívida ativa.`);
      setDaLancId(""); setDaNumeroInsc(""); setDaValorAt(0);
      await loadDividas(); await loadLancamentos(); await loadDash();
    } catch (er) { setMsg(messageFrom(er)); }
  };

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "contribuintes", label: "Contribuintes" },
    { key: "imoveis", label: "Imóveis" },
    { key: "lancamentos", label: "Lançamentos" },
    { key: "guias", label: "Guias" },
    { key: "divida", label: "Dívida Ativa" },
  ] as const;

  return (
    <main className="module-page" style={{ padding: 16 }}>
      <h1>Módulo Tributário / Arrecadação Municipal</h1>
      <p className="muted">Gestão de contribuintes, cadastro imobiliário, lançamentos (IPTU/ISS/ITBI), guias e dívida ativa.</p>

      {msg && <p className={isError ? "notice error" : "notice"}><strong>{msg}</strong></p>}

      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/protocolo">Protocolo</Link>
        <Link className="btn" href="/convenios">Convênios</Link>
      </div>

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

      {/* ─── Dashboard ─────────────────────────────────────────────────────── */}
      {tab === "dashboard" && dash && (
        <section className="section-stack">
          <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, marginTop: 12 }}>
            <div className="card kpi-card"><p className="muted">Contribuintes ativos</p><p className="kpi-value">{dash.total_contribuintes_ativos}</p></div>
            <div className="card kpi-card"><p className="muted">Imóveis cadastrados</p><p className="kpi-value">{dash.total_imoveis_ativos}</p></div>
            <div className="card kpi-card"><p className="muted">Valor em aberto</p><p className="kpi-value">{fmt(dash.valor_aberto)}</p></div>
            <div className="card kpi-card"><p className="muted">Arrecadado (pago)</p><p className="kpi-value">{fmt(dash.valor_arrecadado)}</p></div>
            <div className="card kpi-card"><p className="muted">Dívida ativa</p><p className="kpi-value">{fmt(dash.valor_divida_ativa)}</p></div>
            <div className="card kpi-card" style={{ borderLeft: dash.lancamentos_vencidos_abertos > 0 ? "4px solid #e53e3e" : undefined }}>
              <p className="muted">Vencidos em aberto</p>
              <p className="kpi-value" style={{ color: dash.lancamentos_vencidos_abertos > 0 ? "#e53e3e" : undefined }}>{dash.lancamentos_vencidos_abertos}</p>
            </div>
          </div>
          <div className="card" style={{ marginTop: 12 }}>
            <h2>Lançamentos por status</h2>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
              {Object.entries(dash.lancamentos_por_status).map(([s, c]) => (
                <div key={s} style={{ textAlign: "center", minWidth: 100 }}>
                  <span className={`chip ${CHIP_LANC[s] || "empenhado"}`}>{s.replace("_", " ")}</span>
                  <p style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{c}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─── Contribuintes ──────────────────────────────────────────────────── */}
      {tab === "contribuintes" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
          {/* Formulário */}
          <section className="card">
            <h2>Cadastrar contribuinte</h2>
            <form onSubmit={submitContribuinte} className="section-stack">
              <label className="field-group">CPF / CNPJ<input value={cpfCnpj} onChange={(e) => setCpfCnpj(e.target.value)} required /></label>
              <label className="field-group">Nome / Razão social<input value={cNome} onChange={(e) => setCNome(e.target.value)} required /></label>
              <label className="field-group">
                Tipo
                <select value={cTipo} onChange={(e) => setCTipo(e.target.value)}>
                  <option value="PF">Pessoa Física</option>
                  <option value="PJ">Pessoa Jurídica</option>
                </select>
              </label>
              <label className="field-group">Município<input value={cMunicipio} onChange={(e) => setCMunicipio(e.target.value)} /></label>
              <label className="field-group">UF<input value={cUf} maxLength={2} onChange={(e) => setCUf(e.target.value)} style={{ width: 60 }} /></label>
              <button className="btn btn-primary" type="submit">Cadastrar</button>
            </form>
          </section>

          {/* Lista */}
          <section className="card section-stack">
            <div className="toolbar">
              <input value={cSearch} onChange={(e) => setCSearch(e.target.value)} placeholder="Buscar nome ou CPF/CNPJ" style={{ flex: 1 }} />
              <button className="btn" onClick={() => { setCPage(1); loadContribuintes().catch(() => {}); }}>Buscar</button>
            </div>
            <table>
              <thead><tr><th>ID</th><th>CPF/CNPJ</th><th>Nome</th><th>Tipo</th><th>Município/UF</th><th>Ativo</th></tr></thead>
              <tbody>
                {(contribuintes?.items || []).length > 0 ? contribuintes!.items.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.cpf_cnpj}</td>
                    <td>{c.nome}</td>
                    <td>{c.tipo}</td>
                    <td>{c.municipio}/{c.uf}</td>
                    <td>{c.ativo ? "✓" : "—"}</td>
                  </tr>
                )) : <tr><td colSpan={6} className="empty-state">Nenhum contribuinte.</td></tr>}
              </tbody>
            </table>
            <div className="pagination">
              <button className="btn" disabled={cPage <= 1} onClick={() => setCPage((p) => p - 1)}>Anterior</button>
              <span>Pág {contribuintes?.page || 1} · Total: {contribuintes?.total || 0}</span>
              <button className="btn" disabled={(contribuintes?.items?.length || 0) < 8} onClick={() => setCPage((p) => p + 1)}>Próxima</button>
            </div>
          </section>
        </div>
      )}

      {/* ─── Imóveis ──────────────────────────────────────────────────────── */}
      {tab === "imoveis" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
          <section className="card">
            <h2>Cadastrar imóvel</h2>
            <form onSubmit={submitImovel} style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
              <label className="field-group">ID do Contribuinte<input type="number" value={iContribId} onChange={(e) => setIContribId(e.target.value ? Number(e.target.value) : "")} required /></label>
              <label className="field-group">Inscrição cadastral<input value={iInscricao} onChange={(e) => setIInscricao(e.target.value)} required /></label>
              <label className="field-group">Logradouro<input value={iLogradouro} onChange={(e) => setILogradouro(e.target.value)} required /></label>
              <label className="field-group">Número<input value={iNumero} onChange={(e) => setINumero(e.target.value)} /></label>
              <label className="field-group">Bairro<input value={iBairro} onChange={(e) => setIBairro(e.target.value)} /></label>
              <label className="field-group">
                Uso
                <select value={iUso} onChange={(e) => setIUso(e.target.value)}>
                  {USOS.map((u) => <option key={u}>{u}</option>)}
                </select>
              </label>
              <label className="field-group">Área terreno (m²)<input type="number" value={iAreaT} onChange={(e) => setIAreaT(Number(e.target.value))} /></label>
              <label className="field-group">Área construída (m²)<input type="number" value={iAreaC} onChange={(e) => setIAreaC(Number(e.target.value))} /></label>
              <label className="field-group">Valor venal (R$)<input type="number" value={iValorV} onChange={(e) => setIValorV(Number(e.target.value))} /></label>
              <div style={{ gridColumn: "1 / -1" }}>
                <button className="btn btn-primary" type="submit">Cadastrar imóvel</button>
              </div>
            </form>
          </section>

          <section className="card section-stack">
            <div className="toolbar">
              <input type="number" value={iContribId} onChange={(e) => setIContribId(e.target.value ? Number(e.target.value) : "")} placeholder="Filtrar por ID do contribuinte" style={{ flex: 1 }} />
              <button className="btn" onClick={() => { setIPage(1); loadImoveis().catch(() => {}); }}>Filtrar</button>
            </div>
            <table>
              <thead><tr><th>Inscrição</th><th>Logradouro</th><th>Bairro</th><th>Uso</th><th>Valor venal</th></tr></thead>
              <tbody>
                {(imoveis?.items || []).length > 0 ? imoveis!.items.map((i) => (
                  <tr key={i.id}>
                    <td>{i.inscricao}</td>
                    <td>{i.logradouro}, {i.numero}</td>
                    <td>{i.bairro}</td>
                    <td>{i.uso}</td>
                    <td>{fmt(i.valor_venal)}</td>
                  </tr>
                )) : <tr><td colSpan={5} className="empty-state">Nenhum imóvel encontrado. Filtre por contribuinte ou cadastre um acima.</td></tr>}
              </tbody>
            </table>
            <div className="pagination">
              <button className="btn" disabled={iPage <= 1} onClick={() => setIPage((p) => p - 1)}>Anterior</button>
              <span>Pág {imoveis?.page || 1} · Total: {imoveis?.total || 0}</span>
              <button className="btn" disabled={(imoveis?.items?.length || 0) < 8} onClick={() => setIPage((p) => p + 1)}>Próxima</button>
            </div>
          </section>
        </div>
      )}

      {/* ─── Lançamentos ──────────────────────────────────────────────────── */}
      {tab === "lancamentos" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
          <section className="card">
            <h2>Novo lançamento tributário</h2>
            <form onSubmit={submitLancamento} style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
              <label className="field-group">ID Contribuinte<input type="number" value={lContribId} onChange={(e) => setLContribId(e.target.value ? Number(e.target.value) : "")} required /></label>
              <label className="field-group">ID Imóvel (opcional)<input type="number" value={lImovelId} onChange={(e) => setLImovelId(e.target.value ? Number(e.target.value) : "")} /></label>
              <label className="field-group">
                Tributo
                <select value={lTributo} onChange={(e) => setLTributo(e.target.value)}>
                  {TRIBUTOS.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label className="field-group">Competência (AAAA-MM)<input value={lCompetencia} onChange={(e) => setLCompetencia(e.target.value)} required /></label>
              <label className="field-group">Exercício<input type="number" value={lExercicio} onChange={(e) => setLExercicio(Number(e.target.value))} required /></label>
              <label className="field-group">Valor principal<input type="number" step="0.01" value={lPrincipal} onChange={(e) => setLPrincipal(Number(e.target.value))} required /></label>
              <label className="field-group">Juros<input type="number" step="0.01" value={lJuros} onChange={(e) => setLJuros(Number(e.target.value))} /></label>
              <label className="field-group">Multa<input type="number" step="0.01" value={lMulta} onChange={(e) => setLMulta(Number(e.target.value))} /></label>
              <label className="field-group">Desconto<input type="number" step="0.01" value={lDesconto} onChange={(e) => setLDesconto(Number(e.target.value))} /></label>
              <label className="field-group">Vencimento<input type="date" value={lVencimento} onChange={(e) => setLVencimento(e.target.value)} required /></label>
              <div style={{ gridColumn: "1 / -1" }}>
                <p style={{ fontSize: 13, color: "#555", marginBottom: 6 }}>
                  Total estimado: {fmt(Math.max(0, lPrincipal + lJuros + lMulta - lDesconto))}
                </p>
                <button className="btn btn-primary" type="submit">Lançar tributo</button>
              </div>
            </form>
          </section>

          <section className="card section-stack">
            <div className="toolbar">
              <select value={lStatusFilter} onChange={(e) => setLStatusFilter(e.target.value)}>
                {STATUS_LANC.map((s) => <option key={s} value={s}>{s || "Todos os status"}</option>)}
              </select>
              <select value={lTributoFilter} onChange={(e) => setLTributoFilter(e.target.value)}>
                <option value="">Todos os tributos</option>
                {TRIBUTOS.map((t) => <option key={t}>{t}</option>)}
              </select>
              <button className="btn" onClick={() => { setLPage(1); loadLancamentos().catch(() => {}); }}>Filtrar</button>
            </div>
            <table>
              <thead><tr><th>ID</th><th>Tributo</th><th>Competência</th><th>Valor total</th><th>Vencimento</th><th>Status</th><th>Guia</th></tr></thead>
              <tbody>
                {(lancamentos?.items || []).length > 0 ? lancamentos!.items.map((l) => (
                  <tr key={l.id}>
                    <td>{l.id}</td>
                    <td>{l.tributo}</td>
                    <td>{l.competencia}</td>
                    <td>{fmt(l.valor_total)}</td>
                    <td>{l.vencimento}</td>
                    <td><span className={`chip ${CHIP_LANC[l.status] || "empenhado"}`}>{l.status}</span></td>
                    <td>
                      {l.status === "aberto" && (
                        <button className="btn" style={{ padding: "2px 8px", fontSize: 12 }} onClick={() => emitirGuia(l.id)}>Emitir</button>
                      )}
                    </td>
                  </tr>
                )) : <tr><td colSpan={7} className="empty-state">Nenhum lançamento.</td></tr>}
              </tbody>
            </table>
            <div className="pagination">
              <button className="btn" disabled={lPage <= 1} onClick={() => setLPage((p) => p - 1)}>Anterior</button>
              <span>Pág {lancamentos?.page || 1} · Total: {lancamentos?.total || 0}</span>
              <button className="btn" disabled={(lancamentos?.items?.length || 0) < 8} onClick={() => setLPage((p) => p + 1)}>Próxima</button>
            </div>
          </section>
        </div>
      )}

      {/* ─── Guias ────────────────────────────────────────────────────────── */}
      {tab === "guias" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
          <section className="card">
            <h2>Baixar guia (registrar pagamento)</h2>
            <form onSubmit={baixarGuia} className="section-stack">
              <label className="field-group">
                Guia
                <select value={gBaixaId} onChange={(e) => setGBaixaId(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">Selecione a guia emitida</option>
                  {(guias?.items || []).filter((g) => g.status === "emitida").map((g) => (
                    <option key={g.id} value={g.id}>#{g.id} — {g.codigo_barras.slice(0, 35)}… — {fmt(g.valor)} — vence {g.vencimento}</option>
                  ))}
                </select>
              </label>
              <label className="field-group">Data do pagamento<input type="date" value={gDataPagamento} onChange={(e) => setGDataPagamento(e.target.value)} /></label>
              <label className="field-group">Banco (opcional)<input value={gBanco} onChange={(e) => setGBanco(e.target.value)} /></label>
              <button className="btn btn-primary" type="submit">Confirmar pagamento</button>
            </form>
          </section>

          <section className="card section-stack">
            <div className="toolbar">
              <input type="number" value={gLancamentoId} onChange={(e) => setGLancamentoId(e.target.value ? Number(e.target.value) : "")} placeholder="Filtrar por ID do lançamento" style={{ flex: 1 }} />
              <button className="btn" onClick={() => { setGPage(1); loadGuias().catch(() => {}); }}>Filtrar</button>
            </div>
            <table>
              <thead><tr><th>ID</th><th>Código de barras</th><th>Valor</th><th>Vencimento</th><th>Status</th><th>Pagamento</th></tr></thead>
            <tbody>
              {(guias?.items || []).length > 0 ? guias!.items.map((g) => (
                <tr key={g.id}>
                  <td>{g.id}</td>
                  <td style={{ fontSize: 11, maxWidth: 200, wordBreak: "break-all" }}>{g.codigo_barras}</td>
                  <td>{fmt(g.valor)}</td>
                  <td>{g.vencimento}</td>
                  <td><span className={`chip ${CHIP_GUIA[g.status] || "empenhado"}`}>{g.status}</span></td>
                  <td>{g.data_pagamento || "—"}</td>
                </tr>
              )) : <tr><td colSpan={6} className="empty-state">Nenhuma guia.</td></tr>}
            </tbody>
            </table>
            <div className="pagination">
              <button className="btn" disabled={gPage <= 1} onClick={() => setGPage((p) => p - 1)}>Anterior</button>
              <span>Pág {guias?.page || 1} · Total: {guias?.total || 0}</span>
              <button className="btn" disabled={(guias?.items?.length || 0) < 8} onClick={() => setGPage((p) => p + 1)}>Próxima</button>
            </div>
          </section>
        </div>
      )}

      {/* ─── Dívida Ativa ─────────────────────────────────────────────────── */}
      {tab === "divida" && (
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
          <section className="card">
            <h2>Inscrever em dívida ativa</h2>
            <form onSubmit={inscreverDivida} className="section-stack">
              <label className="field-group">ID do Lançamento<input type="number" value={daLancId} onChange={(e) => setDaLancId(e.target.value ? Number(e.target.value) : "")} required /></label>
              <label className="field-group">Número de inscrição<input value={daNumeroInsc} onChange={(e) => setDaNumeroInsc(e.target.value)} required /></label>
              <label className="field-group">Data de inscrição<input type="date" value={daDataInsc} onChange={(e) => setDaDataInsc(e.target.value)} required /></label>
              <label className="field-group">Valor atualizado (R$)<input type="number" step="0.01" value={daValorAt} onChange={(e) => setDaValorAt(Number(e.target.value))} required /></label>
              <button className="btn btn-primary" type="submit">Inscrever</button>
            </form>
          </section>

          <section className="card section-stack">
            <div className="toolbar">
              <select value={daStatusFilter} onChange={(e) => setDaStatusFilter(e.target.value)}>
                <option value="">Todos os status</option>
                {STATUS_DA.map((s) => <option key={s}>{s}</option>)}
              </select>
              <button className="btn" onClick={() => { setDaPage(1); loadDividas().catch(() => {}); }}>Filtrar</button>
            </div>
            <table>
              <thead><tr><th>Inscrição</th><th>Tributo</th><th>Exercício</th><th>Valor original</th><th>Valor atualizado</th><th>Inscrição</th><th>Status</th></tr></thead>
            <tbody>
              {(dividas?.items || []).length > 0 ? dividas!.items.map((d) => (
                <tr key={d.id}>
                  <td>{d.numero_inscricao}</td>
                  <td>{d.tributo}</td>
                  <td>{d.exercicio}</td>
                  <td>{fmt(d.valor_original)}</td>
                  <td>{fmt(d.valor_atualizado)}</td>
                  <td>{d.data_inscricao}</td>
                  <td><span className={`chip ${CHIP_DA[d.status] || "empenhado"}`}>{d.status}</span></td>
                </tr>
              )) : <tr><td colSpan={7} className="empty-state">Nenhuma inscrição em dívida ativa.</td></tr>}
            </tbody>
            </table>
            <div className="pagination">
              <button className="btn" disabled={daPage <= 1} onClick={() => setDaPage((p) => p - 1)}>Anterior</button>
              <span>Pág {dividas?.page || 1} · Total: {dividas?.total || 0}</span>
              <button className="btn" disabled={(dividas?.items?.length || 0) < 8} onClick={() => setDaPage((p) => p + 1)}>Próxima</button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
