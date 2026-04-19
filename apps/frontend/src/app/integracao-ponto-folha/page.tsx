"use client";

import { FormEvent, useEffect, useState } from "react";
import { authJson } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type Employee = { id: number; name: string; cpf: string };

type Config = {
  id: number;
  employee_id: number;
  desconto_falta_diaria: number | null;
  percentual_hora_extra: number;
  desconto_atraso: boolean;
  ativo: boolean;
};

type IntegrarResultado = {
  employee_id: number;
  employee_name?: string;
  status: "ok" | "pulado" | "erro";
  motivo?: string;
  faltas_descontadas?: number;
  horas_extras_creditadas?: number;
  valor_desconto_faltas?: number;
  valor_desconto_atrasos?: number;
  valor_credito_horas_extras?: number;
  eventos_gerados?: number;
};

type IntegrarResult = {
  periodo: string;
  total_ok: number;
  total_pulados: number;
  total_erros: number;
  resultados: IntegrarResultado[];
};

type PreviewResultado = {
  employee_id: number;
  employee_name: string;
  total_faltas_injustificadas: number;
  total_horas_extras: number;
  total_minutos_atraso: number;
  desconto_previsto_faltas: number;
  desconto_previsto_atrasos: number;
  credito_previsto_he: number;
  ja_integrado: boolean;
};

type Log = {
  id: number;
  employee_id: number;
  periodo: string;
  faltas_descontadas: number;
  horas_extras_creditadas: number;
  valor_desconto_faltas: number;
  valor_desconto_atrasos: number;
  valor_credito_horas_extras: number;
  status: string;
  created_at: string;
};

