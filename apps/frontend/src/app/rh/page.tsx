"use client";

import { FormEvent, useEffect, useState } from "react";

import { useToast } from "@/components/ui/toast";
import { authDownload, authJson, readCookie } from "@/lib/auth";

type ListResponse<T> = { total: number; page: number; size: number; items: T[] };
type Department = { id: number; name: string };
type Employee = { id: number; name: string; cpf: string; job_title: string; employment_type: string; base_salary: number; department_id: number };
type PayrollEvent = { id: number; employee_id: number; month: string; kind: string; description: string; value: number };
type Payslip = { id: number; employee_id: number; month: string; gross_amount: number; deductions: number; net_amount: number };
type EscalaFerias = {
  id: number; employee_id: number; ano_referencia: number;
  data_inicio: string; data_fim: string; dias_gozados: number;
  fracao: number; status: string; aprovado_por_id: number | null;
  observacoes: string;
};

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Falha na operação";
}

export default function RhPage() {
  const [role] = useState(() => readCookie("role"));
  const { toast } = useToast();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [events, setEvents] = useState<ListResponse<PayrollEvent> | null>(null);
  const [payslips, setPayslips] = useState<ListResponse<Payslip> | null>(null);

  // ── Escala de férias (RH-07) ─────────────────────────────────────────────
  const [ferias, setFerias] = useState<EscalaFerias[]>([]);
  const [feriasEmpId, setFeriasEmpId] = useState(1);
  const [feriasAno, setFeriasAno] = useState(new Date().getFullYear());
  const [feriasInicio, setFeriasInicio] = useState("");
  const [feriasFim, setFeriasFim] = useState("");
  const [feriasFracao, setFeriasFracao] = useState(1);

  const [employeeName, setEmployeeName] = useState("Servidor RH Demo");
  const [employeeCpf, setEmployeeCpf] = useState("999.888.777-66");
  const [employeeJobTitle, setEmployeeJobTitle] = useState("Analista Administrativo");
  const [employeeType, setEmployeeType] = useState("Efetivo");
  const [employeeSalary, setEmployeeSalary] = useState(4200);
  const [employeeDepartment, setEmployeeDepartment] = useState(1);

  const [eventEmployeeId, setEventEmployeeId] = useState(1);
  const [eventMonth, setEventMonth] = useState("2026-04");
  const [eventKind, setEventKind] = useState("provento");
  const [eventDescription, setEventDescription] = useState("Gratificação");
  const [eventValue, setEventValue] = useState(350);

  const [eventFilterMonth, setEventFilterMonth] = useState("2026-04");
  const [eventPage, setEventPage] = useState(1);
  const [payslipFilterMonth, setPayslipFilterMonth] = useState("2026-04");
  const [payslipPage, setPayslipPage] = useState(1);
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [employeePage, setEmployeePage] = useState(1);

  const loadDepartments = async () => {
    const data = await authJson("/core/departments");
    setDepartments(data || []);
    if (data?.[0]?.id) setEmployeeDepartment((prev) => prev || data[0].id);
  };

  const loadEmployees = async () => {
    const qs = new URLSearchParams({ page: String(employeePage), size: "10", search: employeeSearch });
    const data = await authJson(`/hr/employees?${qs.toString()}`);
    setEmployees(data || []);
    if ((data || [])[0]?.id) setEventEmployeeId((prev) => prev || data[0].id);
  };

  const loadEvents = async () => {
    const qs = new URLSearchParams({ page: String(eventPage), size: "10" });
    if (eventFilterMonth) qs.set("month", eventFilterMonth);
    const data = await authJson(`/hr/payroll-events?${qs.toString()}`);
    setEvents(data);
  };

  const loadPayslips = async () => {
    const qs = new URLSearchParams({ page: String(payslipPage), size: "10" });
    if (payslipFilterMonth) qs.set("month", payslipFilterMonth);
    const data = await authJson(`/hr/payslips?${qs.toString()}`);
    setPayslips(data);
  };

  const loadFerias = async () => {
    const qs = new URLSearchParams({ employee_id: String(feriasEmpId), size: "50" });
    const data = await authJson(`/hr/ferias?${qs.toString()}`);
    setFerias(data || []);
  };

  const refreshAll = async () => {
    try {
      await Promise.all([loadDepartments(), loadEmployees(), loadEvents(), loadPayslips(), loadFerias()]);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Falha ao carregar dados de RH", "error");
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
      loadEmployees().catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeePage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadEvents().catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventPage]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadPayslips().catch((e) => toast(messageFrom(e), "error"));
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payslipPage]);

  const createEmployee = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/hr/employees", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: employeeName,
          cpf: employeeCpf,
          job_title: employeeJobTitle,
          employment_type: employeeType,
          base_salary: Number(employeeSalary),
          department_id: Number(employeeDepartment),
        }),
      });
      toast("Servidor cadastrado com sucesso.");
      await loadEmployees();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Erro ao cadastrar servidor", "error");
    }
  };

  const createEvent = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await authJson("/hr/payroll-events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee_id: Number(eventEmployeeId),
          month: eventMonth,
          kind: eventKind,
          description: eventDescription,
          value: Number(eventValue),
        }),
      });
      toast("Evento de folha criado.");
      await loadEvents();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Erro ao criar evento", "error");
    }
  };

  const calculatePayroll = async () => {
    try {
      const data = await authJson("/hr/payroll/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ month: eventMonth }),
      });
      toast(`${data.message}. Holerites criados: ${data.created}`);
      setPayslipFilterMonth(eventMonth);
      await loadPayslips();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Erro ao calcular folha", "error");
    }
  };

  return (
    <main className="module-page">
      <h1>Módulo RH e Folha</h1>
      <p className="muted">Perfil atual: <strong suppressHydrationWarning>{role || "não identificado"}</strong> | <a href="/portal-servidor">Portal do servidor</a></p>
      <div className="auto-grid">
        <section className="card">
          <h2>1) Cadastrar servidor</h2>
          <form onSubmit={createEmployee} className="section-stack">
            <label className="field-group">Nome completo<input value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} placeholder="Nome completo" required /></label>
            <label className="field-group">CPF<input value={employeeCpf} onChange={(e) => setEmployeeCpf(e.target.value)} placeholder="CPF" required /></label>
            <label className="field-group">Cargo<input value={employeeJobTitle} onChange={(e) => setEmployeeJobTitle(e.target.value)} placeholder="Cargo" required /></label>
            <label className="field-group">Tipo de vínculo<input value={employeeType} onChange={(e) => setEmployeeType(e.target.value)} placeholder="Tipo vínculo" required /></label>
            <label className="field-group">Salário base<input type="number" value={employeeSalary} onChange={(e) => setEmployeeSalary(Number(e.target.value))} placeholder="Salário base" required /></label>
            <label className="field-group">Departamento<select value={employeeDepartment} onChange={(e) => setEmployeeDepartment(Number(e.target.value))}>
              {departments.map((dep) => <option key={dep.id} value={dep.id}>{dep.name}</option>)}
            </select></label>
            <button className="btn btn-primary" type="submit">Salvar servidor</button>
          </form>
        </section>

        <section className="card">
          <h2>2) Criar evento de folha</h2>
          <form onSubmit={createEvent} className="section-stack">
            <label className="field-group">Servidor<select value={eventEmployeeId} onChange={(e) => setEventEmployeeId(Number(e.target.value))}>
              {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
            </select></label>
            <label className="field-group">Mês de referência<input value={eventMonth} onChange={(e) => setEventMonth(e.target.value)} placeholder="Mês (YYYY-MM)" required /></label>
            <label className="field-group">Tipo do evento<select value={eventKind} onChange={(e) => setEventKind(e.target.value)}>
              <option value="provento">Provento</option>
              <option value="desconto">Desconto</option>
            </select></label>
            <label className="field-group">Descrição<input value={eventDescription} onChange={(e) => setEventDescription(e.target.value)} placeholder="Descrição" required /></label>
            <label className="field-group">Valor<input type="number" value={eventValue} onChange={(e) => setEventValue(Number(e.target.value))} placeholder="Valor" required /></label>
            <button className="btn btn-primary" type="submit">Salvar evento</button>
          </form>
          <button className="btn mt-2" onClick={calculatePayroll}>3) Calcular folha mensal</button>
        </section>
      </div>

      <section className="card">
        <h2>Servidores (busca e paginação)</h2>
        <div className="toolbar">
          <input
            value={employeeSearch}
            onChange={(e) => setEmployeeSearch(e.target.value)}
            placeholder="Buscar por nome"
          />
          <button className="btn" onClick={() => { setEmployeePage(1); loadEmployees().catch((e) => toast(messageFrom(e), "error")); }}>Buscar</button>
        </div>
        <table>
          <thead><tr><th>Nome</th><th>CPF</th><th>Cargo</th><th>Salário</th></tr></thead>
          <tbody>
            {employees.length > 0 ? (
              employees.map((emp) => (
                <tr key={emp.id}><td>{emp.name}</td><td>{emp.cpf}</td><td>{emp.job_title}</td><td>R$ {emp.base_salary.toFixed(2)}</td></tr>
              ))
            ) : (
              <tr><td colSpan={4} className="empty-state">Nenhum servidor encontrado para os filtros informados.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={employeePage <= 1} onClick={() => setEmployeePage((p) => p - 1)}>Anterior</button>
          <span> Página {employeePage} </span>
          <button className="btn" disabled={employees.length < 10} onClick={() => setEmployeePage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      <section className="card">
        <h2>Eventos de folha (filtro e paginação)</h2>
        <div className="toolbar">
          <input value={eventFilterMonth} onChange={(e) => setEventFilterMonth(e.target.value)} placeholder="Mês (YYYY-MM)" />
          <button className="btn" onClick={() => { setEventPage(1); loadEvents().catch((e) => toast(messageFrom(e), "error")); }}>Filtrar</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Servidor</th><th>Mês</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr></thead>
          <tbody>
            {(events?.items || []).length > 0 ? (
              (events?.items || []).map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td><td>{row.employee_id}</td><td>{row.month}</td><td><span className={`chip ${row.kind}`}>{row.kind}</span></td><td>{row.description}</td><td>R$ {row.value.toFixed(2)}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={6} className="empty-state">Sem eventos de folha para o mês informado.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={(events?.page || 1) <= 1} onClick={() => setEventPage((p) => p - 1)}>Anterior</button>
          <span> Página {events?.page || 1} </span>
          <button className="btn" disabled={(events?.items?.length || 0) < 10} onClick={() => setEventPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      <section className="card">
        <h2>Resultados de folha (holerites gerados)</h2>
        <div className="toolbar">
          <input value={payslipFilterMonth} onChange={(e) => setPayslipFilterMonth(e.target.value)} placeholder="Mês (YYYY-MM)" />
          <button className="btn" onClick={() => { setPayslipPage(1); loadPayslips().catch((e) => toast(messageFrom(e), "error")); }}>Filtrar</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Servidor</th><th>Mês</th><th>Bruto</th><th>Descontos</th><th>Líquido</th><th>Ação</th></tr></thead>
          <tbody>
            {(payslips?.items || []).length > 0 ? (
              (payslips?.items || []).map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td><td>{row.employee_id}</td><td>{row.month}</td>
                  <td>R$ {row.gross_amount.toFixed(2)}</td><td>R$ {row.deductions.toFixed(2)}</td><td>R$ {row.net_amount.toFixed(2)}</td>
                  <td><button className="btn" onClick={() => authDownload(`/hr/payslips/${row.id}/pdf`, `holerite-${row.id}.pdf`).catch((e) => toast(messageFrom(e), "error"))}>Baixar PDF</button></td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={7} className="empty-state">Nenhum holerite encontrado para o período selecionado.</td></tr>
            )}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={(payslips?.page || 1) <= 1} onClick={() => setPayslipPage((p) => p - 1)}>Anterior</button>
          <span> Página {payslips?.page || 1} </span>
          <button className="btn" disabled={(payslips?.items?.length || 0) < 10} onClick={() => setPayslipPage((p) => p + 1)}>Próxima</button>
        </div>
      </section>

      {/* ── Escala de Férias (RH-07) ── */}
      <section className="card">
        <h2>Escala de Férias</h2>
        {(role === "admin" || role === "hr") && (
          <form onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            try {
              await authJson("/hr/ferias", {
                method: "POST",
                body: JSON.stringify({
                  employee_id: feriasEmpId,
                  ano_referencia: feriasAno,
                  data_inicio: feriasInicio,
                  data_fim: feriasFim,
                  fracao: feriasFracao,
                }),
              });
              toast("Férias programadas com sucesso.");
              await loadFerias();
            } catch (error) {
              toast(messageFrom(error), "error");
            }
          }} className="form-row">
            <label>Servidor ID
              <input type="number" value={feriasEmpId} min={1} onChange={(e) => setFeriasEmpId(+e.target.value)} required />
            </label>
            <label>Ano Ref.
              <input type="number" value={feriasAno} min={2000} max={2099} onChange={(e) => setFeriasAno(+e.target.value)} required />
            </label>
            <label>Início
              <input type="date" value={feriasInicio} onChange={(e) => setFeriasInicio(e.target.value)} required />
            </label>
            <label>Fim
              <input type="date" value={feriasFim} onChange={(e) => setFeriasFim(e.target.value)} required />
            </label>
            <label>Fração
              <select value={feriasFracao} onChange={(e) => setFeriasFracao(+e.target.value)}>
                <option value={1}>1ª (único)</option>
                <option value={2}>2ª</option>
                <option value={3}>3ª</option>
              </select>
            </label>
            <button className="btn" type="submit">Programar</button>
            <button className="btn" type="button" onClick={() => loadFerias().catch((e) => toast(messageFrom(e), "error"))}>
              Atualizar
            </button>
          </form>
        )}
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Servidor</th><th>Ano Ref.</th><th>Início</th>
              <th>Fim</th><th>Dias</th><th>Fração</th><th>Status</th>
              {(role === "admin" || role === "hr") && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {ferias.length > 0 ? ferias.map((f) => (
              <tr key={f.id}>
                <td>{f.id}</td>
                <td>{f.employee_id}</td>
                <td>{f.ano_referencia}</td>
                <td>{f.data_inicio}</td>
                <td>{f.data_fim}</td>
                <td>{f.dias_gozados}</td>
                <td>{f.fracao}</td>
                <td>
                  <span className={`badge badge-${f.status === "aprovada" ? "success" : f.status === "cancelada" ? "danger" : "warning"}`}>
                    {f.status}
                  </span>
                </td>
                {(role === "admin" || role === "hr") && (
                  <td>
                    {f.status === "programada" && (
                      <>
                        <button className="btn btn-sm" onClick={async () => {
                          try {
                            await authJson(`/hr/ferias/${f.id}`, { method: "PATCH", body: JSON.stringify({ status: "aprovada" }) });
                            await loadFerias();
                          } catch (error) { toast(messageFrom(error), "error"); }
                        }}>Aprovar</button>
                        {" "}
                        <button className="btn btn-sm btn-danger" onClick={async () => {
                          if (!confirm("Cancelar esta escala de férias?")) return;
                          try {
                            await authJson(`/hr/ferias/${f.id}`, { method: "DELETE" });
                            await loadFerias();
                          } catch (error) { toast(messageFrom(error), "error"); }
                        }}>Cancelar</button>
                      </>
                    )}
                  </td>
                )}
              </tr>
            )) : (
              <tr><td colSpan={9} className="empty-state">Nenhuma escala de férias encontrada para este servidor.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
