"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type Asset = { id: number; tag: string; description: string; classification: string; value: number; status: string };

type Config = {
  id: number;
  asset_id: number;
  data_aquisicao: string;
  valor_aquisicao: number;
  vida_util_meses: number;
  valor_residual: number;
  metodo: string;
  ativo: boolean;
};

type Lancamento = {
  id: number;
  asset_id: number;
  periodo: string;
  valor_depreciado: number;
  depreciacao_acumulada: number;
  valor_contabil_liquido: number;
  criado_por_id: number | null;
};

type LancamentoItem = {
  periodo: string;
  valor_depreciado: number;
  depreciacao_acumulada: number;
  valor_contabil_liquido: number;
};

type Relatorio = {
  asset_id: number;
  asset_tag: string;
  asset_description: string;
  valor_aquisicao: number;
  valor_residual: number;
  vida_util_meses: number;
  metodo: string;
  data_aquisicao: string;
  lancamentos: LancamentoItem[];
};

type DashData = {
  periodo: string;
  total_bens_configurados: number;
  total_bens_com_lancamento: number;
  total_depreciado_periodo: number;
  total_depreciacao_acumulada: number;
  total_valor_contabil_liquido: number;
  total_valor_aquisicao: number;
  top_bens: {
    asset_id: number;
    asset_tag: string;
    asset_description: string;
    valor_depreciado: number;
    valor_contabil_liquido: number;
  }[];
};

// ── Helpers ────────────────────────────────────────────────────────────────

function messageFrom(e: unknown) {
  return e instanceof Error ? e.message : "Falha na operação";
}

