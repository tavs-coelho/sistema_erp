"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { authJson } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────

type Paged<T> = { total: number; page: number; size: number; items: T[] };

type Employee = { id: number; name: string; cpf: string; job_title: string };

type Escala = {
  id: number;
  employee_id: number;
  horas_dia: number;
  dias_semana: string;
  hora_entrada: string;
  hora_saida: string;
  hora_inicio_intervalo: string;
  hora_fim_intervalo: string;
};

type Registro = {
  id: number;
  employee_id: number;
  data: string;
  tipo_registro: string;
  hora_registro: string;
  origem: string;
  observacoes: string;
};

type DiaFrequencia = {
  data: string;
  dia_semana: string;
  dia_util: boolean;
  entrada: string | null;
  saida: string | null;
  inicio_intervalo: string | null;
  fim_intervalo: string | null;
  horas_trabalhadas: number;
  horas_extras: number;
  minutos_atraso: number;
  falta: boolean;
  abonado: boolean;
  abono_tipo: string | null;
  status_dia: string;
};

type Folha = {
  employee_id: number;
  employee_name: string;
  periodo: string;
  total_dias_uteis: number;
  total_presencas: number;
  total_faltas: number;
  total_faltas_abonadas: number;
  total_horas_trabalhadas: number;
  total_horas_extras: number;
  total_minutos_atraso: number;
  dias: DiaFrequencia[];
};

type Abono = {
  id: number;
  employee_id: number;
  data: string;
  tipo: string;
  motivo: string;
  status: string;
  aprovado_por_id: number | null;
};

type Dashboard = {
  periodo: string;
  total_servidores: number;
  total_presencas: number;
  total_faltas: number;
  total_faltas_abonadas: number;
  total_horas_extras: number;
  total_minutos_atraso: number;
  abonos_pendentes: number;
  servidores_com_falta: { employee_id: number; employee_name: string; faltas: number }[];
};

// ── Helpers ────────────────────────────────────────────────────────────────

function messageFrom(e: unknown) { return e instanceof Error ? e.message : "Falha na operação"; }

const STATUS_CHIP: Record<string, string> = {
  presente: "pago",
  falta: "baixado",
  falta_abonada: "pendente",
  folga: "pendente",
  fim_semana: "pendente",
};

const ABONO_CHIP: Record<string, string> = {
  pendente: "pendente",
  aprovado: "pago",
  rejeitado: "baixado",
};

const TIPOS_REGISTRO = ["entrada", "saida", "inicio_intervalo", "fim_intervalo"];
const TIPOS_ABONO = ["falta", "atraso", "folga_compensacao"];

