"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
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
  const { toast } = useToast();
  const [tab, setTab] = useState<"dashboard" | "contribuintes" | "imoveis" | "lancamentos" | "guias" | "divida" | "aliquotas" | "parcelamentos" | "relatorio">("dashboard");

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
  const loadDash = async () => { try { setDash(await authJson("/tributario/dashboard")); } catch (e) { toast(messageFrom(e), "error"); } };
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
        toast(messageFrom(e), "error")
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
      toast(`Contribuinte ${cNome} cadastrado.`);
      setCpfCnpj(""); setCNome(""); setCMunicipio(""); setCUf("");
      await loadContribuintes(); await loadDash();
      setTab("contribuintes");
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const submitImovel = async (e: FormEvent) => {
    e.preventDefault();
    if (!iContribId) { toast("Informe o ID do contribuinte.", "error"); return; }
    try {
      await authJson("/tributario/imoveis", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inscricao: iInscricao, contribuinte_id: iContribId, logradouro: iLogradouro, numero: iNumero, bairro: iBairro, area_terreno: iAreaT, area_construida: iAreaC, valor_venal: iValorV, uso: iUso }),
      });
      toast(`Imóvel ${iInscricao} cadastrado.`);
      setIInscricao(""); setILogradouro(""); setINumero(""); setIBairro(""); setIAreaT(0); setIAreaC(0); setIValorV(0);
      await loadImoveis(); await loadDash();
      setTab("imoveis");
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const submitLancamento = async (e: FormEvent) => {
    e.preventDefault();
    if (!lContribId) { toast("Informe o ID do contribuinte.", "error"); return; }
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
      toast(`Lançamento ${lTributo} registrado.`);
      setLPrincipal(0); setLJuros(0); setLMulta(0); setLDesconto(0);
      await loadLancamentos(); await loadDash();
      setTab("lancamentos");
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const emitirGuia = async (lancId: number) => {
    try {
      const guia = await authJson(`/tributario/lancamentos/${lancId}/emitir-guia`, { method: "POST" });
      toast(`Guia emitida: ${guia.codigo_barras}`);
      await loadGuias(); await loadLancamentos();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const baixarGuia = async (e: FormEvent) => {
    e.preventDefault();
    if (!gBaixaId) { toast("Selecione a guia.", "error"); return; }
    try {
      const qs = new URLSearchParams({ data_pagamento: gDataPagamento || new Date().toISOString().slice(0, 10) });
      if (gBanco) qs.set("banco", gBanco);
      await authJson(`/tributario/guias/${gBaixaId}/baixar?${qs}`, { method: "POST" });
      toast("Pagamento registrado.");
      setGBaixaId(""); setGDataPagamento(""); setGBanco("");
      await loadGuias(); await loadLancamentos(); await loadDash();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const inscreverDivida = async (e: FormEvent) => {
    e.preventDefault();
    if (!daLancId) { toast("Informe o ID do lançamento.", "error"); return; }
    try {
      await authJson("/tributario/divida-ativa", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lancamento_id: daLancId, numero_inscricao: daNumeroInsc, data_inscricao: daDataInsc, valor_atualizado: daValorAt }),
      });
      toast(`Inscrição ${daNumeroInsc} realizada em dívida ativa.`);
      setDaLancId(""); setDaNumeroInsc(""); setDaValorAt(0);
      await loadDividas(); await loadLancamentos(); await loadDash();
    } catch (er) { toast(messageFrom(er), "error"); }
  };

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "contribuintes", label: "Contribuintes" },
    { key: "imoveis", label: "Imóveis" },
    { key: "lancamentos", label: "Lançamentos" },
    { key: "guias", label: "Guias" },
    { key: "divida", label: "Dívida Ativa" },
    { key: "aliquotas", label: "Alíquotas IPTU" },
    { key: "parcelamentos", label: "Parcelamentos" },
    { key: "relatorio", label: "Relatório Arrecadação" },
  ] as const;

  return (
    <main className="module-page">
      <h1>Módulo Tributário / Arrecadação Municipal</h1>
      <p className="muted">Gestão de contribuintes, cadastro imobiliário, lançamentos (IPTU/ISS/ITBI), guias e dívida ativa.</p>

      <div className="toolbar">
        <Link className="btn" href="/">Painel</Link>
        <Link className="btn" href="/protocolo">Protocolo</Link>
        <Link className="btn" href="/convenios">Convênios</Link>
      </div>

      {/* Tabs */}
      <div className="toolbar tab-strip-border">
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn${tab === t.key ? " active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── Dashboard ─────────────────────────────────────────────────────── */}
      {tab === "dashboard" && dash && (
        <section className="section-stack">
          <div className="kpi-grid section-top">
            <div className="card kpi-card"><p className="muted">Contribuintes ativos</p><p className="kpi-value">{dash.total_contribuintes_ativos}</p></div>
            <div className="card kpi-card"><p className="muted">Imóveis cadastrados</p><p className="kpi-value">{dash.total_imoveis_ativos}</p></div>
            <div className="card kpi-card"><p className="muted">Valor em aberto</p><p className="kpi-value">{fmt(dash.valor_aberto)}</p></div>
            <div className="card kpi-card"><p className="muted">Arrecadado (pago)</p><p className="kpi-value">{fmt(dash.valor_arrecadado)}</p></div>
            <div className="card kpi-card"><p className="muted">Dívida ativa</p><p className="kpi-value">{fmt(dash.valor_divida_ativa)}</p></div>
            <div className={`card kpi-card${dash.lancamentos_vencidos_abertos > 0 ? " kpi-danger" : ""}`}>
              <p className="muted">Vencidos em aberto</p>
              <p className={`kpi-value${dash.lancamentos_vencidos_abertos > 0 ? " kpi-value-danger" : ""}`}>{dash.lancamentos_vencidos_abertos}</p>
            </div>
          </div>
          <div className="card mt-2">
            <h2>Lançamentos por status</h2>
            <div className="stat-row">
              {Object.entries(dash.lancamentos_por_status).map(([s, c]) => (
                <div key={s} className="stat-item">
                  <span className={`chip ${CHIP_LANC[s] || "empenhado"}`}>{s.replace("_", " ")}</span>
                  <p className="stat-count">{c}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─── Contribuintes ──────────────────────────────────────────────────── */}
      {tab === "contribuintes" && (
        <div className="auto-grid-lg">
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
              <label className="field-group">UF<input value={cUf} maxLength={2} onChange={(e) => setCUf(e.target.value)} className="input-narrow-sm" /></label>
              <button className="btn btn-primary" type="submit">Cadastrar</button>
            </form>
          </section>

          {/* Lista */}
          <section className="card section-stack">
            <div className="toolbar">
              <input value={cSearch} onChange={(e) => setCSearch(e.target.value)} placeholder="Buscar nome ou CPF/CNPJ" className="flex-1" />
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
        <div className="auto-grid-lg">
          <section className="card">
            <h2>Cadastrar imóvel</h2>
            <form onSubmit={submitImovel} className="form-grid">
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
              <div className="grid-full">
                <button className="btn btn-primary" type="submit">Cadastrar imóvel</button>
              </div>
            </form>
          </section>

          <section className="card section-stack">
            <div className="toolbar">
              <input type="number" value={iContribId} onChange={(e) => setIContribId(e.target.value ? Number(e.target.value) : "")} placeholder="Filtrar por ID do contribuinte" className="flex-1" />
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
        <div className="auto-grid-lg">
          <section className="card">
            <h2>Novo lançamento tributário</h2>
            <form onSubmit={submitLancamento} className="form-grid">
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
              <div className="grid-full">
                <p className="text-hint">
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
                        <button className="btn-xs" onClick={() => emitirGuia(l.id)}>Emitir</button>
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
        <div className="auto-grid-lg">
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
              <input type="number" value={gLancamentoId} onChange={(e) => setGLancamentoId(e.target.value ? Number(e.target.value) : "")} placeholder="Filtrar por ID do lançamento" className="flex-1" />
              <button className="btn" onClick={() => { setGPage(1); loadGuias().catch(() => {}); }}>Filtrar</button>
            </div>
            <table>
              <thead><tr><th>ID</th><th>Código de barras</th><th>Valor</th><th>Vencimento</th><th>Status</th><th>Pagamento</th></tr></thead>
            <tbody>
              {(guias?.items || []).length > 0 ? guias!.items.map((g) => (
                <tr key={g.id}>
                  <td>{g.id}</td>
                  <td className="td-code">{g.codigo_barras}</td>
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
        <div className="auto-grid-lg">
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

      {/* ── Alíquotas IPTU ──────────────────────────────────────────────── */}
      {tab === "aliquotas" && <AliquotasTab />}

      {/* ── Parcelamentos ───────────────────────────────────────────────── */}
      {tab === "parcelamentos" && <ParcelamentosTab />}

      {/* ── Relatório de Arrecadação ─────────────────────────────────────── */}
      {tab === "relatorio" && <RelatorioArrecadacaoTab />}

    </main>
  );
}

// ── Alíquotas IPTU Tab ────────────────────────────────────────────────────────

type Aliquota = { id: number; exercicio: number; uso: string; aliquota: number; descricao: string };

function AliquotasTab() {
  const { toast } = useToast();
  const [exercicio, setExercicio] = useState(new Date().getFullYear());
  const [gerarExercicio, setGerarExercicio] = useState(new Date().getFullYear());
  const [gerarVenc, setGerarVenc] = useState(`${new Date().getFullYear()}-03-31`);
  const [aliquotas, setAliquotas] = useState<Aliquota[]>([]);
  const [uso, setUso] = useState("residencial");
  const [aliquota, setAliquota] = useState("");
  const [descricao, setDescricao] = useState("");

  const load = async () => {
    try {
      const d = await authJson(`/tributario/aliquotas-iptu?exercicio=${exercicio}`);
      setAliquotas(d);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  useEffect(() => { load(); }, [exercicio]);

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await authJson("/tributario/aliquotas-iptu", {
        method: "POST", body: JSON.stringify({ exercicio, uso, aliquota: parseFloat(aliquota), descricao }),
      });
      toast("Alíquota cadastrada."); setAliquota(""); setDescricao(""); load();
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Excluir alíquota?")) return;
    try {
      await authJson(`/tributario/aliquotas-iptu/${id}`, { method: "DELETE" });
      toast("Alíquota removida."); load();
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const handleGerarIPTU = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      const r = await authJson(`/tributario/lancamentos/gerar-iptu?exercicio=${gerarExercicio}&vencimento=${gerarVenc}`, { method: "POST" });
      toast(`IPTU gerado: ${r.gerados} lançamentos criados. Ignorados: já existia=${r.ignorados_ja_existia}, sem alíquota=${r.ignorados_sem_aliquota}, valor zero=${r.ignorados_valor_zero}.`);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  return (
    <section className="section-stack section-top">
      <h2>Alíquotas IPTU por Uso</h2>
      <div className="toolbar">
        <label>Exercício:</label>
        <input type="number" value={exercicio} onChange={(e) => setExercicio(+e.target.value)} className="input-narrow" />
      </div>
      <table>
        <thead><tr><th>Exercício</th><th>Uso</th><th>Alíquota (%)</th><th>Descrição</th><th>Ação</th></tr></thead>
        <tbody>
          {aliquotas.length > 0 ? aliquotas.map((a) => (
            <tr key={a.id}>
              <td>{a.exercicio}</td>
              <td>{a.uso}</td>
              <td>{(a.aliquota * 100).toFixed(3)}%</td>
              <td>{a.descricao}</td>
              <td><button className="btn" onClick={() => handleDelete(a.id)}>Excluir</button></td>
            </tr>
          )) : <tr><td colSpan={5} className="empty-state">Nenhuma alíquota cadastrada para este exercício.</td></tr>}
        </tbody>
      </table>
      <details open>
        <summary className="summary-toggle mb-2">Cadastrar nova alíquota</summary>
        <form className="form-grid" onSubmit={handleCreate}>
          <label>Uso
            <select value={uso} onChange={(e) => setUso(e.target.value)}>
              {["residencial", "comercial", "industrial", "rural"].map((u) => <option key={u}>{u}</option>)}
            </select>
          </label>
          <label>Alíquota (ex: 0.005 = 0.5%)
            <input type="number" step="0.0001" value={aliquota} onChange={(e) => setAliquota(e.target.value)} required />
          </label>
          <label>Descrição
            <input value={descricao} onChange={(e) => setDescricao(e.target.value)} />
          </label>
          <button className="btn" type="submit">Cadastrar</button>
        </form>
      </details>

      <hr />
      <h2>Gerar IPTU em Lote</h2>
      <p className="muted">Gera lançamentos de IPTU para todos os imóveis ativos com alíquota configurada para o exercício.</p>
      <form className="form-grid" onSubmit={handleGerarIPTU}>
        <label>Exercício
          <input type="number" value={gerarExercicio} onChange={(e) => setGerarExercicio(+e.target.value)} className="input-narrow" />
        </label>
        <label>Vencimento
          <input type="date" value={gerarVenc} onChange={(e) => setGerarVenc(e.target.value)} required />
        </label>
        <button className="btn" type="submit">Gerar IPTU</button>
      </form>
    </section>
  );
}

// ── Parcelamentos Tab ─────────────────────────────────────────────────────────

type Parcelamento = { id: number; divida_id: number; numero_parcelas: number; valor_total: number; data_acordo: string; status: string; parcelas: Parcela[] };
type Parcela = { id: number; numero_parcela: number; valor: number; vencimento: string; status: string; data_pagamento: string | null };

function ParcelamentosTab() {
  const { toast } = useToast();
  const [dividaId, setDividaId] = useState("");
  const [parcelamentos, setParcelamentos] = useState<Paged<Parcelamento> | null>(null);
  const [selected, setSelected] = useState<Parcelamento | null>(null);
  const [numParcelas, setNumParcelas] = useState("6");
  const [valorTotal, setValorTotal] = useState("");
  const [dataAcordo, setDataAcordo] = useState(new Date().toISOString().slice(0, 10));

  const load = async () => {
    try {
      const qs = dividaId ? `?divida_id=${dividaId}` : "?page=1&size=20";
      const d = await authJson(`/tributario/parcelamentos${qs}`);
      setParcelamentos(d);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const loadDetail = async (id: number) => {
    try {
      const d = await authJson(`/tributario/parcelamentos/${id}`);
      setSelected(d);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const handleCreate = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!dividaId) { toast("Informe o ID da dívida ativa.", "error"); return; }
    try {
      await authJson("/tributario/parcelamentos", {
        method: "POST",
        body: JSON.stringify({ divida_id: +dividaId, numero_parcelas: +numParcelas, valor_total: +valorTotal, data_acordo: dataAcordo }),
      });
      toast("Parcelamento criado."); load();
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const handlePagar = async (pid: number, parcId: number) => {
    const dataPag = prompt("Data de pagamento (YYYY-MM-DD):", new Date().toISOString().slice(0, 10));
    if (!dataPag) return;
    try {
      const r = await authJson(`/tributario/parcelamentos/${pid}/parcelas/${parcId}/pagar`, {
        method: "POST", body: JSON.stringify({ data_pagamento: dataPag }),
      });
      toast(r.parcelamento_quitado ? "Parcelamento quitado! Dívida encerrada." : "Parcela registrada.");
      loadDetail(pid);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const fmtBRL = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <section className="section-stack section-top">
      <h2>Parcelamentos de Dívida Ativa</h2>
      <div className="toolbar">
        <input placeholder="ID da Dívida Ativa (opcional)" value={dividaId} onChange={(e) => setDividaId(e.target.value)} className="input-narrow" />
        <button className="btn" onClick={load}>Buscar</button>
      </div>
      <table>
        <thead><tr><th>ID</th><th>Dívida ID</th><th>Parcelas</th><th>Valor total</th><th>Data acordo</th><th>Status</th><th>Detalhe</th></tr></thead>
        <tbody>
          {(parcelamentos?.items || []).length > 0 ? parcelamentos!.items.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td>
              <td>{p.divida_id}</td>
              <td>{p.numero_parcelas}</td>
              <td>{fmtBRL(p.valor_total)}</td>
              <td>{p.data_acordo}</td>
              <td><span className={`chip ${p.status === "quitado" ? "pago" : p.status === "ativo" ? "empenhado" : "pendente"}`}>{p.status}</span></td>
              <td><button className="btn" onClick={() => loadDetail(p.id)}>Ver parcelas</button></td>
            </tr>
          )) : <tr><td colSpan={7} className="empty-state">Nenhum parcelamento encontrado.</td></tr>}
        </tbody>
      </table>

      {selected && (
        <div className="mt-2">
          <h3>Parcelas do Parcelamento #{selected.id}</h3>
          <table>
            <thead><tr><th>#</th><th>Valor</th><th>Vencimento</th><th>Status</th><th>Pagamento</th><th>Ação</th></tr></thead>
            <tbody>
              {selected.parcelas.map((p) => (
                <tr key={p.id}>
                  <td>{p.numero_parcela}</td>
                  <td>{fmtBRL(p.valor)}</td>
                  <td>{p.vencimento}</td>
                  <td><span className={`chip ${p.status === "paga" ? "pago" : "pendente"}`}>{p.status}</span></td>
                  <td>{p.data_pagamento || "—"}</td>
                  <td>{p.status !== "paga" && <button className="btn" onClick={() => handlePagar(selected.id, p.id)}>Pagar</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <details>
        <summary className="summary-toggle mt-4">Criar novo parcelamento</summary>
        <form className="form-grid mt-2" onSubmit={handleCreate}>
          <label>ID da Dívida Ativa *
            <input value={dividaId} onChange={(e) => setDividaId(e.target.value)} required />
          </label>
          <label>Nº de parcelas
            <input type="number" min={1} value={numParcelas} onChange={(e) => setNumParcelas(e.target.value)} required />
          </label>
          <label>Valor total (R$)
            <input type="number" step="0.01" value={valorTotal} onChange={(e) => setValorTotal(e.target.value)} required />
          </label>
          <label>Data do acordo
            <input type="date" value={dataAcordo} onChange={(e) => setDataAcordo(e.target.value)} required />
          </label>
          <button className="btn" type="submit">Criar Parcelamento</button>
        </form>
      </details>
    </section>
  );
}

// ── Relatório de Arrecadação Tab ──────────────────────────────────────────────

function RelatorioArrecadacaoTab() {
  const [tributo, setTributo] = useState("");
  const [exercicio, setExercicio] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [data, setData] = useState<{ total_arrecadado: number; registros: { tributo: string; exercicio: number; competencia: string; qtd_lancamentos: number; valor_total: number }[] } | null>(null);
  const { toast } = useToast();

  const buildQS = () => {
    const p = new URLSearchParams();
    if (tributo) p.set("tributo", tributo);
    if (exercicio) p.set("exercicio", exercicio);
    if (dataInicio) p.set("data_inicio", dataInicio);
    if (dataFim) p.set("data_fim", dataFim);
    return p.toString();
  };

  const load = async () => {
    try {
      const d = await authJson(`/tributario/relatorio/arrecadacao?${buildQS()}`);
      setData(d);
    } catch (e) { toast("Erro: " + (e instanceof Error ? e.message : "falha"), "error"); }
  };

  const csvHref = () => {
    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const p = new URLSearchParams({ export: "csv" });
    if (tributo) p.set("tributo", tributo);
    if (exercicio) p.set("exercicio", exercicio);
    if (dataInicio) p.set("data_inicio", dataInicio);
    if (dataFim) p.set("data_fim", dataFim);
    return `${API}/tributario/relatorio/arrecadacao?${p.toString()}`;
  };

  const fmtBRL = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <section className="section-stack section-top">
      <h2>Relatório Consolidado de Arrecadação</h2>
      <div className="toolbar-wrap">
        <select value={tributo} onChange={(e) => setTributo(e.target.value)}>
          <option value="">Todos os tributos</option>
          {["IPTU","ISS","ITBI","TAXA_LIXO","TAXA_ILUMINACAO","TAXA_OBRAS"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <input type="number" placeholder="Exercício" value={exercicio} onChange={(e) => setExercicio(e.target.value)} className="input-narrow" />
        <label className="label-inline">De: <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} /></label>
        <label className="label-inline">Até: <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} /></label>
        <button className="btn" onClick={load}>Filtrar</button>
        <a className="btn" href={csvHref()} target="_blank" rel="noreferrer">Exportar CSV</a>
      </div>

      {data && (
        <>
          <div className="total-line">
            Total arrecadado: {fmtBRL(data.total_arrecadado)}
          </div>
          <table>
            <thead><tr><th>Tributo</th><th>Exercício</th><th>Competência</th><th>Qtd lançamentos</th><th>Valor total</th></tr></thead>
            <tbody>
              {data.registros.length > 0 ? data.registros.map((r, i) => (
                <tr key={i}>
                  <td>{r.tributo}</td>
                  <td>{r.exercicio}</td>
                  <td>{r.competencia}</td>
                  <td>{r.qtd_lancamentos}</td>
                  <td>{fmtBRL(r.valor_total)}</td>
                </tr>
              )) : <tr><td colSpan={5} className="empty-state">Nenhum registro encontrado.</td></tr>}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