function periodoAtual() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const fmt = (v: number, decimals = 2) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DepreciacaoPage() {
  const { toast } = useToast();
  const [tab, setTab] = useState<"dashboard" | "config" | "calcular" | "relatorio">("dashboard");

  const [periodo, setPeriodo] = useState(periodoAtual);
  const [dashData, setDashData] = useState<DashData | null>(null);

  const [assets, setAssets] = useState<Asset[]>([]);
  const [configs, setConfigs] = useState<Paged<Config> | null>(null);
  const [configPage, setConfigPage] = useState(1);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [cfgAssetId, setCfgAssetId] = useState("");
  const [cfgDataAq, setCfgDataAq] = useState("");
  const [cfgValorAq, setCfgValorAq] = useState("");
  const [cfgVidaUtil, setCfgVidaUtil] = useState("60");
  const [cfgResidual, setCfgResidual] = useState("0");
  const [cfgMetodo, setCfgMetodo] = useState("linear");

  const [calcPeriodo, setCalcPeriodo] = useState(periodoAtual);
  const [calcAssetId, setCalcAssetId] = useState("");
  const [calcResult, setCalcResult] = useState<Record<string, unknown> | null>(null);
  const [lancamentos, setLancamentos] = useState<Paged<Lancamento> | null>(null);
  const [lancPage, setLancPage] = useState(1);
  const [lancFilterPeriodo, setLancFilterPeriodo] = useState("");
  const [lancFilterAsset, setLancFilterAsset] = useState("");

  const [relAssetId, setRelAssetId] = useState("");
  const [relatorio, setRelatorio] = useState<Relatorio | null>(null);

  // ── Load ───────────────────────────────────────────────────────────────────

  async function loadAssets() {
    try {
      const d = await authJson("/patrimony/assets?size=200&status=ativo");
      setAssets(d?.items ?? []);
    } catch {}
  }

  async function loadDashboard() {
    if (!periodo) return;
    try {
      const d = await authJson(`/depreciacao/dashboard?periodo=${periodo}`);
      setDashData(d);
    } catch (e) {
      toast("Erro ao carregar dashboard: " + messageFrom(e), "error");
    }
  }

  async function loadConfigs() {
    try {
      const d = await authJson(`/depreciacao/config?page=${configPage}&size=30`);
      setConfigs(d);
    } catch (e) {
      toast("Erro: " + messageFrom(e), "error");
    }
  }

  async function loadLancamentos() {
    try {
      const params = new URLSearchParams({ page: String(lancPage), size: "30" });
      if (lancFilterPeriodo) params.set("periodo", lancFilterPeriodo);
      if (lancFilterAsset) params.set("asset_id", lancFilterAsset);
      const d = await authJson(`/depreciacao/lancamentos?${params}`);
      setLancamentos(d);
    } catch (e) {
      toast("Erro: " + messageFrom(e), "error");
    }
  }

  async function loadRelatorio() {
    if (!relAssetId) return;
    try {
      const d = await authJson(`/depreciacao/relatorio/${relAssetId}`);
      setRelatorio(d);
    } catch (e) {
      toast("Erro ao carregar relatório: " + messageFrom(e), "error");
      setRelatorio(null);
    }
  }

  useEffect(() => { loadAssets(); }, []);
  useEffect(() => { if (tab === "dashboard") loadDashboard(); }, [tab, periodo]);
  useEffect(() => { if (tab === "config") loadConfigs(); }, [tab, configPage]);
  useEffect(() => {
    if (tab === "calcular") loadLancamentos();
  }, [tab, lancPage, lancFilterPeriodo, lancFilterAsset]);

  // ── Criar Config ───────────────────────────────────────────────────────────

  async function submitConfig(e: FormEvent) {
    e.preventDefault();
    try {
      await authJson("/depreciacao/config", {
        method: "POST",
        body: JSON.stringify({
          asset_id: Number(cfgAssetId),
          data_aquisicao: cfgDataAq,
          valor_aquisicao: parseFloat(cfgValorAq),
          vida_util_meses: parseInt(cfgVidaUtil),
          valor_residual: parseFloat(cfgResidual),
          metodo: cfgMetodo,
        }),
      });
      toast("Configuração criada com sucesso!");
      setShowConfigForm(false);
      loadConfigs();
    } catch (e) {
      toast("Erro: " + messageFrom(e), "error");
    }
  }

  // ── Calcular ────────────────────────────────────────────────────────────────

  async function submitCalcular(e: FormEvent) {
    e.preventDefault();
    try {
      const body: Record<string, unknown> = { periodo: calcPeriodo };
      if (calcAssetId) body.asset_id = Number(calcAssetId);
      const d = await authJson("/depreciacao/calcular", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setCalcResult(d);
      toast(`Cálculo concluído: ${d.criados} criados, ${d.atualizados} atualizados.`);
      loadLancamentos();
    } catch (e) {
      toast("Erro: " + messageFrom(e), "error");
    }
  }

  function exportRelCsv() {
    if (!relAssetId) return;
    const safeId = String(relAssetId).replace(/[^0-9]/g, "");
    window.location.href = `/api/proxy/depreciacao/relatorio/${safeId}/csv`;
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <main className="page-content">
      <h1 className="page-title">Depreciação Patrimonial</h1>

      <div className="tabs">
        {(["dashboard", "config", "calcular", "relatorio"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "tab active" : "tab"}>
            {t === "dashboard" ? "Dashboard" :
             t === "config" ? "Configuração" :
             t === "calcular" ? "Calcular / Lançamentos" : "Relatório por Bem"}
          </button>
        ))}
      </div>

      {/* ── DASHBOARD ───────────────────────────────────────────────────────── */}
      {tab === "dashboard" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <input
                type="month" value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className="filter-input"
              />
              <button className="btn btn-secondary" onClick={loadDashboard}>Atualizar</button>
            </div>
          </div>

          {dashData && (
            <>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Bens Configurados</div>
                  <div className="kpi-value">{dashData.total_bens_configurados}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Com Lançamento</div>
                  <div className="kpi-value">{dashData.total_bens_com_lancamento}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Depreciado no Período</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_depreciado_periodo)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Depreciação Acumulada</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_depreciacao_acumulada)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Valor Contábil Líquido</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_valor_contabil_liquido)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Valor de Aquisição Total</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_valor_aquisicao)}</div>
                </div>
              </div>

              {dashData.top_bens.length > 0 && (
                <div style={{ marginTop: "1.5rem" }}>
                  <h3 className="section-title">Top bens por depreciação no período</h3>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Tombamento</th>
                          <th>Descrição</th>
                          <th>Deprec. Período</th>
                          <th>VCL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashData.top_bens.map((b) => (
                          <tr key={b.asset_id}>
                            <td>{b.asset_tag}</td>
                            <td>{b.asset_description}</td>
                            <td>R$ {fmt(b.valor_depreciado)}</td>
                            <td>R$ {fmt(b.valor_contabil_liquido)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── CONFIG ──────────────────────────────────────────────────────────── */}
      {tab === "config" && (
        <div>
          <div className="toolbar">
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => setShowConfigForm(!showConfigForm)}>
                + Nova Configuração
              </button>
            </div>
          </div>

          {showConfigForm && (
            <form onSubmit={submitConfig} className="form-card">
              <h3 className="form-title">Configurar Depreciação de Bem</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Bem Patrimonial *</label>
                  <select value={cfgAssetId} onChange={(e) => setCfgAssetId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>{a.tag} — {a.description}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Data de Aquisição *</label>
                  <input type="date" value={cfgDataAq} onChange={(e) => setCfgDataAq(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Valor de Aquisição (R$) *</label>
                  <input type="number" step="0.01" value={cfgValorAq} onChange={(e) => setCfgValorAq(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Vida Útil (meses) *</label>
                  <input type="number" value={cfgVidaUtil} onChange={(e) => setCfgVidaUtil(e.target.value)} required className="form-input" placeholder="60 = 5 anos" />
                </div>
                <div className="form-group">
                  <label>Valor Residual (R$)</label>
                  <input type="number" step="0.01" value={cfgResidual} onChange={(e) => setCfgResidual(e.target.value)} className="form-input" />
                </div>
                <div className="form-group">
                  <label>Método *</label>
                  <select value={cfgMetodo} onChange={(e) => setCfgMetodo(e.target.value)} className="form-select">
                    <option value="linear">Linear (NBCASP padrão)</option>
                    <option value="saldo_decrescente">Saldo Decrescente</option>
                  </select>
                </div>
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)" }}>
                Prazos NBCASP: Veículos 60m · Móveis 120m · Equipamentos TI 60m · Máquinas 120m · Imóveis 300m
              </p>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Salvar</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowConfigForm(false)}>Cancelar</button>
              </div>
            </form>
          )}

          {configs && (
            <>
              <div className="table-meta">{configs.total} configuração(ões)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Bem</th>
                      <th>Data Aquisição</th>
                      <th>Valor Aquisição</th>
                      <th>Vida Útil</th>
                      <th>Residual</th>
                      <th>Método</th>
                      <th>Ativo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {configs.items.map((c) => {
                      const a = assets.find((x) => x.id === c.asset_id);
                      return (
                        <tr key={c.id}>
                          <td>{a ? `${a.tag} — ${a.description}` : c.asset_id}</td>
                          <td>{c.data_aquisicao}</td>
                          <td>R$ {fmt(c.valor_aquisicao)}</td>
                          <td>{c.vida_util_meses}m ({(c.vida_util_meses / 12).toFixed(0)} anos)</td>
                          <td>R$ {fmt(c.valor_residual)}</td>
                          <td>{c.metodo}</td>
                          <td>
                            <span className={`status-chip ${c.ativo ? "pago" : "baixado"}`}>
                              {c.ativo ? "Sim" : "Não"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={configPage <= 1} onClick={() => setConfigPage(configPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Pág {configPage} de {Math.max(1, Math.ceil(configs.total / 30))}</span>
                <button disabled={configPage >= Math.ceil(configs.total / 30)} onClick={() => setConfigPage(configPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── CALCULAR ────────────────────────────────────────────────────────── */}
      {tab === "calcular" && (
        <div>
          <form onSubmit={submitCalcular} className="form-card" style={{ marginBottom: "1.5rem" }}>
            <h3 className="form-title">Calcular Depreciação</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Período (YYYY-MM) *</label>
                <input type="month" value={calcPeriodo} onChange={(e) => setCalcPeriodo(e.target.value)} required className="form-input" />
              </div>
              <div className="form-group">
                <label>Bem Específico (opcional)</label>
                <select value={calcAssetId} onChange={(e) => setCalcAssetId(e.target.value)} className="form-select">
                  <option value="">Todos os bens configurados</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>{a.tag} — {a.description}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">Calcular e Registrar</button>
            </div>
            {calcResult && (
              <div className="alert alert-success" style={{ marginTop: "0.75rem" }}>
                Período: <strong>{String(calcResult.periodo)}</strong> — criados: {String(calcResult.criados)},
                atualizados: {String(calcResult.atualizados)},
                total depreciado: <strong>R$ {fmt(Number(calcResult.total_depreciado))}</strong>
              </div>
            )}
          </form>

          <h3 className="section-title">Lançamentos</h3>
          <div className="toolbar">
            <div className="filter-row">
              <input type="month" value={lancFilterPeriodo}
                onChange={(e) => { setLancFilterPeriodo(e.target.value); setLancPage(1); }}
                className="filter-input" placeholder="Filtrar período" />
              <select value={lancFilterAsset}
                onChange={(e) => { setLancFilterAsset(e.target.value); setLancPage(1); }}
                className="filter-select">
                <option value="">Todos os bens</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>{a.tag}</option>
                ))}
              </select>
            </div>
          </div>

          {lancamentos && (
            <>
              <div className="table-meta">{lancamentos.total} lançamento(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Bem</th>
                      <th>Período</th>
                      <th>Valor Depreciado</th>
                      <th>Deprec. Acumulada</th>
                      <th>VCL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lancamentos.items.map((l) => {
                      const a = assets.find((x) => x.id === l.asset_id);
                      return (
                        <tr key={l.id}>
                          <td>{a ? `${a.tag}` : l.asset_id}</td>
                          <td>{l.periodo}</td>
                          <td>R$ {fmt(l.valor_depreciado)}</td>
                          <td>R$ {fmt(l.depreciacao_acumulada)}</td>
                          <td>R$ {fmt(l.valor_contabil_liquido)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={lancPage <= 1} onClick={() => setLancPage(lancPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Pág {lancPage} de {Math.max(1, Math.ceil(lancamentos.total / 30))}</span>
                <button disabled={lancPage >= Math.ceil(lancamentos.total / 30)} onClick={() => setLancPage(lancPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── RELATÓRIO ───────────────────────────────────────────────────────── */}
      {tab === "relatorio" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select value={relAssetId} onChange={(e) => setRelAssetId(e.target.value)} className="filter-select">
                <option value="">Selecione o bem...</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>{a.tag} — {a.description}</option>
                ))}
              </select>
              <button className="btn btn-secondary" onClick={loadRelatorio}>Ver relatório</button>
            </div>
            <div className="action-row">
              {relatorio && (
                <button className="btn btn-secondary" onClick={exportRelCsv}>↓ CSV</button>
              )}
            </div>
          </div>

          {relatorio && (
            <>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Valor de Aquisição</div>
                  <div className="kpi-value">R$ {fmt(relatorio.valor_aquisicao)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Valor Residual</div>
                  <div className="kpi-value">R$ {fmt(relatorio.valor_residual)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Vida Útil</div>
                  <div className="kpi-value">{relatorio.vida_util_meses}m</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Método</div>
                  <div className="kpi-value">{relatorio.metodo}</div>
                </div>
                {relatorio.lancamentos.length > 0 && (
                  <>
                    <div className="kpi-card">
                      <div className="kpi-label">VCL Atual</div>
                      <div className="kpi-value">
                        R$ {fmt(relatorio.lancamentos[relatorio.lancamentos.length - 1].valor_contabil_liquido)}
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">Deprec. Acumulada</div>
                      <div className="kpi-value">
                        R$ {fmt(relatorio.lancamentos[relatorio.lancamentos.length - 1].depreciacao_acumulada)}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {relatorio.lancamentos.length > 0 && (
                <>
                  <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
                    Percentual depreciado ({relatorio.lancamentos.length} lançamentos)
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${Math.min(100, (relatorio.lancamentos[relatorio.lancamentos.length - 1].depreciacao_acumulada /
                          (relatorio.valor_aquisicao - relatorio.valor_residual)) * 100)}%`,
                      }}
                    />
                  </div>
                </>
              )}

              <div className="table-responsive" style={{ marginTop: "1.25rem" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Período</th>
                      <th>Valor Depreciado</th>
                      <th>Deprec. Acumulada</th>
                      <th>VCL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {relatorio.lancamentos.map((l) => (
                      <tr key={l.periodo}>
                        <td>{l.periodo}</td>
                        <td>R$ {fmt(l.valor_depreciado)}</td>
                        <td>R$ {fmt(l.depreciacao_acumulada)}</td>
                        <td>R$ {fmt(l.valor_contabil_liquido)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