function periodoAtual() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth(); // 0-based
  if (m === 0) return `${y - 1}-12`;
  return `${y}-${String(m).padStart(2, "0")}`;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PontoPage() {
  const { toast } = useToast();
  const [tab, setTab] = useState<"dashboard" | "registros" | "folha" | "abonos">("dashboard");

  // Shared
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [periodo, setPeriodo] = useState(periodoAtual);
  const [selectedEmployee, setSelectedEmployee] = useState<number | "">("");

  // Dashboard
  const [dash, setDash] = useState<Dashboard | null>(null);

  // Registros
  const [registros, setRegistros] = useState<Paged<Registro> | null>(null);
  const [regPage, setRegPage] = useState(1);
  const [showRegForm, setShowRegForm] = useState(false);
  const [regEmployeeId, setRegEmployeeId] = useState("");
  const [regData, setRegData] = useState("");
  const [regTipo, setRegTipo] = useState("entrada");
  const [regHora, setRegHora] = useState("");

  // Folha
  const [folha, setFolha] = useState<Folha | null>(null);
  const [folhaEmployee, setFolhaEmployee] = useState<number | "">("");
  const [folhaPeriodo, setFolhaPeriodo] = useState(periodoAtual);

  // Abonos
  const [abonos, setAbonos] = useState<Paged<Abono> | null>(null);
  const [abonoPage, setAbonoPage] = useState(1);
  const [abonoStatusFiltro, setAbonoStatusFiltro] = useState("");
  const [showAbonoForm, setShowAbonoForm] = useState(false);
  const [abEmpId, setAbEmpId] = useState("");
  const [abData, setAbData] = useState("");
  const [abTipo, setAbTipo] = useState("falta");
  const [abMotivo, setAbMotivo] = useState("");

  // ── Fetch ──────────────────────────────────────────────────────────────────

  async function loadEmployees() {
    try {
      const d = await authJson("/hr/employees?size=200");
      setEmployees(d ?? []);
      if (d?.length && !folhaEmployee) setFolhaEmployee(d[0].id);
      if (d?.length && !regEmployeeId) setRegEmployeeId(String(d[0].id));
      if (d?.length && !abEmpId) setAbEmpId(String(d[0].id));
    } catch {}
  }

  async function loadDashboard() {
    if (!periodo) return;
    try {
      const d = await authJson(`/ponto/dashboard?periodo=${periodo}`);
      setDash(d);
    } catch (e) { toast("Erro ao carregar dashboard: " + messageFrom(e), "error"); }
  }

  async function loadRegistros() {
    try {
      const params = new URLSearchParams({ page: String(regPage), size: "30" });
      if (selectedEmployee) params.set("employee_id", String(selectedEmployee));
      const d = await authJson(`/ponto/registros?${params}`);
      setRegistros(d);
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function loadFolha() {
    if (!folhaEmployee || !folhaPeriodo) return;
    try {
      const d = await authJson(`/ponto/folha/${folhaEmployee}/${folhaPeriodo}`);
      setFolha(d);
    } catch (e) { toast("Erro ao carregar folha: " + messageFrom(e), "error"); }
  }

  async function loadAbonos() {
    try {
      const params = new URLSearchParams({ page: String(abonoPage), size: "30" });
      if (abonoStatusFiltro) params.set("status", abonoStatusFiltro);
      if (selectedEmployee) params.set("employee_id", String(selectedEmployee));
      const d = await authJson(`/ponto/abonos?${params}`);
      setAbonos(d);
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  useEffect(() => { loadEmployees(); }, []);
  useEffect(() => { if (tab === "dashboard") loadDashboard(); }, [tab, periodo]);
  useEffect(() => { if (tab === "registros") loadRegistros(); }, [tab, regPage, selectedEmployee]);
  useEffect(() => { if (tab === "folha") loadFolha(); }, [tab, folhaEmployee, folhaPeriodo]);
  useEffect(() => { if (tab === "abonos") loadAbonos(); }, [tab, abonoPage, abonoStatusFiltro, selectedEmployee]);

  // ── Submit Registro ────────────────────────────────────────────────────────

  async function submitRegistro(e: FormEvent) {
    e.preventDefault();
    try {
      await authJson("/ponto/registros", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(regEmployeeId),
          data: regData,
          tipo_registro: regTipo,
          hora_registro: regHora,
        }),
      });
      toast("Ponto registrado com sucesso!");
      setShowRegForm(false);
      loadRegistros();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function deletarRegistro(id: number) {
    if (!confirm("Confirma exclusão deste registro?")) return;
    try {
      await authJson(`/ponto/registros/${id}`, { method: "DELETE" });
      toast("Registro excluído.");
      loadRegistros();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  function exportFolhaCsv() {
    if (!folhaEmployee || !folhaPeriodo) return;
    // Sanitise path segments: only allow digits and '-'
    const safeEmployee = String(folhaEmployee).replace(/[^0-9]/g, "");
    const safePeriodo = folhaPeriodo.replace(/[^0-9-]/g, "");
    window.location.href = `/api/proxy/ponto/folha/${safeEmployee}/${safePeriodo}/csv`;
  }

  // ── Submit Abono ───────────────────────────────────────────────────────────

  async function submitAbono(e: FormEvent) {
    e.preventDefault();
    try {
      await authJson("/ponto/abonos", {
        method: "POST",
        body: JSON.stringify({
          employee_id: Number(abEmpId),
          data: abData,
          tipo: abTipo,
          motivo: abMotivo,
        }),
      });
      toast("Abono solicitado com sucesso!");
      setShowAbonoForm(false);
      loadAbonos();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  async function aprovarAbono(id: number, novoStatus: string) {
    try {
      await authJson(`/ponto/abonos/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: novoStatus }),
      });
      toast(`Abono ${novoStatus}.`);
      loadAbonos();
    } catch (e) { toast("Erro: " + messageFrom(e), "error"); }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <main className="page-content">
      <h1 className="page-title">Ponto e Frequência</h1>


      <div className="tabs">
        {(["dashboard", "registros", "folha", "abonos"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "tab active" : "tab"}>
            {t === "dashboard" ? "Dashboard" :
             t === "registros" ? "Registros" :
             t === "folha" ? "Folha de Frequência" : "Abonos"}
          </button>
        ))}
      </div>

      {/* ── DASHBOARD ─────────────────────────────────────────────────────── */}
      {tab === "dashboard" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <input
                type="month"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className="filter-input"
              />
              <button className="btn btn-secondary" onClick={loadDashboard}>Atualizar</button>
            </div>
          </div>

          {dash && (
            <>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Servidores</div>
                  <div className="kpi-value">{dash.total_servidores}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Presenças</div>
                  <div className="kpi-value">{dash.total_presencas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Faltas</div>
                  <div className="kpi-value">{dash.total_faltas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Faltas Abonadas</div>
                  <div className="kpi-value">{dash.total_faltas_abonadas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Horas Extras</div>
                  <div className="kpi-value">{dash.total_horas_extras.toFixed(1)}h</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Abonos Pendentes</div>
                  <div className="kpi-value">{dash.abonos_pendentes}</div>
                </div>
              </div>

              {dash.servidores_com_falta.length > 0 && (
                <div style={{ marginTop: "1.5rem" }}>
                  <h3 className="section-title">Top servidores com faltas</h3>
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Servidor</th>
                          <th>Faltas injustificadas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dash.servidores_com_falta.map((s) => (
                          <tr key={s.employee_id}>
                            <td>{s.employee_name}</td>
                            <td>{s.faltas}</td>
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

      {/* ── REGISTROS ─────────────────────────────────────────────────────── */}
      {tab === "registros" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select
                value={selectedEmployee}
                onChange={(e) => { setSelectedEmployee(e.target.value === "" ? "" : Number(e.target.value)); setRegPage(1); }}
                className="filter-select"
              >
                <option value="">Todos os servidores</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.name}</option>
                ))}
              </select>
            </div>
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => setShowRegForm(!showRegForm)}>
                + Registrar Ponto
              </button>
            </div>
          </div>

          {showRegForm && (
            <form onSubmit={submitRegistro} className="form-card">
              <h3 className="form-title">Registrar Ponto</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Servidor *</label>
                  <select value={regEmployeeId} onChange={(e) => setRegEmployeeId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>{emp.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Data *</label>
                  <input type="date" value={regData} onChange={(e) => setRegData(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Tipo *</label>
                  <select value={regTipo} onChange={(e) => setRegTipo(e.target.value)} className="form-select">
                    {TIPOS_REGISTRO.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Hora (HH:MM) *</label>
                  <input type="time" value={regHora} onChange={(e) => setRegHora(e.target.value)} required className="form-input" />
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Registrar</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowRegForm(false)}>Cancelar</button>
              </div>
            </form>
          )}

          {registros && (
            <>
              <div className="table-meta">{registros.total} registro(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Servidor</th>
                      <th>Data</th>
                      <th>Tipo</th>
                      <th>Hora</th>
                      <th>Origem</th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registros.items.map((r) => {
                      const emp = employees.find((e) => e.id === r.employee_id);
                      return (
                        <tr key={r.id}>
                          <td>{emp?.name ?? r.employee_id}</td>
                          <td>{r.data}</td>
                          <td>{r.tipo_registro.replace(/_/g, " ")}</td>
                          <td>{r.hora_registro}</td>
                          <td>{r.origem}</td>
                          <td>
                            <button className="btn btn-xs btn-danger" onClick={() => deletarRegistro(r.id)}>
                              Excluir
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={regPage <= 1} onClick={() => setRegPage(regPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Página {regPage} de {Math.max(1, Math.ceil(registros.total / 30))}</span>
                <button disabled={regPage >= Math.ceil(registros.total / 30)} onClick={() => setRegPage(regPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── FOLHA ─────────────────────────────────────────────────────────── */}
      {tab === "folha" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select
                value={folhaEmployee}
                onChange={(e) => setFolhaEmployee(e.target.value === "" ? "" : Number(e.target.value))}
                className="filter-select"
              >
                <option value="">Servidor...</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.name}</option>
                ))}
              </select>
              <input
                type="month"
                value={folhaPeriodo}
                onChange={(e) => setFolhaPeriodo(e.target.value)}
                className="filter-input"
              />
              <button className="btn btn-secondary" onClick={loadFolha}>Ver folha</button>
            </div>
            <div className="action-row">
              {folha && (
                <button className="btn btn-secondary" onClick={exportFolhaCsv}>↓ CSV</button>
              )}
            </div>
          </div>

          {folha && (
            <>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Dias Úteis</div>
                  <div className="kpi-value">{folha.total_dias_uteis}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Presenças</div>
                  <div className="kpi-value">{folha.total_presencas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Faltas</div>
                  <div className="kpi-value">{folha.total_faltas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Faltas Abonadas</div>
                  <div className="kpi-value">{folha.total_faltas_abonadas}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Horas Trabalhadas</div>
                  <div className="kpi-value">{folha.total_horas_trabalhadas.toFixed(1)}h</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Horas Extras</div>
                  <div className="kpi-value">{folha.total_horas_extras.toFixed(1)}h</div>
                </div>
              </div>

              {folha.total_dias_uteis > 0 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
                    Frequência ({folha.total_presencas}/{folha.total_dias_uteis} dias úteis)
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.min(100, (folha.total_presencas / folha.total_dias_uteis) * 100)}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="table-responsive" style={{ marginTop: "1.25rem" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Dia</th>
                      <th>Entrada</th>
                      <th>Iníc. Interv.</th>
                      <th>Fim Interv.</th>
                      <th>Saída</th>
                      <th>H. Trab.</th>
                      <th>H. Extra</th>
                      <th>Atraso</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {folha.dias.map((d) => (
                      <tr key={d.data} style={{ opacity: d.dia_util ? 1 : 0.5 }}>
                        <td>{d.data}</td>
                        <td>{d.dia_semana}</td>
                        <td>{d.entrada ?? "—"}</td>
                        <td>{d.inicio_intervalo ?? "—"}</td>
                        <td>{d.fim_intervalo ?? "—"}</td>
                        <td>{d.saida ?? "—"}</td>
                        <td>{d.horas_trabalhadas > 0 ? `${d.horas_trabalhadas.toFixed(1)}h` : "—"}</td>
                        <td>{d.horas_extras > 0 ? `${d.horas_extras.toFixed(1)}h` : "—"}</td>
                        <td>{d.minutos_atraso > 0 ? `${d.minutos_atraso}min` : "—"}</td>
                        <td>
                          <span className={`status-chip ${STATUS_CHIP[d.status_dia] ?? "pendente"}`}>
                            {d.status_dia.replace(/_/g, " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ABONOS ────────────────────────────────────────────────────────── */}
      {tab === "abonos" && (
        <div>
          <div className="toolbar">
            <div className="filter-row">
              <select value={abonoStatusFiltro} onChange={(e) => { setAbonoStatusFiltro(e.target.value); setAbonoPage(1); }} className="filter-select">
                <option value="">Todos os status</option>
                <option value="pendente">Pendente</option>
                <option value="aprovado">Aprovado</option>
                <option value="rejeitado">Rejeitado</option>
              </select>
              <select
                value={selectedEmployee}
                onChange={(e) => { setSelectedEmployee(e.target.value === "" ? "" : Number(e.target.value)); setAbonoPage(1); }}
                className="filter-select"
              >
                <option value="">Todos os servidores</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.name}</option>
                ))}
              </select>
            </div>
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => setShowAbonoForm(!showAbonoForm)}>
                + Solicitar Abono
              </button>
            </div>
          </div>

          {showAbonoForm && (
            <form onSubmit={submitAbono} className="form-card">
              <h3 className="form-title">Solicitar Abono de Falta/Atraso</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label>Servidor *</label>
                  <select value={abEmpId} onChange={(e) => setAbEmpId(e.target.value)} required className="form-select">
                    <option value="">Selecione...</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>{emp.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Data *</label>
                  <input type="date" value={abData} onChange={(e) => setAbData(e.target.value)} required className="form-input" />
                </div>
                <div className="form-group">
                  <label>Tipo *</label>
                  <select value={abTipo} onChange={(e) => setAbTipo(e.target.value)} className="form-select">
                    {TIPOS_ABONO.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group form-group-full">
                  <label>Motivo / Justificativa</label>
                  <input value={abMotivo} onChange={(e) => setAbMotivo(e.target.value)} className="form-input" placeholder="Ex: Consulta médica — atestado apresentado" />
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Solicitar</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAbonoForm(false)}>Cancelar</button>
              </div>
            </form>
          )}

          {abonos && (
            <>
              <div className="table-meta">{abonos.total} abono(s) encontrado(s)</div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Servidor</th>
                      <th>Data</th>
                      <th>Tipo</th>
                      <th>Motivo</th>
                      <th>Status</th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {abonos.items.map((a) => {
                      const emp = employees.find((e) => e.id === a.employee_id);
                      return (
                        <tr key={a.id}>
                          <td>{emp?.name ?? a.employee_id}</td>
                          <td>{a.data}</td>
                          <td>{a.tipo.replace(/_/g, " ")}</td>
                          <td>{a.motivo || "—"}</td>
                          <td><span className={`status-chip ${ABONO_CHIP[a.status] ?? "pendente"}`}>{a.status}</span></td>
                          <td style={{ display: "flex", gap: "0.35rem" }}>
                            {a.status === "pendente" && (
                              <>
                                <button className="btn btn-xs btn-primary" onClick={() => aprovarAbono(a.id, "aprovado")}>
                                  Aprovar
                                </button>
                                <button className="btn btn-xs btn-danger" onClick={() => aprovarAbono(a.id, "rejeitado")}>
                                  Rejeitar
                                </button>
                              </>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button disabled={abonoPage <= 1} onClick={() => setAbonoPage(abonoPage - 1)} className="btn btn-secondary btn-sm">‹</button>
                <span>Página {abonoPage} de {Math.max(1, Math.ceil(abonos.total / 30))}</span>
                <button disabled={abonoPage >= Math.ceil(abonos.total / 30)} onClick={() => setAbonoPage(abonoPage + 1)} className="btn btn-secondary btn-sm">›</button>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
