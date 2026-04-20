"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

// ── Types ─────────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type ConfigEntidade = {
  id: number;
  nome_entidade: string;
  cnpj: string;
  codigo_ibge: string;
  uf: string;
  esfera: string;
  poder: string;
  tipo_entidade: string;
  responsavel_nome: string;
  responsavel_cargo: string;
  responsavel_cpf: string;
  ativo: boolean;
  updated_at: string;
};

type Inconsistencia = {
  severidade: "ERRO" | "AVISO";
  codigo: string;
  mensagem: string;
  valor_encontrado?: string;
  valor_esperado?: string;
};

type ValidacaoResult = {
  exercicio: number;
  total_erros: number;
  total_avisos: number;
  pode_exportar: boolean;
  inconsistencias: Inconsistencia[];
};

type Dashboard = {
  exercicio: number;
  status_preparacao: string;
  validacao: { erros: number; avisos: number; pode_exportar: boolean };
  modulos: { entidade_configurada: boolean; loa_vigente: boolean; ppa_vigente: boolean; ldo_vigente: boolean };
  resumo_financeiro: { receita_arrecadada: number; despesa_paga: number; saldo: number; rcl_12meses: number; despesa_pessoal_bruta: number; pct_pessoal_rcl: number };
  exportacoes_geradas: number;
};