type DashData = {
  periodo: string;
  total_configurados: number;
  total_integrados: number;
  total_faltas_descontadas: number;
  total_horas_extras_creditadas: number;
  total_desconto_faltas: number;
  total_desconto_atrasos: number;
  total_credito_horas_extras: number;
  saldo_liquido: number;
  servidores: {
    employee_id: number;
    employee_name: string;
    faltas_descontadas: number;
    horas_extras_creditadas: number;
    valor_desconto_faltas: number;
    valor_desconto_atrasos: number;
    valor_credito_horas_extras: number;
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

const fmt = (v: number) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ── Page ──────────────────────────────────────────────────────────────────────

export default function IntegracaoPontoFolhaPage() {
  const [msg, setMsg] = useState("");
  const isError = msg.toLowerCase().includes("erro") || msg.toLowerCase().includes("falha");
  const [tab, setTab] = useState<"dashboard" | "config" | "integrar" | "logs">("dashboard");

  const [periodo, setPeriodo] = useState(periodoAtual);
  const [dashData, setDashData] = useState<DashData | null>(null);

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [configs, setConfigs] = useState<Paged<Config> | null>(null);
  const [configPage, setConfigPage] = useState(1);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [cfgEmpId, setCfgEmpId] = useState("");
  const [cfgPctHe, setCfgPctHe] = useState("50");
  const [cfgDescAtraso, setCfgDescAtraso] = useState(true);
  const [cfgDescontoFaltaDiaria, setCfgDescontoFaltaDiaria] = useState("");

  const [integrarPeriodo, setIntegrarPeriodo] = useState(periodoAtual);
  const [integrarEmpId, setIntegrarEmpId] = useState("");
  const [integrarForce, setIntegrarForce] = useState(false);
  const [integrarResult, setIntegrarResult] = useState<IntegrarResult | null>(null);
  const [previewResult, setPreviewResult] = useState<{ periodo: string; resultados: PreviewResultado[] } | null>(null);
  const [previewPeriodo, setPreviewPeriodo] = useState(periodoAtual);
  const [previewEmpId, setPreviewEmpId] = useState("");

  const [logs, setLogs] = useState<Paged<Log> | null>(null);
  const [logPage, setLogPage] = useState(1);
  const [logFilterPeriodo, setLogFilterPeriodo] = useState("");
  const [logFilterEmp, setLogFilterEmp] = useState("");

  // ── Load ───────────────────────────────────────────────────────────────────

  async function loadEmployees() {
    try {
      const d = await authJson("/hr/employees?size=200");
      setEmployees(d?.items ?? []);
    } catch {}
  }

  async function loadDashboard() {
    if (!periodo) return;
    try {
      const d = await authJson(`/integracao-ponto-folha/dashboard?periodo=${periodo}`);
      setDashData(d);
    } catch (e) {
      setMsg("Erro ao carregar dashboard: " + messageFrom(e));
    }
  }

  async function loadConfigs() {
    try {
      const d = await authJson(`/integracao-ponto-folha/config?page=${configPage}&size=30`);
      setConfigs(d);
    } catch (e) {
      setMsg("Erro: " + messageFrom(e));
    }
  }

  async function loadLogs() {
    try {
      const params = new URLSearchParams({ page: String(logPage), size: "30" });
      if (logFilterPeriodo) params.set("periodo", logFilterPeriodo);
      if (logFilterEmp) params.set("employee_id", logFilterEmp);
      const d = await authJson(`/integracao-ponto-folha/logs?${params}`);
      setLogs(d);
    } catch (e) {
      setMsg("Erro: " + messageFrom(e));
    }
  }

  useEffect(() => { loadEmployees(); }, []);
  useEffect(() => { if (tab === "dashboard") loadDashboard(); }, [tab, periodo]);
  useEffect(() => { if (tab === "config") loadConfigs(); }, [tab, configPage]);
  useEffect(() => { if (tab === "logs") loadLogs(); }, [tab, logPage, logFilterPeriodo, logFilterEmp]);

  // ── Criar Config ───────────────────────────────────────────────────────────

  async function submitConfig(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await authJson("/integracao-ponto-folha/config", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(cfgEmpId),
          desconto_falta_diaria: cfgDescontoFaltaDiaria ? parseFloat(cfgDescontoFaltaDiaria) : null,
          percentual_hora_extra: parseFloat(cfgPctHe),
          desconto_atraso: cfgDescAtraso,
        }),
      });
      setMsg("Configuração criada!");
      setShowConfigForm(false);
      loadConfigs();
    } catch (e) {
      setMsg("Erro: " + messageFrom(e));
    }
  }

  // ── Preview ────────────────────────────────────────────────────────────────

  async function submitPreview(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    setPreviewResult(null);
    try {
      const body: Record<string, unknown> = { periodo: previewPeriodo };
      if (previewEmpId) body.employee_id = Number(previewEmpId);
      const d = await authJson("/integracao-ponto-folha/preview", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPreviewResult(d);
    } catch (e) {
      setMsg("Erro no preview: " + messageFrom(e));
    }
  }

  // ── Integrar ───────────────────────────────────────────────────────────────

  async function submitIntegrar(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    setIntegrarResult(null);
    try {
      const body: Record<string, unknown> = { periodo: integrarPeriodo, force: integrarForce };
      if (integrarEmpId) body.employee_id = Number(integrarEmpId);
      const d = await authJson("/integracao-ponto-folha/integrar", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setIntegrarResult(d);
      setMsg(`Integração concluída: ${d.total_ok} OK, ${d.total_pulados} pulados, ${d.total_erros} erros`);
      if (tab === "logs") loadLogs();
    } catch (e) {
      setMsg("Erro: " + messageFrom(e));
    }
  }

  function exportCsv() {
    if (!logFilterPeriodo) {
      setMsg("Erro: informe um período para exportar CSV");
      return;
    }
    const safePeriodo = logFilterPeriodo.replace(/[^0-9-]/g, "");
    window.location.href = `/api/proxy/integracao-ponto-folha/logs/csv?periodo=${safePeriodo}`;
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <main className="page-content">
      <h1 className="page-title">Integração Ponto → Folha</h1>

      {msg && (
        <div className={`alert ${isError ? "alert-error" : "alert-success"}`}>
          {msg}
          <button onClick={() => setMsg("")} className="alert-close">×</button>
        </div>
      )}

      <div className="tabs">
        {(["dashboard", "config", "integrar", "logs"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "tab active" : "tab"}>
            {t === "dashboard" ? "Dashboard" :
             t === "config" ? "Configuração" :
             t === "integrar" ? "Integrar" : "Logs"}
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
                  <div className="kpi-label">Configurados</div>
                  <div className="kpi-value">{dashData.total_configurados}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Integrados no Período</div>
                  <div className="kpi-value">{dashData.total_integrados}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Faltas Descontadas</div>
                  <div className="kpi-value">{dashData.total_faltas_descontadas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">HE Creditadas</div>
                  <div className="kpi-value">{dashData.total_horas_extras_creditadas}h</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Total Desc. Faltas</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_desconto_faltas)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Total Desc. Atrasos</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_desconto_atrasos)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Crédito HE</div>
                  <div className="kpi-value">R$ {fmt(dashData.total_credito_horas_extras)}</div>
                </div>
                <div className={`kpi-card ${dashData.saldo_liquido >= 0 ? "" : "kpi-card--alert"}`}>
                  <div className="kpi-label">Saldo Líquido (HE − Desc)</div>
                  <div className="kpi-value">R$ {fmt(dashData.saldo_liquido)}</div>
                </div>
              </div>

              {dashData.servidores.length > 0 && (
                <div style={{ marginTop: "1.5rem" }}>
                  <h3 className="section-title">Detalhamento por servidor</h3>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Servidor</th>
                          <th>Faltas</th>
                          <th>HE (h)</th>
                          <th>Desc. Faltas</th>
                          <th>Desc. Atrasos</th>
                          <th>Créd. HE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashData.servidores.map((s) => (
                          <tr key={s.employee_id}>
                            <td>{s.employee_name}</td>
                            <td>{s.faltas_descontadas}</td>
                            <td>{s.horas_extras_creditadas}</td>
                            <td>R$ {fmt(s.valor_desconto_faltas)}</td>
                            <td>R$ {fmt(s.valor_desconto_atrasos)}</td>
                            <td>R$ {fmt(s.valor_credito_horas_extras)}</td>
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
              <h3 className="form-title">Configurar Regras de Integração</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Servidor *</label>
                  <select value={cfgEmpId} onChange={(e) => setCfgEmpId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {employees.map((e) => (
                      <option key={e.id} value={e.id}>{e.name} — {e.cpf}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>% Adicional Hora Extra</label>
                  <input type="number" step="0.01" value={cfgPctHe}
                    onChange={(e) => setCfgPctHe(e.target.value)} className="form-input"
                    placeholder="50 = 50% | 100 = 100%" />
                </div>
                <div className="form-group">
                  <label>Desconto Falta Diária (R$)</label>
                  <input type="number" step="0.01" value={cfgDescontoFaltaDiaria}
                    onChange={(e) => setCfgDescontoFaltaDiaria(e.target.value)} className="form-input"
                    placeholder="Vazio = proporcional ao salário" />
                  <small>Se vazio: desconto = salário / dias úteis × nº faltas</small>
                </div>
                <div className="form-group" style={{ alignSelf: "end" }}>
                  <label style={{ display: "flex", gap: "0.5rem", alignItems: "center", cursor: "pointer" }}>
                    <input type="checkbox" checked={cfgDescAtraso}
                      onChange={(e) => setCfgDescAtraso(e.target.checked)} />
                    Desconto proporcional por atrasos
                  </label>
                </div>
              </div>
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
                      <th>Servidor</th>
                      <th>% HE</th>
                      <th>Desc. Falta Diária</th>
                      <th>Desc. Atraso</th>
                      <th>Ativo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {configs.items.map((c) => {
                      const emp = employees.find((x) => x.id === c.employee_id);
                      return (
                        <tr key={c.id}>
                          <td>{emp ? emp.name : c.employee_id}</td>
                          <td>{c.percentual_hora_extra}%</td>
                          <td>{c.desconto_falta_diaria != null ? `R$ ${fmt(c.desconto_falta_diaria)}` : "Proporcional"}</td>
                          <td>{c.desconto_atraso ? "Sim" : "Não"}</td>
                          <td>
                            <span className={`status-chip ${c.ativo ? "pago" : "baixado"}`}>
                              {c.ativo ? "Ativo" : "Inativo"}
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

      {/* ── INTEGRAR ────────────────────────────────────────────────────────── */}
      {tab === "integrar" && (
        <div>
          {/* Preview */}
          <form onSubmit={submitPreview} className="form-card" style={{ marginBottom: "1.5rem" }}>
            <h3 className="form-title">Preview (dry-run)</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.5rem" }}>
              Simula o que seria gerado sem persistir dados.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label>Período *</label>
                <input type="month" value={previewPeriodo} onChange={(e) => setPreviewPeriodo(e.target.value)} required className="form-input" />
              </div>
              <div className="form-group">
                <label>Servidor (opcional)</label>
                <select value={previewEmpId} onChange={(e) => setPreviewEmpId(e.target.value)} className="form-select">
                  <option value="">Todos com configuração ativa</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-secondary">Simular</button>
            </div>

            {previewResult && (
              <div style={{ marginTop: "1rem" }}>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Servidor</th>
                        <th>Faltas Inj.</th>
                        <th>HE (h)</th>
                        <th>Min. Atraso</th>
                        <th>Desc. Faltas</th>
                        <th>Desc. Atrasos</th>
                        <th>Créd. HE</th>
                        <th>Já Integrado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewResult.resultados.map((r) => (
                        <tr key={r.employee_id}>
                          <td>{r.employee_name}</td>
                          <td>{r.total_faltas_injustificadas}</td>
                          <td>{r.total_horas_extras}</td>
                          <td>{r.total_minutos_atraso}</td>
                          <td>R$ {fmt(r.desconto_previsto_faltas)}</td>
                          <td>R$ {fmt(r.desconto_previsto_atrasos)}</td>
                          <td>R$ {fmt(r.credito_previsto_he)}</td>
                          <td>
                            <span className={`status-chip ${r.ja_integrado ? "ativo" : "rascunho"}`}>
                              {r.ja_integrado ? "Sim" : "Não"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </form>

          {/* Integrar */}
          <form onSubmit={submitIntegrar} className="form-card">
            <h3 className="form-title">Executar Integração</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.5rem" }}>
              Persiste os descontos e créditos como <strong>PayrollEvents</strong> na folha.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label>Período *</label>
                <input type="month" value={integrarPeriodo} onChange={(e) => setIntegrarPeriodo(e.target.value)} required className="form-input" />
              </div>
              <div className="form-group">
                <label>Servidor (opcional)</label>
                <select value={integrarEmpId} onChange={(e) => setIntegrarEmpId(e.target.value)} className="form-select">
                  <option value="">Todos com configuração ativa</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ alignSelf: "end" }}>
                <label style={{ display: "flex", gap: "0.5rem", alignItems: "center", cursor: "pointer" }}>
                  <input type="checkbox" checked={integrarForce}
                    onChange={(e) => setIntegrarForce(e.target.checked)} />
                  <span><strong>Forçar</strong> (re-processa já integrados)</span>
                </label>
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">Integrar</button>
            </div>

            {integrarResult && (
              <div style={{ marginTop: "1rem" }}>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Servidor</th>
                        <th>Status</th>
                        <th>Faltas</th>
                        <th>HE (h)</th>
                        <th>Desc. Faltas</th>
                        <th>Créd. HE</th>
                        <th>Eventos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {integrarResult.resultados.map((r, i) => {
                        const emp = employees.find((x) => x.id === r.employee_id);
                        return (
                          <tr key={i}>
                            <td>{r.employee_name ?? (emp ? emp.name : r.employee_id)}</td>
                            <td>
                              <span className={`status-chip ${r.status === "ok" ? "pago" : r.status === "pulado" ? "rascunho" : "cancelado"}`}>
                                {r.status}
                              </span>
                            </td>
                            <td>{r.faltas_descontadas ?? "—"}</td>
                            <td>{r.horas_extras_creditadas ?? "—"}</td>
                            <td>{r.valor_desconto_faltas != null ? `R$ ${fmt(r.valor_desconto_faltas)}` : "—"}</td>
                            <td>{r.valor_credito_horas_extras != null ? `R$ ${fmt(r.valor_credito_horas_extras)}` : "—"}</td>
                            <td>{r.eventos_gerados ?? "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </form>
        </div>
      )}

      {/* ── LOGS ────────────────────────────────────────────────────────────── */}
      {tab === "logs" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <input type="month" value={logFilterPeriodo}
                onChange={(e) => { setLogFilterPeriodo(e.target.value); setLogPage(1); }}
                className="filter-input" placeholder="Filtrar período" />
              <select value={logFilterEmp}
                onChange={(e) => { setLogFilterEmp(e.target.value); setLogPage(1); }}
                className="filter-select">
                <option value="">Todos os servidores</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </div>
            <div className="action-row">
              <button className="btn btn-secondary" onClick={exportCsv}>↓ CSV</button>
            </div>
          </div>

          {logs && (
            <>
              <div className="table-meta">{logs.total} log(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Servidor</th>
                      <th>Período</th>
                      <th>Faltas</th>
                      <th>HE (h)</th>
                      <th>Desc. Faltas</th>
                      <th>Desc. Atrasos</th>
                      <th>Créd. HE</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.items.map((l) => {
                      const emp = employees.find((x) => x.id === l.employee_id);
                      return (
                        <tr key={l.id}>
                          <td>{emp ? emp.name : l.employee_id}</td>
                          <td>{l.periodo}</td>
                          <td>{l.faltas_descontadas}</td>
                          <td>{l.horas_extras_creditadas}</td>
                          <td>R$ {fmt(l.valor_desconto_faltas)}</td>
                          <td>R$ {fmt(l.valor_desconto_atrasos)}</td>
                          <td>R$ {fmt(l.valor_credito_horas_extras)}</td>
                          <td>
                            <span className={`status-chip ${l.status === "ok" ? "pago" : "cancelado"}`}>
                              {l.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={logPage <= 1} onClick={() => setLogPage(logPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Pág {logPage} de {Math.max(1, Math.ceil(logs.total / 30))}</span>
                <button disabled={logPage >= Math.ceil(logs.total / 30)} onClick={() => setLogPage(logPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