type ExportacaoItem = {
  id: number;
  tipo: string;
  exercicio: number;
  periodo: string | null;
  status: string;
  inconsistencias: number;
  created_at: string;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function messageFrom(e: unknown) {
  if (e instanceof Error) return e.message;
  return String(e);
}

const anoAtual = new Date().getFullYear();

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SiconfiSiopPage() {
  const [tab, setTab] = useState<"dashboard" | "config" | "finbra" | "rreo" | "rgf" | "siop" | "exportar" | "historico" | "xml">("dashboard");
  const { toast } = useToast();
  const [exercicio, setExercicio] = useState(String(anoAtual));

  // Dashboard
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [validacao, setValidacao] = useState<ValidacaoResult | null>(null);

  // Config
  const [cfg, setCfg] = useState<ConfigEntidade | null>(null);
  const [cfgNome, setCfgNome] = useState("");
  const [cfgCnpj, setCfgCnpj] = useState("");
  const [cfgIbge, setCfgIbge] = useState("");
  const [cfgUf, setCfgUf] = useState("");
  const [cfgEsfera, setCfgEsfera] = useState("Municipal");
  const [cfgPoder, setCfgPoder] = useState("Executivo");
  const [cfgTipo, setCfgTipo] = useState("Prefeitura Municipal");
  const [cfgRespNome, setCfgRespNome] = useState("");
  const [cfgRespCargo, setCfgRespCargo] = useState("");
  const [cfgRespCpf, setCfgRespCpf] = useState("");

  // FINBRA
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [finbraData, setFinbraData] = useState<any>(null);

  // RREO
  const [rreoBimestre, setRreoBimestre] = useState("1");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rreoData, setRreoData] = useState<any>(null);

  // RGF
  const [rgfQuad, setRgfQuad] = useState("1");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rgfData, setRgfData] = useState<any>(null);

  // SIOP
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [siopData, setSiopData] = useState<any>(null);

  // Exportar
  const [expTipo, setExpTipo] = useState("finbra");
  const [expPeriodo, setExpPeriodo] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [expResult, setExpResult] = useState<any>(null);

  // Histórico
  const [historico, setHistorico] = useState<Paged<ExportacaoItem> | null>(null);
  const [histPage, setHistPage] = useState(1);
  const [histFiltroTipo, setHistFiltroTipo] = useState("");

  // ── Load ─────────────────────────────────────────────────────────────────

  async function loadDashboard() {
    try {
      const d = await authJson(`/siconfi/dashboard?exercicio=${exercicio}`);
      setDash(d);
      const v = await authJson(`/siconfi/validar?exercicio=${exercicio}`);
      setValidacao(v);
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadConfig() {
    try {
      const d = await authJson("/siconfi/config");
      if (d) {
        setCfg(d);
        setCfgNome(d.nome_entidade);
        setCfgCnpj(d.cnpj);
        setCfgIbge(d.codigo_ibge);
        setCfgUf(d.uf);
        setCfgEsfera(d.esfera);
        setCfgPoder(d.poder);
        setCfgTipo(d.tipo_entidade);
        setCfgRespNome(d.responsavel_nome);
        setCfgRespCargo(d.responsavel_cargo);
        setCfgRespCpf(d.responsavel_cpf);
      }
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadHistorico() {
    try {
      const params = new URLSearchParams({ page: String(histPage), size: "20" });
      if (exercicio) params.set("exercicio", exercicio);
      if (histFiltroTipo) params.set("tipo", histFiltroTipo);
      const d = await authJson(`/siconfi/exportacoes?${params}`);
      setHistorico(d);
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  useEffect(() => { if (tab === "dashboard") loadDashboard(); }, [tab, exercicio]);
  useEffect(() => { if (tab === "config") loadConfig(); }, [tab]);
  useEffect(() => { if (tab === "historico") loadHistorico(); }, [tab, histPage, histFiltroTipo, exercicio]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function saveConfig(e: FormEvent) {
    e.preventDefault();
    try {
      await authJson("/siconfi/config", {
        method: "POST",
        body: JSON.stringify({
          nome_entidade: cfgNome, cnpj: cfgCnpj, codigo_ibge: cfgIbge,
          uf: cfgUf, esfera: cfgEsfera, poder: cfgPoder, tipo_entidade: cfgTipo,
          responsavel_nome: cfgRespNome, responsavel_cargo: cfgRespCargo, responsavel_cpf: cfgRespCpf,
        }),
      });
      toast("Configuração salva com sucesso.");
      loadConfig();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadFinbra() {
    setFinbraData(null);
    try { setFinbraData(await authJson(`/siconfi/finbra?exercicio=${exercicio}`)); }
    catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadRreo() {
    setRreoData(null);
    try { setRreoData(await authJson(`/siconfi/rreo?exercicio=${exercicio}&bimestre=${rreoBimestre}`)); }
    catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadRgf() {
    setRgfData(null);
    try { setRgfData(await authJson(`/siconfi/rgf?exercicio=${exercicio}&quadrimestre=${rgfQuad}`)); }
    catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadSiop() {
    setSiopData(null);
    try { setSiopData(await authJson(`/siconfi/siop-programas?exercicio=${exercicio}`)); }
    catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function exportar(e: FormEvent) {
    e.preventDefault();
    setExpResult(null);
    try {
      const body: Record<string, unknown> = { tipo: expTipo, exercicio: Number(exercicio) };
      if (expPeriodo) body.periodo = expPeriodo;
      const d = await authJson("/siconfi/exportar", { method: "POST", body: JSON.stringify(body) });
      setExpResult(d);
      toast(`Exportação gerada: ID ${d.id} · status ${d.status}`);
      if (tab === "historico") loadHistorico();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  // XML / Validação (Onda 19)
  const [xmlTipo, setXmlTipo] = useState("finbra");
  const [xmlBimestre, setXmlBimestre] = useState("1");
  const [xmlQuad, setXmlQuad] = useState("1");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [xmlResult, setXmlResult] = useState<any>(null);
  const [xmlLoading, setXmlLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [xmlHistorico, setXmlHistorico] = useState<Paged<any> | null>(null);
  const [xmlHistPage, setXmlHistPage] = useState(1);
  const [xmlHistFiltro, setXmlHistFiltro] = useState("");
  const [xmlHistValido, setXmlHistValido] = useState("");

  async function gerarXml(e: React.FormEvent) {
    e.preventDefault();
    setXmlResult(null); setXmlLoading(true);
    try {
      const params = new URLSearchParams({ exercicio });
      if (xmlTipo === "rreo") params.set("bimestre", xmlBimestre);
      if (xmlTipo === "rgf") params.set("quadrimestre", xmlQuad);
      const d = await authJson(`/siconfi/xml/${xmlTipo}?${params}`);
      setXmlResult(d);
      toast(d.valido ? "✓ XML válido — pronto para export." : `⚠ XML gerado com ${d.erros_xsd?.length ?? 0} erro(s)`, d.valido ? undefined : "error");
    } catch (err) { toast("Erro: " + messageFrom(err), "error"); }
    finally { setXmlLoading(false); }
  }

  async function downloadXml(tipo: string) {
    const params = new URLSearchParams({ exercicio });
    if (tipo === "rreo") params.set("bimestre", xmlBimestre);
    if (tipo === "rgf") params.set("quadrimestre", xmlQuad);
    params.set("download", "true");
    window.open(`/api/proxy/siconfi/xml/${tipo}?${params}`, "_blank");
  }

  async function loadXmlHistorico() {
    try {
      const params = new URLSearchParams({ page: String(xmlHistPage), size: "20" });
      if (xmlHistFiltro) params.set("tipo", xmlHistFiltro);
      if (exercicio) params.set("exercicio", exercicio);
      if (xmlHistValido) params.set("valido", xmlHistValido);
      const d = await authJson(`/siconfi/xml/historico?${params}`);
      setXmlHistorico(d);
    } catch (err) { toast("Erro: " + messageFrom(err), "error"); }
  }

  useEffect(() => { if (tab === "xml") loadXmlHistorico(); }, [tab, xmlHistPage, xmlHistFiltro, xmlHistValido, exercicio]);

  const TABS = [
    { key: "dashboard", label: "Dashboard" },
    { key: "config", label: "Entidade" },
    { key: "finbra", label: "FINBRA" },
    { key: "rreo", label: "RREO" },
    { key: "rgf", label: "RGF" },
    { key: "siop", label: "SIOP" },
    { key: "exportar", label: "Exportar" },
    { key: "historico", label: "Histórico" },
    { key: "xml", label: "XML / Onda 19" },
  ] as const;

  return (
    <main className="page-main">
      <h1 className="page-title">SICONFI / SIOP — Prestação de Contas Federal</h1>
      <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.75rem" }}>
        Camada preparatória: gera e valida os dados localmente antes do envio ao governo federal.
        Não realiza envio via webservice — apenas exporta payloads estruturados para revisão.
      </p>

      {/* Exercício global */}
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginBottom: "1rem" }}>
        <label style={{ fontWeight: 600 }}>Exercício:</label>
        <input type="number" value={exercicio} onChange={(e) => setExercicio(e.target.value)}
          className="form-input" style={{ width: 110 }} />
      </div>


      {/* Tabs */}
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={tab === t.key ? "tab active" : "tab"}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── DASHBOARD ──────────────────────────────────────────────────────── */}
      {tab === "dashboard" && (
        <div>
          <div className="toolbar">
            <button className="btn btn-secondary" onClick={loadDashboard}>↻ Atualizar</button>
          </div>

          {dash && (
            <div className="stats-grid">
              <div className={`stat-card ${dash.status_preparacao === "PRONTO" ? "success" : "warning"}`}>
                <div className="stat-label">Status de Preparação</div>
                <div className="stat-value">{dash.status_preparacao}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Erros / Avisos</div>
                <div className="stat-value">{dash.validacao.erros} / {dash.validacao.avisos}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Receita Arrecadada</div>
                <div className="stat-value">R$ {fmt(dash.resumo_financeiro.receita_arrecadada)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Despesa Paga</div>
                <div className="stat-value">R$ {fmt(dash.resumo_financeiro.despesa_paga)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">RCL 12 meses</div>
                <div className="stat-value">R$ {fmt(dash.resumo_financeiro.rcl_12meses)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Despesa Pessoal / RCL</div>
                <div className="stat-value">{dash.resumo_financeiro.pct_pessoal_rcl}%</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Exportações Geradas</div>
                <div className="stat-value">{dash.exportacoes_geradas}</div>
              </div>
            </div>
          )}

          {dash && (
            <div style={{ marginTop: "1.5rem" }}>
              <h3 className="section-title">Módulos</h3>
              <div className="stats-grid">
                {Object.entries(dash.modulos).map(([k, v]) => (
                  <div key={k} className={`stat-card ${v ? "success" : "warning"}`}>
                    <div className="stat-label">{k.replace(/_/g, " ")}</div>
                    <div className="stat-value">{v ? "✓" : "✗"}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {validacao && validacao.inconsistencias.length > 0 && (
            <div style={{ marginTop: "1.5rem" }}>
              <h3 className="section-title">Inconsistências ({validacao.total_erros} erro(s), {validacao.total_avisos} aviso(s))</h3>
              <div className="table-responsive">
                <table className="data-table">
                  <thead><tr><th>Sev.</th><th>Código</th><th>Mensagem</th><th>Encontrado</th><th>Esperado</th></tr></thead>
                  <tbody>
                    {validacao.inconsistencias.map((inc, i) => (
                      <tr key={i}>
                        <td><span className={`status-chip ${inc.severidade === "ERRO" ? "cancelado" : "rascunho"}`}>{inc.severidade}</span></td>
                        <td><code>{inc.codigo}</code></td>
                        <td>{inc.mensagem}</td>
                        <td>{inc.valor_encontrado ?? "—"}</td>
                        <td>{inc.valor_esperado ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── ENTIDADE ───────────────────────────────────────────────────────── */}
      {tab === "config" && (
        <form onSubmit={saveConfig} className="form-card">
          <h3 className="form-title">Configuração da Entidade</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", marginBottom: "0.5rem" }}>
            Dados obrigatórios para o cabeçalho das exportações SICONFI/FINBRA/SIOP.
          </p>
          <div className="form-grid">
            <div className="form-group">
              <label>Nome da Entidade *</label>
              <input className="form-input" value={cfgNome} onChange={(e) => setCfgNome(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>CNPJ * (XX.XXX.XXX/XXXX-XX)</label>
              <input className="form-input" value={cfgCnpj} onChange={(e) => setCfgCnpj(e.target.value)} required placeholder="12.345.678/0001-90" />
            </div>
            <div className="form-group">
              <label>Código IBGE * (7 dígitos)</label>
              <input className="form-input" value={cfgIbge} onChange={(e) => setCfgIbge(e.target.value)} required maxLength={7} placeholder="1234567" />
            </div>
            <div className="form-group">
              <label>UF *</label>
              <input className="form-input" value={cfgUf} onChange={(e) => setCfgUf(e.target.value)} required maxLength={2} placeholder="SP" />
            </div>
            <div className="form-group">
              <label>Esfera</label>
              <select className="form-select" value={cfgEsfera} onChange={(e) => setCfgEsfera(e.target.value)}>
                <option>Municipal</option><option>Estadual</option><option>Federal</option>
              </select>
            </div>
            <div className="form-group">
              <label>Poder</label>
              <select className="form-select" value={cfgPoder} onChange={(e) => setCfgPoder(e.target.value)}>
                <option>Executivo</option><option>Legislativo</option><option>Judiciário</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tipo de Entidade</label>
              <input className="form-input" value={cfgTipo} onChange={(e) => setCfgTipo(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Responsável — Nome</label>
              <input className="form-input" value={cfgRespNome} onChange={(e) => setCfgRespNome(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Responsável — Cargo</label>
              <input className="form-input" value={cfgRespCargo} onChange={(e) => setCfgRespCargo(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Responsável — CPF</label>
              <input className="form-input" value={cfgRespCpf} onChange={(e) => setCfgRespCpf(e.target.value)} placeholder="000.000.000-00" />
            </div>
          </div>
          {cfg && (
            <p style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)" }}>
              Última atualização: {new Date(cfg.updated_at).toLocaleString("pt-BR")}
            </p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">Salvar</button>
          </div>
        </form>
      )}

      {/* ── FINBRA ─────────────────────────────────────────────────────────── */}
      {tab === "finbra" && (
        <div>
          <div className="toolbar">
            <button className="btn btn-primary" onClick={loadFinbra}>Gerar FINBRA {exercicio}</button>
          </div>
          {finbraData && (
            <div>
              <h3 className="section-title">Balanço Orçamentário FINBRA — {finbraData.cabecalho.exercicio}</h3>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">Receita Prevista (LOA)</div><div className="stat-value">R$ {fmt(finbraData.balanco_receita.receita_prevista_loa)}</div></div>
                <div className="stat-card"><div className="stat-label">Receita Arrecadada</div><div className="stat-value">R$ {fmt(finbraData.balanco_receita.receita_arrecadada)}</div></div>
                <div className="stat-card"><div className="stat-label">% Realização</div><div className="stat-value">{finbraData.balanco_receita.pct_realizacao}%</div></div>
                <div className="stat-card"><div className="stat-label">Dotação Autorizada</div><div className="stat-value">R$ {fmt(finbraData.balanco_despesa.dotacao_autorizada)}</div></div>
                <div className="stat-card"><div className="stat-label">Despesa Empenhada</div><div className="stat-value">R$ {fmt(finbraData.balanco_despesa.despesa_empenhada)}</div></div>
                <div className="stat-card"><div className="stat-label">Despesa Paga</div><div className="stat-value">R$ {fmt(finbraData.balanco_despesa.despesa_paga)}</div></div>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <h4>Indicadores LRF</h4>
                <div className="stats-grid">
                  <div className="stat-card"><div className="stat-label">RCL 12 meses</div><div className="stat-value">R$ {fmt(finbraData.indicadores_lrf.rcl_12meses)}</div></div>
                  <div className="stat-card"><div className="stat-label">Despesa Pessoal</div><div className="stat-value">R$ {fmt(finbraData.indicadores_lrf.despesa_pessoal_bruta)}</div></div>
                  <div className="stat-card"><div className="stat-label">% Pessoal/RCL</div><div className="stat-value">{finbraData.indicadores_lrf.pct_pessoal_rcl}%</div></div>
                  <div className={`stat-card ${finbraData.indicadores_lrf.situacao_pessoal === "REGULAR" ? "success" : "warning"}`}>
                    <div className="stat-label">Situação Pessoal LRF</div>
                    <div className="stat-value">{finbraData.indicadores_lrf.situacao_pessoal}</div>
                  </div>
                  <div className={`stat-card ${finbraData.resultado_exercicio.tipo === "superavit" ? "success" : "warning"}`}>
                    <div className="stat-label">Resultado do Exercício</div>
                    <div className="stat-value">{finbraData.resultado_exercicio.tipo.toUpperCase()}: R$ {fmt(Math.abs(finbraData.resultado_exercicio.saldo))}</div>
                  </div>
                  <div className="stat-card"><div className="stat-label">Dívida Consolidada</div><div className="stat-value">R$ {fmt(finbraData.indicadores_lrf.divida_consolidada)}</div></div>
                </div>
              </div>
              <details style={{ marginTop: "1rem" }}>
                <summary style={{ cursor: "pointer", fontWeight: 600 }}>Ver JSON completo</summary>
                <pre style={{ fontSize: "0.72rem", background: "var(--color-surface-raised)", padding: "1rem", borderRadius: "6px", overflow: "auto", maxHeight: 300 }}>
                  {JSON.stringify(finbraData, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      )}

      {/* ── RREO ───────────────────────────────────────────────────────────── */}
      {tab === "rreo" && (
        <div>
          <div className="toolbar">
            <label style={{ fontWeight: 600 }}>Bimestre:</label>
            <select className="form-select" style={{ width: 80 }} value={rreoBimestre} onChange={(e) => setRreoBimestre(e.target.value)}>
              {[1, 2, 3, 4, 5, 6].map((b) => <option key={b}>{b}</option>)}
            </select>
            <button className="btn btn-primary" onClick={loadRreo}>Gerar RREO</button>
          </div>
          {rreoData && (
            <div>
              <h3 className="section-title">RREO — {rreoData.cabecalho.referencia}</h3>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">Receita Prevista (LOA)</div><div className="stat-value">R$ {fmt(rreoData.receitas.prevista_loa)}</div></div>
                <div className="stat-card"><div className="stat-label">Receita Arrecadada (bimestre)</div><div className="stat-value">R$ {fmt(rreoData.receitas.arrecadada_bimestre)}</div></div>
                <div className="stat-card"><div className="stat-label">Receita Arrecadada (acumulada)</div><div className="stat-value">R$ {fmt(rreoData.receitas.arrecadada_acumulada)}</div></div>
                <div className="stat-card"><div className="stat-label">Despesa Paga (bimestre)</div><div className="stat-value">R$ {fmt(rreoData.despesas_totais.paga_bimestre)}</div></div>
                <div className="stat-card"><div className="stat-label">Despesa Paga (acumulada)</div><div className="stat-value">R$ {fmt(rreoData.despesas_totais.paga_acumulada)}</div></div>
              </div>
              {rreoData.despesas_por_funcao.length > 0 && (
                <div style={{ marginTop: "1rem" }}>
                  <h4>Despesas por Função</h4>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead><tr><th>Função</th><th>Dotação Autorizada</th><th>Executado</th></tr></thead>
                      <tbody>
                        {rreoData.despesas_por_funcao.map((f: { function_code: string; dotacao_autorizada: number; dotacao_executada: number }, i: number) => (
                          <tr key={i}>
                            <td>{f.function_code}</td>
                            <td>R$ {fmt(f.dotacao_autorizada)}</td>
                            <td>R$ {fmt(f.dotacao_executada)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── RGF ────────────────────────────────────────────────────────────── */}
      {tab === "rgf" && (
        <div>
          <div className="toolbar">
            <label style={{ fontWeight: 600 }}>Quadrimestre:</label>
            <select className="form-select" style={{ width: 80 }} value={rgfQuad} onChange={(e) => setRgfQuad(e.target.value)}>
              {[1, 2, 3].map((q) => <option key={q}>{q}</option>)}
            </select>
            <button className="btn btn-primary" onClick={loadRgf}>Gerar RGF</button>
          </div>
          {rgfData && (
            <div>
              <h3 className="section-title">RGF — {rgfData.cabecalho.referencia}</h3>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">RCL 12 meses</div><div className="stat-value">R$ {fmt(rgfData.despesa_pessoal.rcl_12meses)}</div></div>
                <div className="stat-card"><div className="stat-label">Desp. Pessoal Acumulada</div><div className="stat-value">R$ {fmt(rgfData.despesa_pessoal.acumulada_ano)}</div></div>
                <div className="stat-card"><div className="stat-label">Limite 60% RCL</div><div className="stat-value">R$ {fmt(rgfData.despesa_pessoal.limite_legal_60pct)}</div></div>
                <div className="stat-card"><div className="stat-label">% Pessoal/RCL</div><div className="stat-value">{rgfData.despesa_pessoal.pct_rcl}%</div></div>
                <div className={`stat-card ${rgfData.despesa_pessoal.situacao === "REGULAR" ? "success" : "warning"}`}>
                  <div className="stat-label">Situação LRF</div>
                  <div className="stat-value">{rgfData.despesa_pessoal.situacao}</div>
                </div>
                <div className="stat-card"><div className="stat-label">Dívida Consolidada</div><div className="stat-value">R$ {fmt(rgfData.divida_consolidada.saldo)}</div></div>
                <div className="stat-card"><div className="stat-label">Disponibilidade Financeira</div><div className="stat-value">R$ {fmt(rgfData.disponibilidade_financeira.saldo)}</div></div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SIOP ───────────────────────────────────────────────────────────── */}
      {tab === "siop" && (
        <div>
          <div className="toolbar">
            <button className="btn btn-primary" onClick={loadSiop}>Gerar SIOP {exercicio}</button>
          </div>
          {siopData && (
            <div>
              <h3 className="section-title">SIOP — Programas e Ações</h3>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">Programas PPA</div><div className="stat-value">{siopData.totais.programas_ppa}</div></div>
                <div className="stat-card"><div className="stat-label">Ações LOA</div><div className="stat-value">{siopData.totais.acoes_loa}</div></div>
                <div className="stat-card"><div className="stat-label">Metas LDO</div><div className="stat-value">{siopData.totais.metas_ldo}</div></div>
              </div>

              {siopData.programas_ppa.length > 0 && (
                <div style={{ marginTop: "1rem" }}>
                  <h4>Programas PPA</h4>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead><tr><th>Código</th><th>Nome</th><th>Objetivo</th><th>Valor Estimado</th><th>Período PPA</th></tr></thead>
                      <tbody>
                        {siopData.programas_ppa.map((p: { codigo: string; nome: string; objetivo: string; valor_estimado: number; ppa_periodo: string }, i: number) => (
                          <tr key={i}>
                            <td>{p.codigo}</td><td>{p.nome}</td><td>{p.objetivo}</td>
                            <td>R$ {fmt(p.valor_estimado)}</td><td>{p.ppa_periodo}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {siopData.acoes_loa.length > 0 && (
                <div style={{ marginTop: "1rem" }}>
                  <h4>Ações LOA</h4>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead><tr><th>Função</th><th>Subfunção</th><th>Programa</th><th>Ação</th><th>Descrição</th><th>Dotação</th><th>Executado</th></tr></thead>
                      <tbody>
                        {siopData.acoes_loa.map((a: { function_code: string; subfunction_code: string; program_code: string; action_code: string; description: string; dotacao_autorizada: number; dotacao_executada: number }, i: number) => (
                          <tr key={i}>
                            <td>{a.function_code}</td><td>{a.subfunction_code}</td>
                            <td>{a.program_code}</td><td>{a.action_code}</td>
                            <td>{a.description}</td>
                            <td>R$ {fmt(a.dotacao_autorizada)}</td>
                            <td>R$ {fmt(a.dotacao_executada)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── EXPORTAR ───────────────────────────────────────────────────────── */}
      {tab === "exportar" && (
        <div>
          <form onSubmit={exportar} className="form-card">
            <h3 className="form-title">Registrar Exportação</h3>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)" }}>
              Gera e salva um snapshot auditável dos dados para SICONFI/SIOP.
              Não realiza envio ao governo federal.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label>Tipo *</label>
                <select className="form-select" value={expTipo} onChange={(e) => setExpTipo(e.target.value)}>
                  <option value="finbra">FINBRA — Balanço Orçamentário</option>
                  <option value="rreo">RREO — Bimestral</option>
                  <option value="rgf">RGF — Quadrimestral</option>
                  <option value="siop_programas">SIOP — Programas e Ações</option>
                </select>
              </div>
              <div className="form-group">
                <label>Período (opcional)</label>
                <input className="form-input" value={expPeriodo}
                  onChange={(e) => setExpPeriodo(e.target.value)}
                  placeholder="ex: bimestre_3 | quad_2" />
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">Gerar Exportação</button>
            </div>
            {expResult && (
              <div style={{ marginTop: "1rem", padding: "0.75rem", background: "var(--color-surface-raised)", borderRadius: 6 }}>
                <strong>Exportação gerada:</strong> ID {expResult.id} · Tipo: {expResult.tipo} · Status: {expResult.status} · Inconsistências: {expResult.inconsistencias}
              </div>
            )}
          </form>
        </div>
      )}

      {/* ── HISTÓRICO ──────────────────────────────────────────────────────── */}
      {tab === "historico" && (
        <div>
          <div className="toolbar">
            <div className="action-row">
              <select className="form-select" value={histFiltroTipo} onChange={(e) => { setHistFiltroTipo(e.target.value); setHistPage(1); }}>
                <option value="">Todos os tipos</option>
                <option value="finbra">FINBRA</option>
                <option value="rreo">RREO</option>
                <option value="rgf">RGF</option>
                <option value="siop_programas">SIOP</option>
              </select>
              <button className="btn btn-secondary" onClick={loadHistorico}>↻ Atualizar</button>
            </div>
          </div>
          {historico && (
            <>
              <div className="table-meta">{historico.total} exportação(ões)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Tipo</th><th>Exercício</th><th>Período</th><th>Status</th><th>Inconsistências</th><th>Gerado em</th></tr></thead>
                  <tbody>
                    {historico.items.map((e) => (
                      <tr key={e.id}>
                        <td>{e.id}</td>
                        <td><span className="status-chip ativo">{e.tipo}</span></td>
                        <td>{e.exercicio}</td>
                        <td>{e.periodo ?? "ANUAL"}</td>
                        <td><span className={`status-chip ${e.status === "validado" ? "pago" : "rascunho"}`}>{e.status}</span></td>
                        <td style={{ color: e.inconsistencias > 0 ? "var(--color-danger)" : undefined }}>{e.inconsistencias}</td>
                        <td>{new Date(e.created_at).toLocaleString("pt-BR")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={histPage <= 1} onClick={() => setHistPage(histPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Pág {histPage} de {Math.max(1, Math.ceil(historico.total / 20))}</span>
                <button disabled={histPage >= Math.ceil(historico.total / 20)} onClick={() => setHistPage(histPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── XML / ONDA 19 ──────────────────────────────────────────────────── */}
      {tab === "xml" && (
        <div>
          <div style={{ background: "var(--color-surface-raised)", padding: "0.75rem 1rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.82rem" }}>
            <strong>Onda 19 — Fase 1:</strong> Geração de XML estruturado + validação local contra XSD inline.
            O XML gerado pode ser baixado e revisado antes do envio real ao Tesouro Nacional (Fase 2).
          </div>

          {/* Geração */}
          <form onSubmit={gerarXml} className="form-card" style={{ marginBottom: "1.5rem" }}>
            <h3 className="form-title">Gerar e Validar XML</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Tipo *</label>
                <select className="form-select" value={xmlTipo} onChange={(e) => setXmlTipo(e.target.value)}>
                  <option value="finbra">FINBRA — Balanço Orçamentário Anual</option>
                  <option value="rreo">RREO — Relatório Bimestral</option>
                  <option value="rgf">RGF — Relatório Quadrimestral</option>
                </select>
              </div>
              {xmlTipo === "rreo" && (
                <div className="form-group">
                  <label>Bimestre</label>
                  <select className="form-select" value={xmlBimestre} onChange={(e) => setXmlBimestre(e.target.value)}>
                    {[1,2,3,4,5,6].map(b => <option key={b}>{b}</option>)}
                  </select>
                </div>
              )}
              {xmlTipo === "rgf" && (
                <div className="form-group">
                  <label>Quadrimestre</label>
                  <select className="form-select" value={xmlQuad} onChange={(e) => setXmlQuad(e.target.value)}>
                    {[1,2,3].map(q => <option key={q}>{q}</option>)}
                  </select>
                </div>
              )}
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={xmlLoading}>
                {xmlLoading ? "Gerando..." : "Gerar XML"}
              </button>
              {xmlResult && (
                <button type="button" className="btn btn-secondary" onClick={() => downloadXml(xmlTipo)}>
                  ⬇ Download XML
                </button>
              )}
            </div>

            {xmlResult && (
              <div style={{ marginTop: "1rem" }}>
                <div className="stats-grid">
                  <div className={`stat-card ${xmlResult.valido ? "success" : "warning"}`}>
                    <div className="stat-label">Status XSD</div>
                    <div className="stat-value">{xmlResult.valido ? "✓ Válido" : "✗ Inválido"}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Erros XSD</div>
                    <div className="stat-value">{xmlResult.erros_xsd?.length ?? 0}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Tamanho</div>
                    <div className="stat-value">{(xmlResult.xml_tamanho_bytes / 1024).toFixed(1)} KB</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">ID Validação</div>
                    <div className="stat-value">#{xmlResult.validacao_id}</div>
                  </div>
                </div>

                {(xmlResult.erros_xsd?.length ?? 0) > 0 && (
                  <div style={{ marginTop: "0.75rem" }}>
                    <h4>Erros XSD</h4>
                    <ul style={{ fontSize: "0.8rem", color: "var(--color-danger)" }}>
                      {xmlResult.erros_xsd.map((e: string, i: number) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}

                {(xmlResult.avisos?.length ?? 0) > 0 && (
                  <div style={{ marginTop: "0.75rem" }}>
                    <h4>Avisos</h4>
                    <ul style={{ fontSize: "0.8rem", color: "var(--color-warning)" }}>
                      {xmlResult.avisos.map((a: string, i: number) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>
                )}

                <details style={{ marginTop: "0.75rem" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>Preview XML</summary>
                  <pre style={{ fontSize: "0.68rem", background: "var(--color-surface-raised)", padding: "0.75rem", borderRadius: 6, overflow: "auto", maxHeight: 300 }}>
                    {xmlResult.xml_preview}
                  </pre>
                </details>
              </div>
            )}
          </form>

          {/* Fase 2 info box */}
          <div style={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border)", borderRadius: 8, padding: "1rem", marginBottom: "1.5rem" }}>
            <h4 style={{ marginBottom: "0.5rem" }}>Fase 2 — Envio Real (não implementado)</h4>
            <p style={{ fontSize: "0.82rem", marginBottom: "0.5rem" }}>
              O endpoint <code>POST /siconfi/envio</code> retorna <strong>501 Not Implemented</strong>.
              Para habilitá-lo é necessário:
            </p>
            <ul style={{ fontSize: "0.82rem", paddingLeft: "1.2rem" }}>
              <li>Credenciais gov.br (usuário SICONFI)</li>
              <li>Certificado ICP-Brasil A1/A3 do gestor responsável</li>
              <li>WSDL do webservice SICONFI (Tesouro Nacional)</li>
              <li>Biblioteca de assinatura XML WS-Security (signxml)</li>
              <li>Mapeamento JSON → XSD validado pelo Tesouro Nacional</li>
            </ul>
          </div>

          {/* Histórico de validações */}
          <h3 className="section-title">Histórico de Validações XML</h3>
          <div className="toolbar">
            <div className="action-row">
              <select className="form-select" value={xmlHistFiltro} onChange={(e) => { setXmlHistFiltro(e.target.value); setXmlHistPage(1); }}>
                <option value="">Todos os tipos</option>
                <option value="finbra">FINBRA</option>
                <option value="rreo">RREO</option>
                <option value="rgf">RGF</option>
              </select>
              <select className="form-select" value={xmlHistValido} onChange={(e) => { setXmlHistValido(e.target.value); setXmlHistPage(1); }}>
                <option value="">Todos</option>
                <option value="true">Válidos</option>
                <option value="false">Com erros</option>
              </select>
              <button className="btn btn-secondary" onClick={loadXmlHistorico}>↻ Atualizar</button>
            </div>
          </div>
          {xmlHistorico && (
            <>
              <div className="table-meta">{xmlHistorico.total} validação(ões)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Tipo</th><th>Exercício</th><th>Período</th><th>Status XSD</th><th>Erros</th><th>Fonte XSD</th><th>Gerado em</th></tr></thead>
                  <tbody>
                    {xmlHistorico.items.map((v) => (
                      <tr key={v.id}>
                        <td>{v.id}</td>
                        <td><span className="status-chip ativo">{v.tipo}</span></td>
                        <td>{v.exercicio}</td>
                        <td>{v.periodo ?? "ANUAL"}</td>
                        <td><span className={`status-chip ${v.valido ? "pago" : "cancelado"}`}>{v.valido ? "válido" : "inválido"}</span></td>
                        <td style={{ color: (v.erros_xsd?.length ?? 0) > 0 ? "var(--color-danger)" : undefined }}>
                          {v.erros_xsd?.length ?? 0}
                        </td>
                        <td><code>{v.xsd_fonte}</code></td>
                        <td>{new Date(v.created_at).toLocaleString("pt-BR")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={xmlHistPage <= 1} onClick={() => setXmlHistPage(xmlHistPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Pág {xmlHistPage} de {Math.max(1, Math.ceil(xmlHistorico.total / 20))}</span>
                <button disabled={xmlHistPage >= Math.ceil(xmlHistorico.total / 20)} onClick={() => setXmlHistPage(xmlHistPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
